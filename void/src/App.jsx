import { Routes, Route } from "react-router-dom";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDispatch } from "react-redux";
import { useIsFetching } from "@tanstack/react-query";

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
import VoidLoader from "./styles/VoidLoader";
import ServerUnavailable from "./components/common/ServerUnavailable";
import { AppStartupProvider } from "./components/common/AppStartupContext";

import { logout, restoreSession } from "./store/authSlice";
import { fetchCurrentCart } from "./store/cartSlice";

import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./App.css";
import "./index.css";

const MIN_INITIAL_LOADER_MS = 3000;
const MAX_INITIAL_LOADER_MS = 5000;
const LOADER_FADE_MS = 500;
let bootstrapPromise;

const isBackendUnavailable = (action) => {
  if (action.meta?.requestStatus !== "rejected") return false;
  const status = action.payload?.status;
  return status == null || status >= 500;
};

const initializeApp = (dispatch) => {
  if (!bootstrapPromise) {
    bootstrapPromise = (async () => {
      const sessionResult = await dispatch(restoreSession());
      if (isBackendUnavailable(sessionResult)) return false;

      const cartResult = await dispatch(fetchCurrentCart());
      return !isBackendUnavailable(cartResult);
    })()
      .catch(() => false)
      .finally(() => {
        bootstrapPromise = null;
      });
  }

  return bootstrapPromise;
};

function App() {
  const dispatch = useDispatch();
  const [startupPhase, setStartupPhase] = useState("loading");
  const [retryCount, setRetryCount] = useState(0);
  const [bootstrapComplete, setBootstrapComplete] = useState(false);
  const [fadeDuration, setFadeDuration] = useState(LOADER_FADE_MS);
  const isFetching = useIsFetching();
  const startupPhaseRef = useRef(startupPhase);
  const attemptStartedAtRef = useRef(0);
  const isFetchingRef = useRef(isFetching);

  const transitionTo = useCallback((phase) => {
    startupPhaseRef.current = phase;
    setStartupPhase(phase);
  }, []);

  useEffect(() => {
    const handleBackendUnavailable = (event) => {
      const occurredAt = event.detail?.occurredAt ?? Date.now();
      if (
        startupPhaseRef.current !== "unavailable" &&
        occurredAt >= attemptStartedAtRef.current
      ) {
        transitionTo("unavailable");
      }
    };

    window.addEventListener("void:backend-unavailable", handleBackendUnavailable);
    return () => {
      window.removeEventListener("void:backend-unavailable", handleBackendUnavailable);
    };
  }, [transitionTo]);

  // Start route queries alongside session restoration so the loader adds no API delay.
  useEffect(() => {
    let active = true;
    const startedAt = Date.now();
    attemptStartedAtRef.current = startedAt;

    initializeApp(dispatch).then((serviceAvailable) => {
      if (!active) return;
      if (!serviceAvailable) {
        transitionTo("unavailable");
        return;
      }
      setBootstrapComplete(true);
    });

    return () => {
      active = false;
    };
  }, [dispatch, retryCount, transitionTo]);

  useEffect(() => {
    isFetchingRef.current = isFetching;
  }, [isFetching]);

  // Hold the initial screen through first-route data loading, then fade it away.
  useEffect(() => {
    if (
      !bootstrapComplete ||
      isFetching > 0 ||
      startupPhaseRef.current !== "loading"
    ) {
      return undefined;
    }

    let active = true;
    let settlingTimer;
    let minimumTimer;
    let fadeTimer;

    settlingTimer = window.setTimeout(() => {
      if (
        !active ||
        isFetchingRef.current > 0 ||
        startupPhaseRef.current !== "loading"
      ) {
        return;
      }

      const isInitialAttempt = retryCount === 0;
      const elapsed = Date.now() - attemptStartedAtRef.current;
      const remainingMinimum = Math.max(
        0,
        (isInitialAttempt ? MIN_INITIAL_LOADER_MS : 0) - elapsed
      );

      minimumTimer = window.setTimeout(() => {
        if (!active || startupPhaseRef.current !== "loading") return;

        const timeBeforeFade = Date.now() - attemptStartedAtRef.current;
        const duration =
          isInitialAttempt && timeBeforeFade <= MAX_INITIAL_LOADER_MS
            ? Math.min(
                LOADER_FADE_MS,
                MAX_INITIAL_LOADER_MS - timeBeforeFade
              )
            : LOADER_FADE_MS;
        setFadeDuration(duration);
        transitionTo("fading");
        fadeTimer = window.setTimeout(() => {
          if (active && startupPhaseRef.current === "fading") {
            transitionTo("ready");
          }
        }, duration);
      }, remainingMinimum);
    }, 50);

    return () => {
      active = false;
      window.clearTimeout(settlingTimer);
      window.clearTimeout(minimumTimer);
      window.clearTimeout(fadeTimer);
    };
  }, [bootstrapComplete, isFetching, retryCount, transitionTo]);

  // If Django rejects the refresh cookie, clear the Redux auth state.
  useEffect(() => {
    const handleAuthExpired = () => dispatch(logout());

    window.addEventListener("void:auth-expired", handleAuthExpired);
    return () => {
      window.removeEventListener("void:auth-expired", handleAuthExpired);
    };
  }, [dispatch]);

  const retryBackend = () => {
    attemptStartedAtRef.current = Date.now();
    setBootstrapComplete(false);
    transitionTo("loading");
    setRetryCount((count) => count + 1);
  };

  return (
    <>
      {startupPhase === "unavailable" ? (
        <ServerUnavailable onRetry={retryBackend} />
      ) : (
        <>
          <AppStartupProvider value={startupPhase !== "ready"}>
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
          </AppStartupProvider>
          {startupPhase !== "ready" && (
            <VoidLoader
              fullScreen
              fadeOut={startupPhase === "fading"}
              fadeDuration={fadeDuration}
              label="Restoring session"
            />
          )}
        </>
      )}

      {startupPhase === "ready" && (
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
      )}
    </>
  );
}

export default App;
