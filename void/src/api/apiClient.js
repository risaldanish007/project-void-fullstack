import axios from "axios";

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
  if (error.code === "ERR_CANCELED" || error.name === "CanceledError") return;

  const status = error.response?.status;
  if (!error.response || [502, 503, 504].includes(status)) {
    window.dispatchEvent(
      new CustomEvent("void:backend-unavailable", {
        detail: { status: status ?? null, occurredAt: Date.now() },
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
const refreshAccessToken = () => {
  if (!refreshPromise) {
    refreshPromise = accountsClient
      .post("/token/refresh/", {})
      .then(({ data }) => {
        setAccessToken(data.access);
        return data.access;
      })
      .catch((error) => {
        if (error.response?.status === 401) {
          clearAccessToken();
          window.dispatchEvent(new Event("void:auth-expired"));
        }
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
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
