import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { catalogClient } from "../api/apiClient";
import VoidLoader from "../styles/VoidLoader";

const SearchResults = () => {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q")?.trim() || "";

  const {
    data: products = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["product-search", query],
    enabled: query.length >= 2,
    queryFn: async ({ signal }) => {
      const response = await catalogClient.get("/products/", {
        params: { search: query },
        signal,
      });
      return response.data;
    },
  });

  return (
    <main className="min-h-screen bg-[#050505] text-white pt-32 pb-20 px-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl sm:text-5xl font-black uppercase italic tracking-tight">
          Search Results
        </h1>
        <p className="text-white/50 mt-3 mb-10">
          Results for: <span className="text-green-400">{query || "—"}</span>
        </p>

        {query.length < 2 && (
          <p className="text-white/50">
            Enter at least 2 characters in the navbar search.
          </p>
        )}
        {isLoading && <VoidLoader label="Searching products" />}
        {isError && (
          <p className="text-red-400">
            {error?.response?.status === 429
              ? "You're searching too quickly. Please wait a moment and try again."
              : "Could not load search results. Please try again."}
          </p>
        )}

        {!isLoading && !isError && query.length >= 2 && products.length === 0 && (
          <p className="text-white/50">No matching products found.</p>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {products.map((product) => (
            <Link
              key={product.id}
              to={`/product/${product.id}`}
              className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 hover:border-green-500/50 transition"
            >
              <img
                src={product.image}
                alt={product.name}
                className="w-full h-56 object-contain bg-black rounded-xl mb-5"
              />
              <h2 className="text-xl font-bold uppercase">{product.name}</h2>
              <p className="text-white/50 text-sm mt-2 line-clamp-2">
                {product.description}
              </p>
              <p className="text-green-400 font-bold mt-4">${product.price}</p>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
};

export default SearchResults;
