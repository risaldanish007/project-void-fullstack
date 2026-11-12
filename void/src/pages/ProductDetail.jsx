import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useDispatch } from "react-redux";
import { addProductToCart} from "../store/cartSlice";
import { toast } from "react-toastify";
import { catalogClient } from "../api/apiClient";

const ProductDetail = () => {
  const { id } = useParams();
  const dispatch = useDispatch();

  const { data: product, isLoading, isError } = useQuery({
    queryKey: ["product", id],
    queryFn: async () => {
      const response = await catalogClient.get(`/products/${id}`);
      return response.data;
    },
  });

  if (isLoading) return (
    <div className="min-h-screen bg-black flex items-center justify-center text-white font-black tracking-widest uppercase animate-pulse">
      Synchronizing Void...
    </div>
  );
  
  if (isError || !product) return (
    <div className="min-h-screen bg-black flex items-center justify-center text-red-500 font-black uppercase">
      Product Not Found.
    </div>
  );

  // --- INVENTORY LOGIC ---
  const stockCount = Number(product.stock || 0);
  const isOutOfStock = stockCount <= 0;
  const isLowStock = stockCount > 0 && stockCount <= 10;

  const handleAddToCart = async () => {
    if (isOutOfStock) return;

    try {
      await dispatch(
        addProductToCart({ productId: product.id, quantity: 1 })
      ).unwrap();

      toast.success("Added to cart");
    } catch (error) {
      const message =
        typeof error === "string"
          ? error
          : error?.stock || error?.detail || "Could not add product to cart";

      toast.error(message);
    }
};

  return (
    <div 
      className="product-page-wrapper relative isolate flex items-center py-24 sm:py-28"
      style={{ backgroundImage: `url(${product.image_bg})` }}
    >
      <div className="absolute inset-0 z-0 bg-black/40"></div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-8 lg:px-10 w-full flex justify-center md:justify-end">
        
        <div className={`w-full mt-4 md:mt-10 text-white max-w-md p-5 sm:p-8 bg-black/55 backdrop-blur-md rounded-xl border border-white/10 shadow-2xl transition-all ${isOutOfStock ? 'opacity-80 grayscale-[0.5]' : ''}`}>
          
          <div className="flex justify-between items-start mb-2">
            <p className="text-green-500 font-bold uppercase tracking-[0.4em] text-[9px]">
              {product.category.name}
            </p>
            
            {/* STOCK INDICATOR */}
            {isOutOfStock ? (
              <span className="text-red-500 font-mono text-[9px] uppercase tracking-widest bg-red-500/10 px-2 py-1 rounded">out of stock</span>
            ) : isLowStock ? (
              <span className="text-yellow-500 font-mono text-[9px] uppercase tracking-widest animate-pulse">LIMITED: {stockCount}</span>
            ) : (
              <span className="text-white/20 font-mono text-[9px] uppercase tracking-widest">Stock_Verified</span>
            )}
          </div>

          <h1 className="text-3xl sm:text-5xl font-black uppercase mb-4 tracking-tighter">
            {product.name}
          </h1>

          <p className="text-gray-400 text-sm leading-relaxed mb-8">
            {product.description}
          </p>

          <div className="mb-10 grid grid-cols-2 gap-4 border-y border-white/5 py-6">
            {product.ingredients?.map((item, index) => (
              <div key={index} className="flex flex-col">
                <span className="text-white font-bold text-[11px] uppercase tracking-wide">
                  {item.name}
                </span>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between">
            <span className={`text-3xl font-black ${isOutOfStock ? 'text-white/20' : 'text-white'}`}>
              ${product.price}
            </span>
            
            <button 
              onClick={handleAddToCart}
              disabled={isOutOfStock}
              className={`px-8 py-3 rounded-lg font-black uppercase text-xs tracking-widest transition-all active:scale-95
                ${isOutOfStock 
                  ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed border border-white/5' 
                  : 'bg-white text-black hover:bg-green-500 hover:text-white'}`}
            >
              {isOutOfStock ? "Out of Stock" : "Add to Cart"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductDetail;
