import { createSelector } from '@reduxjs/toolkit';

import type { RootState } from '../store/configureStore';
import type { AuthState } from '../store/slices/authSlice';
import type { AuthSession, AuthUser } from '../types/auth';

const resolveSession = (auth: AuthState): AuthSession | null => auth.session ?? null;

export const selectAuthState = (state: RootState): AuthState => state.auth;

export const selectAuthLoading = (state: RootState): boolean => selectAuthState(state).loading;

export const selectAuthError = (state: RootState): string | null => selectAuthState(state).error;

export const selectAuthUser = (state: RootState): AuthUser | null => resolveSession(selectAuthState(state))?.user ?? null;

export const selectAuthIsLoggedIn = (state: RootState): boolean => {
  const session = resolveSession(selectAuthState(state));
  return Boolean(session?.authenticated && session?.user);
};

export const selectAuthSessionChecked = (state: RootState): boolean =>
  selectAuthState(state).sessionChecked;

export const selectAuthAuthenticated = selectAuthIsLoggedIn;

export const selectAuthViewModel = createSelector([selectAuthState], (auth) => {
  const session = resolveSession(auth);
  const authenticated = Boolean(session?.authenticated && session?.user);

  return {
    loading: auth.loading,
    error: auth.error,
    user: session?.user ?? null,
    isLoggedIn: authenticated,
    authenticated,
    sessionChecked: auth.sessionChecked,
  };
});
