import { Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import { useDispatch } from "react-redux";

import Register from "./pages/Register";
import Login from "./pages/Login";
import Profile from "./pages/Profile";
import Home from "./pages/Home";
import ProductDetail from "./pages/ProductDetail";
import Cart from "./pages/Cart";
import Checkout from "./pages/Checkout";
import Success from "./pages/Success";
import Variants from "./pages/variants";
import SeriesPage from "./pages/SeriesPage";
import Contact from "./pages/contact";
import About from "./pages/about";
import NotFound from "./pages/NotFound";
import Banned from "./pages/Banned";
import OrderDetail from "./pages/OrderDetails";
import SearchResults from "./pages/SearchResults";
import VerifyEmail from "./pages/VerifyEmail";

import ProtectedRoute from "./components/common/ProtectedRoute";
import PublicRoute from "./components/common/PublicRoute";
import PublicLayout from "./components/layout/PublicLayout";

import AdminRoute from "./admin/components/AdminRoute";
import AdminLayout from "./admin/layouts/AdminLayout";
import AdminDashboard from "./admin/pages/AdminDashboard";
import InventoryManager from "./admin/pages/InventoryManager";
import OrderManifest from "./admin/pages/OrderManifest";
import UserDirectory from "./admin/pages/UserDirectory";

import ScrollToTop from "./utils/ScrollToTop";

import { logout, restoreSession } from "./store/authSlice";
import { fetchCurrentCart } from "./store/cartSlice";

import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./App.css";
import "./index.css";

function App() {
  const dispatch = useDispatch();

  // Restore the Django session before fetching the current cart.
  useEffect(() => {
    let active = true;

    dispatch(restoreSession()).finally(() => {
      if (active) {
        dispatch(fetchCurrentCart());
      }
    });

    return () => {
      active = false;
    };
  }, [dispatch]);

  // If Django rejects the refresh cookie, clear the Redux auth state.
  useEffect(() => {
    const handleAuthExpired = () => dispatch(logout());

    window.addEventListener("void:auth-expired", handleAuthExpired);
    return () => {
      window.removeEventListener("void:auth-expired", handleAuthExpired);
    };
  }, [dispatch]);

  

  return (
    <>
      <ScrollToTop />

      <Routes>
        <Route path="/banned" element={<Banned />} />

        <Route element={<PublicRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
        </Route>

        {/* Public pages with Navbar and Footer */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/series/:seriesId" element={<SeriesPage />} />
          <Route path="/product/:id" element={<ProductDetail />} />
          <Route path="/cart" element={<Cart />} />
          <Route path="/variants" element={<Variants />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/about" element={<About />} />
          <Route path="/search" element={<SearchResults />} />

          {/* Protected customer pages */}
          <Route element={<ProtectedRoute />}>
            <Route path="/order/:id" element={<OrderDetail />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/checkout" element={<Checkout />} />
            <Route path="/success" element={<Success />} />
          </Route>
        </Route>

        {/* Admin pages */}
        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboard />} />
            <Route path="inventory" element={<InventoryManager />} />
            <Route path="orders" element={<OrderManifest />} />
            <Route path="users" element={<UserDirectory />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>

      <ToastContainer
        theme="dark"
        position="bottom-right"
        autoClose={1600}
        hideProgressBar
        closeButton={false}
        toastClassName={() =>
          "relative flex p-4 min-h-10 rounded-2xl justify-between overflow-hidden cursor-pointer bg-[#0a0a0a] border border-white/10 shadow-2xl mb-4 font-mono text-[10px] uppercase tracking-widest"
        }
        bodyClassName={() => "flex items-center text-white"}
      />
    </>
  );
}

export default App;