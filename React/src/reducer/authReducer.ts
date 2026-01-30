import { Map as ImmutableMap } from 'immutable';

import { AUTH_ACTIONS } from '../actions/authActions';
import { authFailure, authLogoutAction, authResetError, authRequest, authSetSession } from '../actions/authActions';
import type { AuthSession } from '../types/auth';

type AuthKnownAction =
  | ReturnType<typeof authRequest>
  | ReturnType<typeof authSetSession>
  | ReturnType<typeof authFailure>
  | ReturnType<typeof authLogoutAction>
  | ReturnType<typeof authResetError>;

export type AuthState = ImmutableMap<string, unknown>;

const initialState: AuthState = ImmutableMap<string, unknown>({
  isLoggedIn: false,
  authenticated: false,
  user: null,
  loading: false,
  error: null,
  sessionChecked: false,
});

const createSessionState = (session: AuthSession | null) => {
  const authenticated = Boolean(session?.authenticated && session?.user);
  const user = session?.user ?? null;

  return {
    isLoggedIn: authenticated,
    authenticated,
    user,
    loading: false,
    error: null,
    sessionChecked: true,
  } satisfies Record<string, unknown>;
};

export const authReducer = (state: AuthState = initialState, action: AuthKnownAction): AuthState => {
  switch (action.type) {
    case AUTH_ACTIONS.REQUEST:
      return state.merge({
        loading: true,
        error: null,
      });

    case AUTH_ACTIONS.SET_SESSION:
      return state.merge(createSessionState((action.payload as AuthSession | null) ?? null));

    case AUTH_ACTIONS.FAILURE: {
      const { message, resetSession } = (action.payload ?? {}) as { message?: string; resetSession?: boolean };
      const nextState = state.merge({
        loading: false,
        error: message ?? null,
        sessionChecked: true,
      });

      return resetSession
        ? nextState.merge({
            isLoggedIn: false,
            authenticated: false,
            user: null,
          })
        : nextState;
    }

    case AUTH_ACTIONS.LOGOUT:
      return initialState.merge({
        authenticated: false,
        sessionChecked: true,
      });

    case AUTH_ACTIONS.RESET_ERROR:
      return state.set('error', null);

    default:
      return state;
  }
};

export { initialState as authInitialState };
