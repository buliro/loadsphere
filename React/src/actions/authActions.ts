import { createAction } from '@reduxjs/toolkit';

import type { AppThunk } from '../store/configureStore';
import { AuthService } from '../services/AuthService';
import type { AuthSession, LoginPayload, RegisterPayload } from '../types/auth';

export const AUTH_ACTIONS = {
  REQUEST: 'auth/REQUEST',
  SET_SESSION: 'auth/SET_SESSION',
  FAILURE: 'auth/FAILURE',
  LOGOUT: 'auth/LOGOUT',
  RESET_ERROR: 'auth/RESET_ERROR',
} as const;

export const authRequest = createAction(AUTH_ACTIONS.REQUEST);
export const authSetSession = createAction<AuthSession | null>(AUTH_ACTIONS.SET_SESSION);
export const authFailure = createAction<{ message: string; resetSession?: boolean }>(AUTH_ACTIONS.FAILURE);
export const authLogoutAction = createAction(AUTH_ACTIONS.LOGOUT);
export const authResetError = createAction(AUTH_ACTIONS.RESET_ERROR);

/**
 * Retrieve the current authentication session from the backend and update state.
 *
 * @returns Thunk that resolves once the session request completes.
 */
export const fetchSession = (): AppThunk => async (dispatch) => {
  dispatch(authRequest());

  try {
    const session = await AuthService.session();
    dispatch(authSetSession(session));
  } catch (error) {
    dispatch(authSetSession({ authenticated: false, user: null }));
  }
};

/**
 * Attempt to authenticate a user with provided credentials.
 *
 * @param payload - Login details including email and password.
 * @returns Thunk that resolves when the login request finishes.
 * @throws Propagates the original error when authentication fails.
 */
export const login = (payload: LoginPayload): AppThunk => async (dispatch) => {
  dispatch(authRequest());

  try {
    const session = await AuthService.login(payload);
    dispatch(authSetSession(session));
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Login failed';
    dispatch(authFailure({ message, resetSession: true }));
    throw error;
  }
};

/**
 * Register a new user account and establish an authenticated session.
 *
 * @param payload - Registration payload containing email, passwords, and profile data.
 * @returns Thunk that resolves with the created session information.
 * @throws Propagates the original error when registration fails.
 */
export const register = (payload: RegisterPayload): AppThunk => async (dispatch) => {
  dispatch(authRequest());

  try {
    const session = await AuthService.register(payload);
    dispatch(authSetSession(session));
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Registration failed';
    dispatch(authFailure({ message, resetSession: true }));
    throw error;
  }
};

/**
 * Terminate the current user session and clear authentication state.
 *
 * @returns Thunk that resolves once logout completes.
 * @throws Propagates the original error if the logout request fails.
 */
export const logout = (): AppThunk => async (dispatch) => {
  dispatch(authRequest());

  try {
    await AuthService.logout();
    dispatch(authLogoutAction());
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to sign out';
    dispatch(authFailure({ message }));
    throw error;
  }
};
