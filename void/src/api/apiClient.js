import axios from "axios";
import { isBackendUnavailable } from "./errorClassification";

const API_TIMEOUT_MS = 10000;

// ---------------------------------------------------------------------------
// Axios clients – each targets a specific Django application.
// Legacy JSON-Server client (http://localhost:5000) has been removed.
// ---------------------------------------------------------------------------

export const catalogClient = axios.create({
  baseURL: import.meta.env.VITE_CATALOG_API_URL,
  timeout: API_TIMEOUT_MS,
  headers: { "Content-Type": "application/json" },
});

export const cartClient = axios.create({
  baseURL: import.meta.env.VITE_CART_API_URL,
  timeout: API_TIMEOUT_MS,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

export const accountsClient = axios.create({
  baseURL: import.meta.env.VITE_ACCOUNTS_API_URL,
  timeout: API_TIMEOUT_MS,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

export const ordersClient = axios.create({
  baseURL: import.meta.env.VITE_ORDERS_API_URL,
  timeout: API_TIMEOUT_MS,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// ---------------------------------------------------------------------------
// In-memory token store – never persisted to localStorage / sessionStorage.
// ---------------------------------------------------------------------------
let accessToken = null;
let csrfToken = null;
let refreshPromise = null;

const reportUnavailableService = (error) => {
  if (isBackendUnavailable(error)) {
    window.dispatchEvent(
      new CustomEvent("void:backend-unavailable", {
        detail: { status: null, occurredAt: Date.now() },
      })
    );
  }
};

export const setAccessToken = (token) => { accessToken = token; };
export const getAccessToken = () => accessToken;
export const clearAccessToken = () => { accessToken = null; };

export const ensureCsrfToken = async () => {
  if (csrfToken) return csrfToken;
  const response = await accountsClient.get("/csrf/");
  csrfToken = response.data.csrfToken;
  return csrfToken;
};

// ---------------------------------------------------------------------------
// Shared refresh logic – collapses concurrent 401 retries into one request.
// ---------------------------------------------------------------------------
const withSessionRefreshLock = (callback) => {
  if (typeof navigator !== "undefined" && navigator.locks?.request) {
    return navigator.locks.request("void-session-refresh", callback);
  }
  return callback();
};

export const refreshAccessToken = () => {
  if (!refreshPromise) {
    refreshPromise = withSessionRefreshLock(() =>
      accountsClient.post("/token/refresh/", {})
    )
      .then(({ data }) => {
        setAccessToken(data.access);
        return data.access;
      })
      .catch((error) => {
        if (error.response?.status === 401) {
          const notifyUser = Boolean(accessToken);
          clearAccessToken();
          window.dispatchEvent(
            new CustomEvent("void:auth-expired", {
              detail: { notifyUser },
            })
          );
        }
        // Network and 5xx failures leave a potentially valid session intact.
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
};

export const logoutSession = async () => {
  await ensureCsrfToken();

  // Older browsers lack Web Locks; avoid racing this tab's in-flight rotation.
  if (
    !(typeof navigator !== "undefined" && navigator.locks?.request) &&
    refreshPromise
  ) {
    await refreshPromise.catch(() => undefined);
  }

  return withSessionRefreshLock(() => accountsClient.post("/logout/", {}));
};

// ---------------------------------------------------------------------------
// Interceptor factory – attaches auth headers and handles 401 auto-refresh.
// Applied to every protected client.
// ---------------------------------------------------------------------------
const addRequestHeaders = (client) => {
  client.interceptors.request.use((config) => {
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    const method = config.method?.toLowerCase();
    if (["post", "put", "patch", "delete"].includes(method) && csrfToken) {
      config.headers["X-CSRFToken"] = csrfToken;
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      reportUnavailableService(error);

      const request = error.config;
      const url = request?.url || "";
      const isAuthEndpoint = [
        "/login/",
        "/register/",
        "/verify-email/",
        "/resend-otp/",
        "/csrf/",
        "/logout/",
        "/token/refresh/",
      ].some((path) => url.includes(path));

      if (
        error.response?.status !== 401 ||
        !request ||
        request._retry ||
        isAuthEndpoint
      ) {
        return Promise.reject(error);
      }

      request._retry = true;
      try {
        const access = await refreshAccessToken();
        request.headers.Authorization = `Bearer ${access}`;
        return client(request);
      } catch (refreshError) {
        return Promise.reject(refreshError);
      }
    }
  );
};

addRequestHeaders(accountsClient);
addRequestHeaders(cartClient);
addRequestHeaders(ordersClient);
addRequestHeaders(catalogClient);
