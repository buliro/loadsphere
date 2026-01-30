import React, { useMemo, useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';

import { useAppDispatch, useAppSelector } from '../../../store/hooks';
import {
  loginUser,
  logoutUser,
  registerUser,
  resetAuthError,
  selectAuthViewModel,
} from '../../../store/slices/authSlice';
import type { LoginPayload, RegisterPayload } from '../../../types/auth';

import styles from './AuthScreen.module.scss';

type AuthMode = 'login' | 'register';

type RegisterFormState = RegisterPayload;

type LoginFormState = LoginPayload;

const REGISTER_INITIAL: RegisterFormState = {
  email: '',
  password1: '',
  password2: '',
  first_name: '',
  last_name: '',
};

const LOGIN_INITIAL: LoginFormState = {
  email: '',
  password: '',
};

/**
 * Check whether a string resembles a valid email address format.
 *
 * @param value - Text input supplied by the user.
 * @returns True when the value passes a basic email regex, otherwise false.
 */
const isValidEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

/**
 * Render the authentication screen providing login and registration workflows.
 *
 * @returns JSX layout containing login/register forms and related controls.
 */
export const AuthScreen: React.FC = () => {
  const dispatch = useAppDispatch();
  const { user: sessionUser, loading, authenticated, error: authError } = useAppSelector(selectAuthViewModel);

  const [mode, setMode] = useState<AuthMode>('login');
  const [registerForm, setRegisterForm] = useState<RegisterFormState>(REGISTER_INITIAL);
  const [loginForm, setLoginForm] = useState<LoginFormState>(LOGIN_INITIAL);
  const [localError, setLocalError] = useState<string | null>(null);
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [showRegisterPassword, setShowRegisterPassword] = useState(false);
  const [showRegisterConfirmPassword, setShowRegisterConfirmPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const isBusy = loading || submitting;
  const submitLabel = mode === 'login' ? 'Sign in' : 'Create account';
  const busyLabel = mode === 'login' ? 'Signing in…' : 'Creating account…';

  const isAuthenticated = Boolean(authenticated && sessionUser);
  const combinedError = localError ?? authError ?? null;

  const registerValidationMessage = useMemo(() => {
    if (mode !== 'register') {
      return null;
    }

    const messages: string[] = [];

    if (!registerForm.first_name.trim()) messages.push('First name is required');
    if (!registerForm.last_name.trim()) messages.push('Last name is required');
    if (!registerForm.email.trim()) messages.push('Email is required');
    if (registerForm.email && !isValidEmail(registerForm.email.trim())) messages.push('Enter a valid email address');
    if (registerForm.password1.length < 8) messages.push('Password must be at least 8 characters');
    if (registerForm.password1 !== registerForm.password2) messages.push('Passwords must match');

    return messages.length > 0 ? messages.join('. ') : null;
  }, [mode, registerForm]);

  /**
   * Switch between login and registration modes while resetting transient state.
   *
   * @param nextMode - Requested authentication mode.
   */
  const handleModeChange = (nextMode: AuthMode) => {
    setMode(nextMode);
    setLocalError(null);
    setShowLoginPassword(false);
    setShowRegisterPassword(false);
    setShowRegisterConfirmPassword(false);
    dispatch(resetAuthError());
  };

  /**
   * Update registration form values when a user edits an input field.
   *
   * @param event - Change event emitted by an input element.
   */
  const handleRegisterChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setRegisterForm((current: RegisterFormState) => ({ ...current, [name]: value }));
  };

  /**
   * Update login form state when a user edits an input field.
   *
   * @param event - Change event emitted by an input element.
   */
  const handleLoginChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setLoginForm((current: LoginFormState) => ({ ...current, [name]: value }));
  };

  /**
   * Submit the active authentication form and dispatch login/register actions.
   *
   * @param event - Form submission event.
   * @returns Promise that resolves when the operation finishes.
   */
  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setLocalError(null);
    dispatch(resetAuthError());

    try {
      if (mode === 'login') {
        if (!isValidEmail(loginForm.email.trim().toLowerCase())) {
          setLocalError('Enter a valid email address');
          return;
        }

        await dispatch(
          loginUser({
            email: loginForm.email.trim().toLowerCase(),
            password: loginForm.password,
          }),
        ).unwrap();
        return;
      }

      if (registerValidationMessage) {
        setLocalError(registerValidationMessage);
        return;
      }

      await dispatch(
        registerUser({
          email: registerForm.email.trim().toLowerCase(),
          password1: registerForm.password1,
          password2: registerForm.password2,
          first_name: registerForm.first_name.trim(),
          last_name: registerForm.last_name.trim(),
        }),
      ).unwrap();
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : 'Unable to submit form';
      setLocalError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    try {
      await dispatch(logoutUser()).unwrap();
      dispatch(resetAuthError());
    } catch (logoutError) {
      const message = logoutError instanceof Error ? logoutError.message : 'Failed to sign out';
      setLocalError(message);
    }
  };

  if (isAuthenticated && sessionUser) {
    return (
      <section className={styles.authScreen}>
        <div className={styles.authCard}>
          <header className={styles.header}>
            <h1>Account</h1>
            <p>Manage access to the route planner platform.</p>
          </header>
          <div className={styles.accountCard}>
            <div className={styles.accountDetails}>
              <h2>{sessionUser.first_name} {sessionUser.last_name}</h2>
              <span>{sessionUser.email}</span>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              disabled={loading || submitting}
              className={styles.signOutButton}
            >
              {loading || submitting ? 'Signing out…' : 'Sign out'}
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className={styles.authScreen}>
      <div className={styles.authCard}>
        <header className={styles.header}>
          <h1>Route Planner Portal</h1>
          <p>Sign in to orchestrate routes, or create a free account to get started.</p>
        </header>

        <div className={styles.modeSwitch} role="tablist">
          <button
            type="button"
            className={`${styles.modeButton} ${mode === 'login' ? styles.modeButtonActive : ''}`}
            onClick={() => handleModeChange('login')}
            aria-selected={mode === 'login'}
            disabled={isBusy}
          >
            Sign in
          </button>
          <button
            type="button"
            className={`${styles.modeButton} ${mode === 'register' ? styles.modeButtonActive : ''}`}
            onClick={() => handleModeChange('register')}
            aria-selected={mode === 'register'}
            disabled={isBusy}
          >
            Register
          </button>
        </div>

        <form className={styles.form} onSubmit={handleSubmit} noValidate>
          {mode === 'register' && (
            <div className={styles.nameRow}>
              <div className={styles.field}>
                <label htmlFor="first_name">First name</label>
                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  value={registerForm.first_name}
                  onChange={handleRegisterChange}
                  autoComplete="given-name"
                  required
                  disabled={isBusy}
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="last_name">Last name</label>
                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  value={registerForm.last_name}
                  onChange={handleRegisterChange}
                  autoComplete="family-name"
                  required
                  disabled={isBusy}
                />
              </div>
            </div>
          )}

          <div className={styles.field}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              value={mode === 'login' ? loginForm.email : registerForm.email}
              onChange={mode === 'login' ? handleLoginChange : handleRegisterChange}
              autoComplete="email"
              required
              disabled={isBusy}
            />
          </div>

          {mode === 'login' ? (
            <div className={`${styles.field} ${styles.passwordField}`}>
              <label htmlFor="password">Password</label>
              <input
                id="password"
                name="password"
                type={showLoginPassword ? 'text' : 'password'}
                value={loginForm.password}
                onChange={handleLoginChange}
                autoComplete="current-password"
                minLength={8}
                required
                disabled={isBusy}
              />
              <button
                type="button"
                className={styles.passwordToggle}
                onClick={() => setShowLoginPassword((current: boolean) => !current)}
                aria-label={showLoginPassword ? 'Hide password' : 'Show password'}
                disabled={isBusy}
              >
                {showLoginPassword ? '🙈' : '👁️'}
              </button>
            </div>
          ) : (
            <>
              <div className={`${styles.field} ${styles.passwordField}`}>
                <label htmlFor="password1">Password</label>
                <input
                  id="password1"
                  name="password1"
                  type={showRegisterPassword ? 'text' : 'password'}
                  value={registerForm.password1}
                  onChange={handleRegisterChange}
                  autoComplete="new-password"
                  minLength={8}
                  required
                  disabled={isBusy}
                />
                <button
                  type="button"
                  className={styles.passwordToggle}
                  onClick={() => setShowRegisterPassword((current: boolean) => !current)}
                  aria-label={showRegisterPassword ? 'Hide password' : 'Show password'}
                  disabled={isBusy}
                >
                  {showRegisterPassword ? '🙈' : '👁️'}
                </button>
              </div>
              <div className={`${styles.field} ${styles.passwordField}`}>
                <label htmlFor="password2">Confirm password</label>
                <input
                  id="password2"
                  name="password2"
                  type={showRegisterConfirmPassword ? 'text' : 'password'}
                  value={registerForm.password2}
                  onChange={handleRegisterChange}
                  autoComplete="new-password"
                  minLength={8}
                  required
                  disabled={isBusy}
                />
                <button
                  type="button"
                  className={styles.passwordToggle}
                  onClick={() => setShowRegisterConfirmPassword((current: boolean) => !current)}
                  aria-label={showRegisterConfirmPassword ? 'Hide password' : 'Show password'}
                  disabled={isBusy}
                >
                  {showRegisterConfirmPassword ? '🙈' : '👁️'}
                </button>
              </div>
            </>
          )}

          {combinedError && (
            <p className={styles.error} role="alert">
              {combinedError}
            </p>
          )}

          <div className={styles.actions}>
            <button
              type="submit"
              className={styles.submitButton}
              disabled={isBusy}
              aria-busy={isBusy}
            >
              {isBusy ? (
                <>
                  <span className={styles.submitButtonSpinner} aria-hidden="true" />
                  <span className={styles.submitButtonText}>{busyLabel}</span>
                </>
              ) : (
                submitLabel
              )}
            </button>
          </div>
        </form>

        <p className={styles.toggleMessage}>
          {mode === 'login' ? (
            <>
              Need an account?{' '}
              <button type="button" onClick={() => handleModeChange('register')} disabled={isBusy}>
                Register now
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button type="button" onClick={() => handleModeChange('login')} disabled={isBusy}>
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
    </section>
  );
};
