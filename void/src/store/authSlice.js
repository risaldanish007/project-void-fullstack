import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import {
  accountsClient,
  ensureCsrfToken,
  setAccessToken,
  clearAccessToken,
} from "../api/apiClient";

let restoreRequest = null;

const requestSessionRestore = () => {
  if (!restoreRequest) {
    restoreRequest = (async () => {
      await ensureCsrfToken();

      const tokenResponse = await accountsClient.post("/token/refresh/", {});
      setAccessToken(tokenResponse.data.access);

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
    await ensureCsrfToken();
    await accountsClient.post("/logout/", {});
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
