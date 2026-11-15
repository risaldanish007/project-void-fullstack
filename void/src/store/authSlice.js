import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import {
  accountsClient,
  ensureCsrfToken,
  clearAccessToken,
  refreshAccessToken,
  logoutSession,
} from "../api/apiClient";

let restoreRequest = null;
const EXPLICIT_LOGOUT_KEY = "void_session_logged_out";

const hasExplicitLogout = () => {
  try {
    return localStorage.getItem(EXPLICIT_LOGOUT_KEY) === "1";
  } catch {
    return false;
  }
};

export const clearExplicitLogout = () => {
  try {
    localStorage.removeItem(EXPLICIT_LOGOUT_KEY);
  } catch {
    // Storage can be disabled; server-side logout still remains authoritative.
  }
};

const requestSessionRestore = () => {
  if (!restoreRequest) {
    restoreRequest = (async () => {
      await ensureCsrfToken();

      await refreshAccessToken();

      const profileResponse = await accountsClient.get("/profile/");
      return profileResponse.data;
    })().finally(() => {
      restoreRequest = null;
    });
  }

  return restoreRequest;
};

export const restoreSession = createAsyncThunk(
  "auth/restoreSession",
  async (_, { rejectWithValue }) => {
    if (hasExplicitLogout()) {
      clearAccessToken();
      return rejectWithValue({
        status: 401,
        message: "This session was logged out.",
      });
    }

    try {
      return await requestSessionRestore();
    } catch (error) {
      if (error.response?.status === 401) clearAccessToken();
      return rejectWithValue({
        status: error.response?.status ?? null,
        message: error.message || "Could not restore the session",
      });
    }
  }
);

export const logoutFromServer = () => async (dispatch) => {
  try {
    localStorage.setItem(EXPLICIT_LOGOUT_KEY, "1");
  } catch {
    // Storage can be disabled; clear in-memory credentials regardless.
  }

  try {
    await logoutSession();
  } catch (error) {
    console.error("Server logout request failed:", error);
  } finally {
    clearAccessToken();
    dispatch(logout());
  }
};

const authSlice = createSlice({
  name: "auth",
  initialState: {
    user: null,
    isAuthenticated: false,
    isInitializing: true,
  },
  reducers: {
    setCredentials: (state, action) => {
      state.user = action.payload;
      state.isAuthenticated = true;
      state.isInitializing = false;
    },
    logout: (state) => {
      state.user = null;
      state.isAuthenticated = false;
      state.isInitializing = false;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(restoreSession.pending, (state) => {
        state.isInitializing = true;
      })
      .addCase(restoreSession.fulfilled, (state, action) => {
        state.user = action.payload;
        state.isAuthenticated = true;
        state.isInitializing = false;
      })
      .addCase(restoreSession.rejected, (state, action) => {
        state.isInitializing = false;
        if (action.payload?.status === 401) {
          state.user = null;
          state.isAuthenticated = false;
        }
      });
  },
});



export const { setCredentials, logout } = authSlice.actions;
export default authSlice.reducer;
