import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";

import {
  ensureCsrfToken,
  ordersClient,
} from "../api/apiClient";
import { fetchCurrentCart } from "../store/cartSlice";

const Checkout = () => {
  const { items, totalPrice } = useSelector((state) => state.cart);
  const { user } = useSelector((state) => state.auth);

  const dispatch = useDispatch();
  const navigate = useNavigate();

  const [isProcessing, setIsProcessing] = useState(false);
  const [pendingOrder, setPendingOrder] = useState(null);
  const [pendingVerification, setPendingVerification] = useState(null);

  const [shippingDetails, setShippingDetails] = useState({
    firstName: "",
    lastName: "",
    phone: "",
    address: "",
    city: "",
    state: "",
    zip: "",
    instructions: "",
  });

  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (!isProcessing && (!items || items.length === 0)) {
      navigate("/cart");
    }
  }, [items, navigate, isProcessing]);

  const validateForm = () => {
    const newErrors = {};
    const nameRegex = /^[A-Za-z\s]{2,50}$/;
    const phoneRegex = /^[6-9]\d{9}$/;
    const zipRegex = /^\d{6}$/;

    if (!nameRegex.test(shippingDetails.firstName.trim())) {
      newErrors.firstName = "Enter a valid first name.";
    }

    if (
      shippingDetails.lastName.trim() &&
      !nameRegex.test(shippingDetails.lastName.trim())
    ) {
      newErrors.lastName = "Enter a valid last name.";
    }

    if (!phoneRegex.test(shippingDetails.phone.trim())) {
      newErrors.phone = "Enter a valid 10-digit Indian phone number.";
    }

    if (shippingDetails.address.trim().length < 5) {
      newErrors.address = "Enter a more detailed street address.";
    }

    if (!nameRegex.test(shippingDetails.city.trim())) {
      newErrors.city = "Enter a valid city.";
    }

    if (!nameRegex.test(shippingDetails.state.trim())) {
      newErrors.state = "Enter a valid state.";
    }

    if (!zipRegex.test(shippingDetails.zip.trim())) {
      newErrors.zip = "Enter a valid 6-digit PIN code.";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (event) => {
    const { name, value } = event.target;

    setShippingDetails((previous) => ({
      ...previous,
      [name]: value,
    }));

    if (errors[name]) {
      setErrors((previous) => ({
        ...previous,
        [name]: null,
      }));
    }
  };

  const verifyPayment = async (order, paymentResponse) => {
    await ensureCsrfToken();

    const { data: verifiedOrder } = await ordersClient.post("/verify-payment/", {
      order_id: order.order_id,
      razorpay_order_id: paymentResponse.razorpay_order_id,
      razorpay_payment_id: paymentResponse.razorpay_payment_id,
      razorpay_signature: paymentResponse.razorpay_signature,
    });

    // Django clears the purchased quantities from the database cart.
    // Refresh Redux from that server cart.
    try {
      await dispatch(fetchCurrentCart()).unwrap();
    } catch (cartError) {
      console.error("Could not refresh cart after payment:", cartError);
    }

    setPendingVerification(null);
    setPendingOrder(null);
    setIsProcessing(false);
    navigate("/success", {
      state: { orderId: verifiedOrder.order_id },
    });
  };

  const retryVerification = async () => {
    if (!pendingVerification) return;

    setIsProcessing(true);

    try {
      await verifyPayment(
        pendingVerification.order,
        pendingVerification.paymentResponse
      );
    } catch (error) {
      console.error("Payment verification retry failed:", error);
      setIsProcessing(false);
      alert(
        "Django still could not confirm the payment. Do not pay again; retry verification later."
      );
    }
  };

  const handleConfirmOrder = async (event) => {
    event.preventDefault();

    if (pendingVerification) return;
    if (!pendingOrder && !validateForm()) return;

    if (!window.Razorpay) {
      alert("Razorpay Checkout did not load. Refresh and try again.");
      return;
    }

    setIsProcessing(true);

    try {
      let order = pendingOrder;

      if (!order) {
        await ensureCsrfToken();

        const response = await ordersClient.post("/checkout/", {
          shipping_first_name: shippingDetails.firstName.trim(),
          shipping_last_name: shippingDetails.lastName.trim(),
          shipping_phone: shippingDetails.phone.trim(),
          shipping_address: shippingDetails.address.trim(),
          shipping_city: shippingDetails.city.trim(),
          shipping_state: shippingDetails.state.trim(),
          shipping_postal_code: shippingDetails.zip.trim(),
          shipping_instructions: shippingDetails.instructions.trim(),
        });

        order = response.data;
        setPendingOrder(order);
      }

      const razorpayCheckout = new window.Razorpay({
        key: order.razorpay_key_id,
        amount: order.amount,
        currency: order.currency,
        name: "VOID ENERGY",
        description: "Signal Deployment Protocol",
        order_id: order.razorpay_order_id,

        prefill: {
          name: `${shippingDetails.firstName} ${shippingDetails.lastName}`.trim(),
          email: user?.email,
          contact: `+91${shippingDetails.phone.trim()}`,
        },

        theme: {
          color: "#22d3ee",
        },

        handler: async (paymentResponse) => {
          setPendingVerification({ order, paymentResponse });

          try {
            await verifyPayment(order, paymentResponse);
          } catch (error) {
            console.error("Payment verification failed:", error);
            setIsProcessing(false);
            alert(
              "Payment may have completed, but Django could not confirm it. Retry verification; do not pay again."
            );
          }
        },

        modal: {
          ondismiss: () => {
            setIsProcessing(false);
          },
        },
      });

      razorpayCheckout.on("payment.failed", (event) => {
        console.error("Razorpay payment failed:", event.error);
        setIsProcessing(false);
        alert("Payment failed. You can retry using the same pending order.");
      });

      razorpayCheckout.open();
    } catch (error) {
      console.error("Could not start checkout:", error);
      setIsProcessing(false);

      const detail = error.response?.data?.detail;
      alert(
        typeof detail === "string"
          ? detail
          : "Could not start checkout. Please try again."
      );
    }
  };

  if (!items || items.length === 0) return null;

  const operativeName =
    [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
    user?.email ||
    "Customer";

  return (
  <div className="min-h-screen pt-24 sm:pt-28 pb-12 sm:pb-20 px-3 sm:px-6 bg-[#050505] text-white">
    <div className="max-w-3xl mx-auto">
      <div className="mb-8 sm:mb-14 flex items-end gap-4 sm:gap-6">
        <div className="h-14 w-[2px] bg-cyan-500 shadow-[0_0_12px_cyan]" />
        <div>
          <h2 className="text-3xl font-extralight uppercase tracking-tight">
            Finalize <span className="text-cyan-400 italic">Signal</span>
          </h2>
          <p className="text-[10px] font-mono uppercase tracking-[0.4em] text-white/30 mt-1">
            Operative: {operativeName} // Clearance: Level_1
          </p>
        </div>
      </div>

      <form
        onSubmit={handleConfirmOrder}
        noValidate
        className="bg-[#0d0d0d] border border-white/5 p-4 sm:p-8 md:p-12 relative overflow-hidden rounded-2xl sm:rounded-3xl"
      >
        <div className="space-y-12">
          <section className="space-y-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-pulse" />
              <label className="text-[10px] uppercase tracking-[0.5em] text-cyan-500/70 font-bold">
                Destination_Coordinates
              </label>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="flex flex-col">
                <input
                  type="text"
                  name="firstName"
                  placeholder="First Name"
                  value={shippingDetails.firstName}
                  onChange={handleInputChange}
                  disabled={Boolean(pendingOrder)}
                  className={`bg-black/60 border px-5 py-4 text-sm outline-none transition rounded-xl ${
                    errors.firstName
                      ? "border-red-500"
                      : "border-white/10 focus:border-cyan-500"
                  }`}
                />
                {errors.firstName && (
                  <span className="text-red-500 text-[9px] font-mono mt-2 ml-2">
                    {errors.firstName}
                  </span>
                )}
              </div>

              <div className="flex flex-col">
                <input
                  type="text"
                  name="lastName"
                  placeholder="Last Name (Optional)"
                  value={shippingDetails.lastName}
                  onChange={handleInputChange}
                  disabled={Boolean(pendingOrder)}
                  className={`bg-black/60 border px-5 py-4 text-sm outline-none transition rounded-xl ${
                    errors.lastName
                      ? "border-red-500"
                      : "border-white/10 focus:border-cyan-500"
                  }`}
                />
                {errors.lastName && (
                  <span className="text-red-500 text-[9px] font-mono mt-2 ml-2">
                    {errors.lastName}
                  </span>
                )}
              </div>
            </div>

            <div className="flex flex-col">
              <input
                type="tel"
                name="phone"
                placeholder="Contact Phone (10 digits)"
                value={shippingDetails.phone}
                onChange={handleInputChange}
                disabled={Boolean(pendingOrder)}
                className={`w-full bg-black/60 border px-5 py-4 text-sm outline-none transition rounded-xl ${
                  errors.phone
                    ? "border-red-500"
                    : "border-white/10 focus:border-cyan-500"
                }`}
              />
              {errors.phone && (
                <span className="text-red-500 text-[9px] font-mono mt-2 ml-2">
                  {errors.phone}
                </span>
              )}
            </div>

            <div className="flex flex-col">
              <input
                type="text"
                name="address"
                placeholder="Street Address"
                value={shippingDetails.address}
                onChange={handleInputChange}
                disabled={Boolean(pendingOrder)}
                className={`w-full bg-black/60 border px-5 py-4 text-sm outline-none transition rounded-xl ${
                  errors.address
                    ? "border-red-500"
                    : "border-white/10 focus:border-cyan-500"
                }`}
              />
              {errors.address && (
                <span className="text-red-500 text-[9px] font-mono mt-2 ml-2">
                  {errors.address}
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="flex flex-col">
                <input
                  type="text"
                  name="city"
                  placeholder="City"
                  value={shippingDetails.city}
                  onChange={handleInputChange}
                  disabled={Boolean(pendingOrder)}
                  className={`bg-black/60 border px-5 py-4 text-sm rounded-xl outline-none ${
                    errors.city
                      ? "border-red-500"
                      : "border-white/10 focus:border-cyan-500"
                  }`}
                />
                {errors.city && (
                  <span className="text-red-500 text-[9px] font-mono mt-2 ml-2">
                    {errors.city}
                  </span>
                )}
              </div>

              <div className="flex flex-col">
                <input
                  type="text"
                  name="state"
                  placeholder="State"
                  value={shippingDetails.state}
                  onChange={handleInputChange}
                  disabled={Boolean(pendingOrder)}
                  className={`bg-black/60 border px-5 py-4 text-sm rounded-xl outline-none ${
                    errors.state
                      ? "border-red-500"
                      : "border-white/10 focus:border-cyan-500"
                  }`}
                />
                {errors.state && (
                  <span className="text-red-500 text-[9px] font-mono mt-2 ml-2">
                    {errors.state}
                  </span>
                )}
              </div>

              <div className="flex flex-col">
                <input
                  type="text"
                  name="zip"
                  placeholder="PIN Code"
                  value={shippingDetails.zip}
                  onChange={handleInputChange}
                  disabled={Boolean(pendingOrder)}
                  className={`bg-black/60 border px-5 py-4 text-sm rounded-xl outline-none ${
                    errors.zip
                      ? "border-red-500"
                      : "border-white/10 focus:border-cyan-500"
                  }`}
                />
                {errors.zip && (
                  <span className="text-red-500 text-[9px] font-mono mt-2 ml-2">
                    {errors.zip}
                  </span>
                )}
              </div>
            </div>

            <textarea
              name="instructions"
              placeholder="Special Instructions (Optional)"
              rows="2"
              value={shippingDetails.instructions}
              onChange={handleInputChange}
              disabled={Boolean(pendingOrder)}
              className="w-full bg-black/60 border border-white/10 px-5 py-4 text-sm rounded-xl resize-none"
            />
          </section>

          <section className="space-y-6">
            <label className="text-[10px] uppercase tracking-[0.5em] text-cyan-500/70 font-bold">
              Payment_Protocol
            </label>

            <div className="flex items-center gap-4 border border-cyan-500/20 bg-cyan-500/5 p-6 rounded-2xl">
              <div className="w-4 h-4 rounded-full border-4 border-cyan-500 bg-black" />
              <div>
                <p className="text-sm uppercase tracking-wide font-bold">
                  Credit Uplink
                </p>
                <p className="text-[10px] text-white/40 uppercase tracking-widest">
                  Razorpay Secure Gateway
                </p>
              </div>
            </div>
          </section>

          <section className="border-t border-white/5 pt-10">
            <div className="flex justify-between text-white/40 text-[10px] uppercase tracking-[0.4em] font-mono">
              <span>Product Subtotal (USD)</span>
              <span>Payment Currency: INR</span>
            </div>

            <div className="flex justify-between items-end mt-4">
              <span className="text-4xl font-extralight uppercase tracking-tighter">
                Total
              </span>
              <span className="text-3xl sm:text-5xl font-light italic tracking-tight text-cyan-400">
                {pendingOrder
                  ? `₹${pendingOrder.total_inr}`
                  : `$${Number(totalPrice).toFixed(2)}`}
              </span>
            </div>

            {pendingOrder ? (
              <p className="text-xs text-white/40 mt-3">
                Converted at ₹{pendingOrder.exchange_rate_usd_to_inr} per USD.
              </p>
            ) : (
              <p className="text-xs text-white/40 mt-3">
                Django calculates the final INR amount before payment.
              </p>
            )}
          </section>

          {pendingVerification && (
            <div className="border border-yellow-500/30 bg-yellow-500/5 p-5 rounded-xl">
              <p className="text-sm text-yellow-300 mb-4">
                Payment was returned by Razorpay, but Django has not confirmed
                it yet. Retry confirmation; do not pay again.
              </p>
              <button
                type="button"
                onClick={retryVerification}
                disabled={isProcessing}
                className="px-5 py-3 bg-yellow-500 text-black rounded-lg font-bold disabled:opacity-50"
              >
                {isProcessing
                  ? "VERIFYING..."
                  : "Retry Payment Verification"}
              </button>
            </div>
          )}

          {!pendingVerification && (
            <button
              type="submit"
              disabled={isProcessing}
              className={`w-full h-20 border text-[12px] font-black uppercase tracking-[0.6em] transition-all ${
                isProcessing
                  ? "opacity-50 cursor-wait border-white/30"
                  : "border-white text-white hover:bg-white hover:text-black"
              }`}
            >
              {isProcessing
                ? "PROCESSING_UPLINK..."
                : pendingOrder
                  ? "Resume Payment"
                  : "Confirm & Deploy"}
            </button>
          )}
        </div>
      </form>
    </div>
  </div>
);
};

export default Checkout;
