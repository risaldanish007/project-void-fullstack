import { useSelector, useDispatch } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { updateCartItem, deleteCartItem } from "../store/cartSlice";
import { toast } from "react-toastify";

const Cart = () => {
  const navigate = useNavigate();
  const { items, totalPrice } = useSelector((state) => state.cart);
  const dispatch = useDispatch();

  const showCartError = (error) => {
    toast.error(
      error?.stock || error?.detail || "Could not update cart"
    );
  };

  const changeQuantity = async (item, amount) => {
    const quantity = item.quantity + amount;

    try {
      if (quantity < 1) {
        await dispatch(deleteCartItem(item.cartItemId)).unwrap();
      } else {
        await dispatch(
          updateCartItem({ cartItemId: item.cartItemId, quantity })
        ).unwrap();
      }
    } catch (error) {
      showCartError(error);
    }
  };

  const removeItem = async (item) => {
    try {
      await dispatch(deleteCartItem(item.cartItemId)).unwrap();
    } catch (error) {
      showCartError(error);
    }
  };

  if (items.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0a0a]">
        <div className="text-center group">
          <p className="text-[10px] tracking-[0.8em] uppercase text-white/20 mb-4 overflow-hidden">
            <span className="inline-block animate-reveal">Null Pointer / 000</span>
          </p>
          <Link to="/" className="text-white font-light text-2xl tracking-tighter hover:italic transition-all">
            Begin Acquisition —&gt;
          </Link>
        </div>
      </div>
    );
  }

 return (
  <div className="min-h-screen bg-[#0a0a0a] text-white font-light">
    <div className="max-w-7xl mx-auto pt-24 pb-20 px-4 sm:px-8">

      {/* Header */}
      <header className="flex flex-wrap justify-between items-end gap-4 mb-10 sm:mb-16">
        <h1 className="text-4xl sm:text-5xl font-extralight tracking-tight uppercase">
          Cart
          <span className="text-sm align-top ml-2 text-white/30">
            ({items.length})
          </span>
        </h1>
        <p className="text-[10px] tracking-[0.4em] uppercase text-white/30">
          Checkout Ready
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12">

        {/* Items */}
        <div className="col-span-12 lg:col-span-7 divide-y divide-white/[0.06]">
          {items.map((item, idx) => (
            <div
              key={item.id}
              className="py-6 sm:py-8 flex items-center gap-3 sm:gap-8 group hover:bg-white/[0.02] transition-colors px-2 sm:px-4 -mx-2 sm:-mx-4 min-w-0"
            >
              <span className="font-mono text-[10px] text-white/20 w-6">
                {String(idx + 1).padStart(2, "0")}
              </span>

              <div className="w-16 h-24 sm:w-24 sm:h-32 shrink-0 bg-zinc-900/60 overflow-hidden">
                <img
                  src={item.image}
                  className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition"
                  alt={item.name}
                />
              </div>

              <div className="flex-grow min-w-0 grid grid-cols-2 items-center gap-2">
                <div>
                  <h3 className="text-base sm:text-xl uppercase tracking-tight italic">
                    {item.name}
                  </h3>
                  <button
                    onClick={() => removeItem(item)}
                    className="text-[9px] tracking-[0.3em] uppercase text-white/30 hover:text-red-400 mt-2"
                  >
                    Remove
                  </button>
                </div>

                <div className="text-right space-y-4">
                  <p className="text-xl tabular-nums">
                    ${(item.price * item.quantity).toFixed(2)}
                  </p>

                  <div className="flex justify-end items-center gap-5 text-xs font-mono tracking-widest">
                    <button
                      onClick={() => changeQuantity(item, -1)}
                      className="text-white/30 hover:text-white"
                    >
                      −
                    </button>

                    <span className="text-cyan-400">
                      {item.quantity}
                    </span>

                    <button
                      onClick={() => changeQuantity(item, 1)}
                      className="text-white/30 hover:text-white"
                    >
                      +
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

{/* Summary */}
<div className="lg:col-span-5">
  <div className="lg:sticky lg:top-32 border-l border-white/10 pl-5 sm:pl-10">
    <h2 className="text-sm uppercase tracking-[0.4em] text-white/40 mb-10">
      Summary
    </h2>

    <div className="space-y-4">
      <div className="flex justify-between text-white/60 italic">
        <span>Subtotal</span>
        {/* SAFE FIX HERE */}
        <span>${Number(totalPrice || 0).toFixed(2)}</span>
      </div>

      <div className="flex justify-between text-3xl tracking-tight">
        <span className="font-extralight uppercase">Total</span>
        <span className="font-medium">
          {/* SAFE FIX HERE */}
          ${Number(totalPrice || 0).toFixed(2)}
        </span>
      </div>
    </div>

    <button
      onClick={() => navigate("/checkout")}
      className="w-full mt-12 h-16 border border-white text-[11px] tracking-[0.4em] uppercase relative overflow-hidden group"
    >
      <span className="relative z-10 group-hover:text-black transition">
        Proceed
      </span>
      <div className="absolute inset-0 bg-white translate-y-full group-hover:translate-y-0 transition-transform duration-500" />
    </button>
  </div>
</div>

      </div>
    </div>
  </div>
);
}

export default Cart;
