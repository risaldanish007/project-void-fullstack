import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ordersClient } from "../api/apiClient";

const OrderDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const {
    data: order,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["orderDetail", id],
    queryFn: async () => {
      const response = await ordersClient.get(`/${id}/`);
      return response.data;
    },
    enabled: Boolean(id),
  });

  const getStatusStyles = (status) => {
    switch (status?.toLowerCase()) {
      case "delivered":
        return "text-green-500 border-green-500/50 bg-green-500/10";
      case "shipped":
      case "processing":
      case "placed":
        return "text-cyan-400 border-cyan-400/50 bg-cyan-400/10";
      case "cancelled":
        return "text-red-500 border-red-500/50 bg-red-500/10";
      default:
        return "text-yellow-500 border-yellow-500/50 bg-yellow-500/10";
    }
  };

  const formatDate = (value) => {
    if (!value) return "Date unavailable";
    return new Date(value).toLocaleString();
  };

  const formatUsd = (amount) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(Number(amount));

  const formatInr = (amount) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format(Number(amount));

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black text-cyan-500 font-mono text-xs uppercase tracking-[0.5em] animate-pulse font-black">
        Retrieving_Data...
      </div>
    );
  }

  if (isError || !order) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-black text-red-500 p-10 text-center">
        <h2 className="text-2xl font-black italic mb-4 uppercase tracking-tighter">
          Order_Not_Found
        </h2>
        <p className="font-mono text-xs text-white/40 uppercase tracking-widest">
          This order may not exist or may not belong to your account.
        </p>
        <button
          onClick={() => navigate("/profile")}
          className="mt-8 border border-red-500/30 px-6 py-2 text-[10px] font-black uppercase text-red-500 hover:bg-red-500 hover:text-white transition-all"
        >
          Return to Profile
        </button>
      </div>
    );
  }

  const fullName = [
    order.shipping_first_name,
    order.shipping_last_name,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="min-h-screen pt-28 sm:pt-32 pb-12 sm:pb-20 px-4 sm:px-6 max-w-4xl mx-auto text-white animate-in fade-in duration-700">
      <button
        onClick={() => navigate(-1)}
        className="mb-10 flex items-center gap-2 text-white/70 hover:text-white transition-all font-mono text-[11px] uppercase tracking-widest font-black"
      >
        <span>[</span> Back <span>]</span>
      </button>

      <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-12 border-b border-white/10 pb-10 gap-6">
        <div>
          <span className="text-cyan-500 font-mono text-[12px] tracking-[0.4em] uppercase block mb-2 font-black">
            Official_Invoice
          </span>
          <h1 className="text-3xl sm:text-5xl font-black italic tracking-tighter uppercase leading-none break-all">
            #{order.public_id.slice(-8).toUpperCase()}
          </h1>
          <p className="text-white/80 font-mono text-[11px] mt-4 font-black uppercase tracking-widest">
            Placed: {formatDate(order.created_at)}
          </p>
        </div>

        <div className="flex flex-col items-start md:items-end gap-3 max-w-full">
          <div
            className={`text-[12px] font-black uppercase tracking-[0.3em] px-6 py-2.5 rounded-xl border shadow-xl ${getStatusStyles(
              order.status
            )}`}
          >
            {order.status?.replaceAll("_", " ") || "Pending"}
          </div>
          <p className="text-[10px] font-mono text-white/50 uppercase tracking-[0.2em]">
            Payment: {order.payment_status}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16">
        <section className="space-y-8 md:space-y-12 min-w-0">
          <div>
            <h3 className="text-[12px] font-mono text-white/70 uppercase tracking-[0.5em] border-b border-white/10 pb-3 mb-6 font-black">
              Shipping_Address
            </h3>
            <div className="text-white/90 text-sm leading-relaxed uppercase font-bold tracking-wider space-y-1">
              {fullName && (
                <p className="text-xl font-black text-white italic">
                  {fullName}
                </p>
              )}
              <p className="text-white/80 font-black">
                {order.shipping_address}
              </p>
              <p className="text-white/80 font-black">
                {order.shipping_city}, {order.shipping_state} -{" "}
                {order.shipping_postal_code}
              </p>
              <div className="mt-8 p-4 bg-cyan-500/5 border border-cyan-500/20 rounded-xl inline-block">
                <p className="text-cyan-400 font-mono text-[11px] font-black tracking-widest uppercase">
                  Phone: {order.shipping_phone}
                </p>
              </div>
              {order.shipping_instructions && (
                <p className="pt-4 text-white/60 normal-case">
                  Instructions: {order.shipping_instructions}
                </p>
              )}
            </div>
          </div>

          <div>
            <h3 className="text-[12px] font-mono text-white/70 uppercase tracking-[0.5em] border-b border-white/10 pb-3 mb-6 font-black">
              Payment_Information
            </h3>
            <div className="text-white/70 text-[11px] font-mono uppercase font-black tracking-widest leading-loose">
              <p>Provider: Razorpay</p>
              <p>Payment status: {order.payment_status}</p>
              <p>Currency: {order.currency}</p>
              <p>
                USD to INR rate: {order.exchange_rate_usd_to_inr}
              </p>
            </div>
          </div>
        </section>

        <section>
          <h3 className="text-[12px] font-mono text-white/70 uppercase tracking-[0.5em] border-b border-white/10 pb-3 mb-6 font-black">
            Order_Summary
          </h3>

          <div className="space-y-4 max-h-[350px] overflow-y-auto pr-1 sm:pr-3 custom-scrollbar">
            {order.items.map((item) => (
              <div
                key={item.id}
                className="flex justify-between items-center gap-3 bg-white/[0.03] p-3 sm:p-5 rounded-2xl border border-white/10 min-w-0"
              >
                <div className="min-w-0">
                  <p className="text-white text-sm font-black uppercase tracking-tight italic leading-tight">
                    {item.product_name}
                  </p>
                  <p className="text-white/60 text-[11px] font-black mt-2 uppercase tracking-widest font-mono">
                    Qty: {item.quantity} · {formatUsd(item.unit_price_usd)} each
                  </p>
                </div>
                <span className="text-white font-black text-sm tracking-tight">
                  {formatInr(Number(item.unit_price_inr) * item.quantity)}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-12 pt-10 border-t-2 border-white/10 space-y-4">
            <div className="flex justify-between text-white/60 font-mono text-sm">
              <span>USD Subtotal</span>
              <span>{formatUsd(order.subtotal_usd)}</span>
            </div>
            <div className="flex justify-between items-end">
              <div>
                <p className="text-[12px] font-mono text-white/50 uppercase tracking-[0.4em] font-black">
                  Amount_Paid
                </p>
                <p className="text-[10px] text-cyan-500/50 uppercase font-mono mt-2 font-bold tracking-tighter">
                  Transaction_Verified
                </p>
              </div>
              <p className="text-3xl sm:text-5xl font-black italic text-cyan-400 tracking-tighter">
                {formatInr(order.total_inr)}
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default OrderDetail;