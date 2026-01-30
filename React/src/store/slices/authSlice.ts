import { createAsyncThunk, createSelector, createSlice } from '@reduxjs/toolkit';

import { AuthService } from '../../services/AuthService';
import type { AuthSession, LoginPayload, RegisterPayload } from '../../types/auth';
import type { RootState } from '../configureStore';

type AuthState = {
  session: AuthSession | null;
  loading: boolean;
  error: string | null;
  sessionChecked: boolean;
};

const initialState: AuthState = {
  session: null,
  loading: false,
  error: null,
  sessionChecked: false,
};

const getErrorMessage = (error: unknown, fallback: string) =>
  error instanceof Error ? error.message : fallback;

export const fetchSession = createAsyncThunk<AuthSession | null, void, { rejectValue: string }>(
  'auth/fetchSession',
  async (_, { rejectWithValue }) => {
    try {
      return await AuthService.session();
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Unable to fetch session'));
    }
  },
);

export const loginUser = createAsyncThunk<AuthSession, LoginPayload, { rejectValue: string }>(
  'auth/login',
  async (payload, { rejectWithValue }) => {
    try {
      return await AuthService.login(payload);
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Login failed'));
    }
  },
);

export const registerUser = createAsyncThunk<AuthSession, RegisterPayload, { rejectValue: string }>(
  'auth/register',
  async (payload, { rejectWithValue }) => {
    try {
      return await AuthService.register(payload);
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Registration failed'));
    }
  },
);

export const logoutUser = createAsyncThunk<void, void, { rejectValue: string }>(
  'auth/logout',
  async (_, { rejectWithValue }) => {
    try {
      await AuthService.logout();
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, 'Failed to sign out'));
    }
  },
);

const resolveAuthState = (state: AuthState, session: AuthSession | null) => {
  state.session = session;
  state.sessionChecked = true;
  state.loading = false;
  state.error = null;
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    resetAuthError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchSession.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSession.fulfilled, (state, action) => {
        resolveAuthState(state, action.payload);
      })
      .addCase(fetchSession.rejected, (state, action) => {
        resolveAuthState(state, { authenticated: false, user: null });
        state.error = action.payload ?? state.error;
      })
      .addCase(loginUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        resolveAuthState(state, action.payload);
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload ?? state.error;
        state.session = { authenticated: false, user: null };
        state.sessionChecked = true;
      })
      .addCase(registerUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(registerUser.fulfilled, (state, action) => {
        resolveAuthState(state, action.payload);
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload ?? state.error;
        state.session = { authenticated: false, user: null };
        state.sessionChecked = true;
      })
      .addCase(logoutUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(logoutUser.fulfilled, (state) => {
        resolveAuthState(state, { authenticated: false, user: null });
      })
      .addCase(logoutUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload ?? state.error;
      });
  },
});

export const { resetAuthError } = authSlice.actions;
export const authReducer = authSlice.reducer;

const selectAuthState = (state: RootState): AuthState => state.auth;

export const selectAuthSession = (state: RootState) => selectAuthState(state).session;
export const selectAuthLoading = (state: RootState) => selectAuthState(state).loading;
export const selectAuthError = (state: RootState) => selectAuthState(state).error;
export const selectAuthSessionChecked = (state: RootState) => selectAuthState(state).sessionChecked;

export const selectAuthViewModel = createSelector([selectAuthState], (auth) => {
  const session = auth.session;
  const authenticated = Boolean(session?.authenticated && session?.user);

  return {
    session,
    user: session?.user ?? null,
    authenticated,
    loading: auth.loading,
    error: auth.error,
    sessionChecked: auth.sessionChecked,
  };
});

export type { AuthState };
