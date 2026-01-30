import React, { useEffect, useMemo } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { AuthScreen } from '../auth/screens/AuthScreen';
import { DashboardScreen } from '../dashboard/screens/DashboardScreen';
import { CreateRouteScreen } from '../routes/screens/CreateRouteScreen';
import RouteReportScreen from '../routes/screens/RouteReportScreen';
import LogsScreen from '../logs/screens/LogsScreen';
import { NotificationsContainer } from '../notifications/components/NotificationsContainer';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import { fetchSession, selectAuthViewModel } from '../../store/slices/authSlice';

import './App.scss';

/**
 * Render the authenticated and unauthenticated application routes.
 *
 * @param props - Component props.
 * @param props.isAuthenticated - Indicates whether a user session is active.
 * @returns JSX fragment describing the available routes.
 */
const AppRoutes: React.FC<{ isAuthenticated: boolean }> = ({ isAuthenticated }) => {
  return (
    <Routes>
      <Route
        path="/auth"
        element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <AuthScreen />}
      />
      <Route
        path="/dashboard"
        element={isAuthenticated ? <DashboardScreen /> : <Navigate to="/auth" replace />}
      />
      <Route
        path="/routes/new"
        element={isAuthenticated ? <CreateRouteScreen /> : <Navigate to="/auth" replace />}
      />
      <Route
        path="/routes/logs"
        element={isAuthenticated ? <LogsScreen /> : <Navigate to="/auth" replace />}
      />
      <Route
        path="/routes/:tripId/report"
        element={isAuthenticated ? <RouteReportScreen /> : <Navigate to="/auth" replace />}
      />
      <Route path="*" element={<Navigate to={isAuthenticated ? '/dashboard' : '/auth'} replace />} />
    </Routes>
  );
};

/**
 * Manage session bootstrap logic and shell layout for the application.
 *
 * @returns JSX structure wrapping route content and handling auth redirects.
 */
const AppContent: React.FC = () => {
  const dispatch = useAppDispatch();
  const { authenticated, user, sessionChecked } = useAppSelector(selectAuthViewModel);
  const isAuthenticated = Boolean(authenticated && user);
  const location = useLocation();
  const isDashboardRoute = useMemo(() => location.pathname.startsWith('/dashboard'), [location.pathname]);

  useEffect(() => {
    if (!sessionChecked) {
      dispatch(fetchSession());
    }
  }, [dispatch, sessionChecked]);

  useEffect(() => {
    const className = 'app-body--dashboard';

    if (isDashboardRoute) {
      document.body.classList.add(className);
    } else {
      document.body.classList.remove(className);
    }

    return () => {
      document.body.classList.remove(className);
    };
  }, [isDashboardRoute]);

  if (!sessionChecked) {
    return (
      <main className="app-shell app-shell--auth">
        <div className="app-loading">
          <div className="app-loading__spinner" aria-hidden="true" />
          <p>Preparing your workspace…</p>
        </div>
      </main>
    );
  }

  return (
    <main className={`app-shell ${isDashboardRoute ? 'app-shell--dashboard' : 'app-shell--auth'}`}>
      <AppRoutes isAuthenticated={isAuthenticated} />
    </main>
  );
};

/**
 * Root application component responsible for rendering routes and global UI chrome.
 *
 * @returns JSX layout including the routed content and notification surface.
 */
export const App: React.FC = () => {
  return (
    <>
      <AppContent />
      <NotificationsContainer />
    </>
  );
};
