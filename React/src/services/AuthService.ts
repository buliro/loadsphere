import { restJson } from './rest';
import type { AuthSession, LoginPayload, RegisterPayload } from '../types/auth';

type SessionResponse = {
  authenticated?: boolean;
  success?: boolean;
  user?: AuthSession['user'];
  errors?: string[];
  detail?: string;
};

const AUTH_ENDPOINTS = {
  register: '/api/auth/register/',
  login: '/api/auth/login/',
  logout: '/api/auth/logout/',
  session: '/api/auth/session/',
} as const;

/**
 * Derive a human-readable error message from an auth endpoint response body.
 *
 * @param data - Parsed JSON payload returned by the backend, if any.
 * @param fallback - Default message to use when no explicit error is present.
 * @returns Resolved error string suitable for display.
 */
const extractErrorMessage = (data: SessionResponse | null, fallback = 'Request failed') => {
  if (!data) {
    return fallback;
  }

  if (Array.isArray(data.errors) && data.errors.length > 0) {
    return data.errors.join('\n');
  }

  if (typeof data.detail === 'string' && data.detail.length > 0) {
    return data.detail;
  }

  return fallback;
};

/**
 * Normalise backend session responses into the front-end session shape.
 *
 * @param data - Parsed session response payload from the API.
 * @returns AuthSession containing authentication flag and optional user data.
 */
const resolveSession = (data: SessionResponse | null): AuthSession => {
  const user = data?.user ?? null;
  const authenticatedFlag = data?.authenticated ?? data?.success ?? Boolean(user);

  return {
    authenticated: Boolean(authenticatedFlag && user),
    user,
  };
};

export const AuthService = {
  async register(payload: RegisterPayload): Promise<AuthSession> {
    /**
     * Submit registration data to the backend and return the resulting session.
     *
     * @param payload - Registration details including credentials and profile fields.
     * @returns AuthSession describing the authenticated user.
     * @throws Error when the server indicates registration failure.
     */
    const { response, data } = await restJson<SessionResponse>(AUTH_ENDPOINTS.register, {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(extractErrorMessage(data, 'Registration failed'));
    }

    return resolveSession(data);
  },

  async login(payload: LoginPayload): Promise<AuthSession> {
    /**
     * Authenticate a user with email and password credentials.
     *
     * @param payload - Login payload containing user credentials.
     * @returns AuthSession describing the authenticated user when successful.
     * @throws Error when the server rejects the login request.
     */
    const { response, data } = await restJson<SessionResponse>(AUTH_ENDPOINTS.login, {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(extractErrorMessage(data, 'Login failed'));
    }

    return resolveSession(data);
  },

  async logout(): Promise<void> {
    /**
     * Terminate the active session on the backend.
     *
     * @returns Promise resolving when the logout completes.
     * @throws Error when the server fails to process the logout request.
     */
    const { response, data } = await restJson<SessionResponse>(AUTH_ENDPOINTS.logout, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(extractErrorMessage(data, 'Failed to sign out'));
    }
  },

  async session(): Promise<AuthSession> {
    /**
     * Fetch the current session metadata for the active user.
     *
     * @returns AuthSession describing whether the user is authenticated.
     * @throws Error when the session request is unsuccessful.
     */
    const { response, data } = await restJson<SessionResponse>(AUTH_ENDPOINTS.session);

    if (!response.ok) {
      throw new Error('Failed to fetch session');
    }

    return resolveSession(data);
  },
};
