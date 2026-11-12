import axios from "axios";

const apiClient = axios.create({
  baseURL: "http://localhost:5000",
  // baseURL: 'https://void-server-bwya.onrender.com',
  // For the legacy server, replace the URL above with its deployed API URL.
  headers: {
    "Content-Type": "application/json",
  },
});

export { apiClient };
export default apiClient;

export const catalogClient = axios.create({
  baseURL: import.meta.env.VITE_CATALOG_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const cartClient = axios.create({
  baseURL: import.meta.env.VITE_CART_API_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

export const accountsClient = axios.create({
  baseURL: import.meta.env.VITE_ACCOUNTS_API_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

export const ordersClient = axios.create({
  baseURL: import.meta.env.VITE_ORDERS_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

let accessToken = null;
let csrfToken = null;
let refreshPromise = null;

export const setAccessToken = (token) => {
  accessToken = token;
};

export const getAccessToken = () => accessToken;

export const clearAccessToken = () => {
  accessToken = null;
};

export const ensureCsrfToken = async () => {
  if (csrfToken) return csrfToken;

  const response = await accountsClient.get("/csrf/");
  csrfToken = response.data.csrfToken;

  return csrfToken;
};

const refreshAccessToken = () => {
  if (!refreshPromise) {
    refreshPromise = accountsClient
      .post("/token/refresh/", {})
      .then(({ data }) => {
        setAccessToken(data.access);
        return data.access;
      })
      .catch((error) => {
        clearAccessToken();
        window.dispatchEvent(new Event("void:auth-expired"));
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
};

const addRequestHeaders = (client) => {
  client.interceptors.request.use((config) => {
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }

    const method = config.method?.toLowerCase();
    const changesData = ["post", "put", "patch", "delete"].includes(method);

    if (changesData && csrfToken) {
      config.headers["X-CSRFToken"] = csrfToken;
    }

    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    async (error) => {
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