import { Link, useNavigate } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import Logo from "./Logo";
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import AdminLink from "../../admin/layouts/AdminLink";
import { logoutFromServer } from "../../store/authSlice";
import { catalogClient } from "../../api/apiClient";

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const { user, isAuthenticated } = useSelector((state) => state.auth);
  const { totalQuantity } = useSelector((state) => state.cart);

  const dispatch = useDispatch();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await dispatch(logoutFromServer());
    setIsMenuOpen(false);
    navigate("/");
  };

  const closeMenu = () => setIsMenuOpen(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm.trim());
    }, 300);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  const { data: suggestions = [], error: suggestionError } = useQuery({
    queryKey: ["catalog-search-suggestions", debouncedSearchTerm],
    enabled: debouncedSearchTerm.length >= 2,
    queryFn: async ({ signal }) => {
      const response = await catalogClient.get("/products/", {
        params: { search: debouncedSearchTerm },
        signal,
      });
      return response.data.slice(0, 5);
    },
    retry: (failureCount, error) =>
      error.response?.status !== 429 && failureCount < 2,
  });

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    const query = searchTerm.trim();

    if (query.length < 2) return;

    setShowSuggestions(false);
    closeMenu();
    navigate(`/search?q=${encodeURIComponent(query)}`);
  };

  const renderSuggestions = () => {
    if (
      !showSuggestions ||
      debouncedSearchTerm.length < 2 ||
      searchTerm.trim() !== debouncedSearchTerm
    ) {
      return null;
    }

    return (
      <div
        onMouseDown={(event) => event.preventDefault()}
        className="absolute left-0 right-0 top-full z-[130] mt-2 max-h-80 overflow-y-auto rounded-2xl border border-white/10 bg-[#0a0a0a] shadow-2xl"
      >
        {suggestionError ? (
          <p className="px-4 py-3 text-xs text-red-400">
            {suggestionError.response?.status === 429
              ? "Searching too quickly. Please wait a moment."
              : "Could not load suggestions."}
          </p>
        ) : suggestions.length ? (
          suggestions.map((product) => (
            <Link
              key={product.id}
              to={`/product/${product.id}`}
              onClick={() => {
                setShowSuggestions(false);
                closeMenu();
              }}
              className="flex items-center gap-3 border-b border-white/5 px-4 py-3 last:border-b-0 hover:bg-white/5"
            >
              <img
                src={product.image}
                alt=""
                className="h-10 w-10 rounded-lg bg-black object-contain"
              />
              <span className="min-w-0 flex-1 truncate text-xs font-bold uppercase text-white">
                {product.name}
              </span>
              <span className="text-xs text-green-400">${product.price}</span>
            </Link>
          ))
        ) : (
          <p className="px-4 py-3 text-xs text-white/50">No matching products.</p>
        )}
      </div>
    );
  };

  useEffect(() => {
    document.body.style.overflow = isMenuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [isMenuOpen]);

  return (
    <nav className="fixed top-2 left-1/2 -translate-x-1/2 w-[calc(100%-1rem)] sm:w-[95%] max-w-7xl bg-[#0a0a0a] border border-white/10 px-3 sm:px-6 py-2.5 sm:py-3 flex justify-between items-center z-[100] rounded-full shadow-2xl">
      {/* Logo */}
      <Link
        to="/"
        onClick={closeMenu}
        className="z-[120] inline-flex h-10 shrink-0 items-center sm:h-12"
      >
        <Logo />
      </Link>

      {/* Desktop links and account actions */}
      <div className="flex items-center gap-4 md:gap-8">
        <div className="hidden md:flex items-center gap-4 lg:gap-8 text-sm font-bold uppercase tracking-widest text-gray-400">
          <form
            onSubmit={handleSearchSubmit}
            role="search"
            className="relative flex items-center rounded-full border border-white/10 bg-white/5"
          >
            <label htmlFor="desktop-product-search" className="sr-only">
              Search products
            </label>
            <input
              id="desktop-product-search"
              type="search"
              value={searchTerm}
              onChange={(event) => {
                setSearchTerm(event.target.value);
                setShowSuggestions(true);
              }}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setShowSuggestions(false)}
              placeholder="Search products"
              className="w-24 lg:w-36 xl:w-44 bg-transparent px-3 lg:px-4 py-2 text-xs text-white outline-none placeholder:text-white/30"
            />
            <button
              type="submit"
              aria-label="Search products"
              className="px-2 lg:px-3 py-2 text-green-400 hover:text-white"
            >
              ⌕
            </button>
            {renderSuggestions()}
          </form>

          <Link
            to="/variants"
            onClick={closeMenu}
            className="hover:text-white transition-colors"
          >
            Shop
          </Link>

          <Link to="/cart" className="relative group">
            <span className="text-xl group-hover:scale-110 block transition-transform">
              🛒
            </span>
            {totalQuantity > 0 && (
              <span className="absolute -top-2 -right-2 bg-green-500 text-black text-[10px] w-4 h-4 flex items-center justify-center rounded-full font-black">
                {totalQuantity}
              </span>
            )}
          </Link>

          {isAuthenticated ? (
            <div className="flex items-center gap-6 border-l border-white/10 pl-8">
              <Link
                to="/profile"
                className="text-white hover:text-green-500 transition-colors lowercase font-medium"
              >
                Hi, <span className="text-green-500">{user?.first_name}</span>
              </Link>
              <AdminLink />
              <button
                onClick={handleLogout}
                className="bg-white/5 hover:bg-red-500/20 hover:text-red-500 border border-white/10 px-5 py-2 rounded-full transition-all text-xs"
              >
                Logout
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-6">
              <Link to="/login" className="hover:text-white transition-colors">
                Login
              </Link>
              <Link
                to="/register"
                className="bg-white text-black px-6 py-2 rounded-full hover:bg-green-500 transition-all font-bold"
              >
                Join
              </Link>
            </div>
          )}
        </div>

        {/* Mobile cart */}
        <Link
          to="/cart"
          onClick={closeMenu}
          className="md:hidden relative z-[120] mr-2"
        >
          <span className="text-xl">🛒</span>
          {totalQuantity > 0 && (
            <span className="absolute -top-2 -right-2 bg-green-500 text-black text-[9px] w-4 h-4 flex items-center justify-center rounded-full font-bold">
              {totalQuantity}
            </span>
          )}
        </Link>

        {/* Mobile menu toggle */}
        <button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className="md:hidden z-[120] text-white text-2xl w-10 h-10 flex items-center justify-center"
          aria-label={isMenuOpen ? "Close menu" : "Open menu"}
          aria-expanded={isMenuOpen}
        >
          {isMenuOpen ? "✕" : "☰"}
        </button>
      </div>

      {/* Mobile menu */}
      <div
        className={`
          fixed inset-0 w-full h-[100dvh] overflow-y-auto overscroll-contain
          bg-[#0a0a0a] flex flex-col items-center justify-center gap-6 sm:gap-8
          px-6 py-24 transition-all duration-500 ease-in-out z-[110]
          ${
            isMenuOpen
              ? "translate-y-0 opacity-100"
              : "-translate-y-full opacity-0 pointer-events-none"
          }
        `}
      >
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-green-500/10 blur-[120px] rounded-full" />

        <Link
          to="/variants"
          onClick={closeMenu}
          className="text-4xl font-black uppercase italic tracking-tighter text-white hover:text-green-500 transition-colors"
        >
          Shop
        </Link>

        <form
          onSubmit={handleSearchSubmit}
          role="search"
          className="relative flex w-full max-w-sm items-center rounded-full border border-white/10 bg-white/5"
        >
          <label htmlFor="mobile-product-search" className="sr-only">
            Search products
          </label>
          <input
            id="mobile-product-search"
            type="search"
            value={searchTerm}
            onChange={(event) => {
              setSearchTerm(event.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setShowSuggestions(false)}
            placeholder="Search products"
            className="min-w-0 flex-1 bg-transparent px-5 py-3 text-sm text-white outline-none placeholder:text-white/30"
          />
          <button
            type="submit"
            className="px-5 py-3 text-xs font-bold uppercase tracking-widest text-green-400"
          >
            Search
          </button>
          {renderSuggestions()}
        </form>

        <div className="flex flex-wrap justify-center gap-x-8 gap-y-4 text-xs sm:text-sm font-mono uppercase tracking-[0.2em] text-white/60">
          <Link
            to="/about"
            onClick={closeMenu}
            className="hover:text-green-400"
          >
            About
          </Link>
          <Link
            to="/contact"
            onClick={closeMenu}
            className="hover:text-green-400"
          >
            Contact
          </Link>
          {isAuthenticated && (
            <Link
              to="/profile"
              onClick={closeMenu}
              className="hover:text-green-400"
            >
              Orders
            </Link>
          )}
          {isAuthenticated && <AdminLink />}
        </div>

        <div className="h-[1px] w-12 bg-white/10" />

        {isAuthenticated ? (
          <>
            <Link
              to="/profile"
              onClick={closeMenu}
              className="text-xl text-white font-mono uppercase tracking-widest"
            >
              Account: <span className="text-green-500">{user?.name}</span>
            </Link>
            <button
              onClick={handleLogout}
              className="bg-red-500/10 text-red-500 border border-red-500/20 px-10 py-4 rounded-full font-black uppercase tracking-widest text-xs"
            >
              Logout System
            </button>
          </>
        ) : (
          <div className="flex flex-col items-center gap-6 w-full px-10">
            <Link
              to="/login"
              onClick={closeMenu}
              className="text-2xl text-white font-black uppercase italic tracking-tighter"
            >
              Login
            </Link>
            <Link
              to="/register"
              onClick={closeMenu}
              className="w-full max-w-[300px] text-center bg-white text-black py-5 rounded-full font-black text-xl hover:bg-green-500 transition-colors uppercase tracking-tighter"
            >
              Join the Void
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
