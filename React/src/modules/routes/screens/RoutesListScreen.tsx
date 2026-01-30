import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { RoutesService } from '../../../services/RoutesService';
import { LogsService } from '../../../services/LogsService';
import {
  ROUTE_STATUS_DICTIONARY,
  TRIP_STATUS_LABELS,
  type RouteListTrip,
  type TripStatus,
} from '../../../types/routes';
import type { DriverLogRecord } from '../../../types/logs';
import { pushNotification } from '../../../store/slices/notificationsSlice';
import { useAppDispatch } from '../../../store/hooks';

import styles from './RoutesListScreen.module.scss';

type RoutesListScreenProps = {
  onStatusUpdated?: () => Promise<void> | void;
};

type StatusOption = {
  value: TripStatus;
  label: string;
  disabled?: boolean;
};

const STATUS_ORDER: TripStatus[] = [
  ROUTE_STATUS_DICTIONARY.planned,
  ROUTE_STATUS_DICTIONARY.inProgress,
  ROUTE_STATUS_DICTIONARY.completed,
];
const MINUTES_PER_DAY = 24 * 60;

/**
 * Resolve a human-friendly label for a trip status value.
 *
 * @param status - Trip status enum value.
 * @returns Display label for the provided status.
 */
const getStatusLabel = (status: TripStatus) => TRIP_STATUS_LABELS[status] ?? status;

/**
 * Format a trip location with optional coordinates for table display.
 *
 * @param label - Prefix describing the location role.
 * @param location - Location object with address and optional coordinates.
 * @returns String combining address and coordinates when available.
 */
const formatLocation = (label: string, location: RouteListTrip['startLocation']) => {
  if (!location?.address) {
    return `${label}: —`;
  }
  const coords =
    location?.lat != null && location?.lng != null
      ? ` (${location.lat.toFixed(4)}, ${location.lng.toFixed(4)})`
      : '';
  return `${label}: ${location.address}${coords}`;
};

/**
 * Render a table of saved routes with status management controls.
 *
 * @param props - Component props.
 * @param props.onStatusUpdated - Optional callback after a status mutation.
 * @returns JSX table containing route metadata and actions.
 */
export const RoutesListScreen: React.FC<RoutesListScreenProps> = ({ onStatusUpdated }) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [routes, setRoutes] = useState<RouteListTrip[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  /**
   * Fetch the route list from the backend and update component state.
   *
   * @returns Promise resolving when routes have been loaded.
   */
  const loadRoutes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await RoutesService.fetchRoutesList();
      setRoutes(list);
    } catch (fetchError) {
      const message =
        fetchError instanceof Error ? fetchError.message : 'Unable to load routes right now.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRoutes();
  }, [loadRoutes]);

  /**
   * Reload the current route list on demand.
   */
  const handleRefresh = () => {
    void loadRoutes();
  };

  const handleViewReport = useCallback(
    (tripId: string) => {
      navigate(`/routes/${tripId}/report`);
    },
    [navigate],
  );

  const statusOptions = useMemo<StatusOption[]>(
    () => STATUS_ORDER.map((status) => ({ value: status, label: getStatusLabel(status) })),
    [],
  );

  /**
   * Compute available status options for a given route row.
   *
   * @param route - Route entry to evaluate.
   * @returns Array of select options with disabled states applied.
   */
  const getRouteOptions = useCallback(
    (route: RouteListTrip) => {
      if (route.status === ROUTE_STATUS_DICTIONARY.inProgress) {
        return statusOptions.map((option) => {
          if (option.value === ROUTE_STATUS_DICTIONARY.planned) {
            return { ...option, disabled: true };
          }
          if (option.value === ROUTE_STATUS_DICTIONARY.inProgress) {
            return { ...option, disabled: true };
          }
          return option;
        });
      }

      if (route.status === ROUTE_STATUS_DICTIONARY.planned) {
        const otherInProgress = routes.some(
          (candidate) =>
            candidate.id !== route.id && candidate.status === ROUTE_STATUS_DICTIONARY.inProgress,
        );

        return statusOptions.map((option) => {
          if (option.value === ROUTE_STATUS_DICTIONARY.inProgress) {
            return { ...option, disabled: otherInProgress };
          }
          if (option.value === ROUTE_STATUS_DICTIONARY.completed) {
            return { ...option, disabled: true };
          }
          return option;
        });
      }

      if (route.status === ROUTE_STATUS_DICTIONARY.completed) {
        return statusOptions.map((option) =>
          option.value === ROUTE_STATUS_DICTIONARY.completed
            ? { ...option, disabled: true }
            : { ...option, disabled: true },
        );
      }

      return statusOptions;
    },
    [routes, statusOptions],
  );

  /**
   * Persist a status change for a route and update local state.
   *
   * @param tripId - Identifier of the route being updated.
   * @param nextStatus - Requested status value.
   * @returns Promise resolving when the mutation completes.
   */
  const handleStatusChange = async (tripId: string, nextStatus: TripStatus) => {
    const currentRoute = routes.find((route) => route.id === tripId);
    if (!currentRoute || currentRoute.status === nextStatus) {
      return;
    }

    if (nextStatus === ROUTE_STATUS_DICTIONARY.completed) {
      try {
        const driverLogs = await LogsService.fetchDriverLogs(tripId);
        const flaggedLogs = driverLogs
          .map((log: DriverLogRecord) => {
            const totalMinutes =
              (log.totalDrivingMinutes ?? 0) +
              (log.totalOnDutyMinutes ?? 0) +
              (log.totalOffDutyMinutes ?? 0) +
              (log.totalSleeperMinutes ?? 0);

            return {
              dayNumber: log.dayNumber,
              totalMinutes,
            };
          })
          .filter(({ totalMinutes }) => totalMinutes > 0 && totalMinutes % MINUTES_PER_DAY !== 0);

        if (flaggedLogs.length > 0) {
          const summary = flaggedLogs
            .map(({ dayNumber, totalMinutes }) => `• Day ${dayNumber}: ${(totalMinutes / 60).toFixed(2)} hrs recorded`)
            .join('\n');

          const proceed = window.confirm(
            `Driver log totals for this route do not equal a full 24-hour day (driving + on duty + off duty + sleeper):\n${summary}\n\nMark this route as completed anyway?`,
          );

          if (!proceed) {
            return;
          }
        }
      } catch (logError) {
        const message =
          logError instanceof Error ? logError.message : 'Unable to verify driver log hours for this route.';
        dispatch(pushNotification({ message, variant: 'warning' }));
      }
    }

    setUpdatingId(tripId);
    try {
      await RoutesService.updateRouteStatus(tripId, nextStatus);
      setRoutes((current) =>
        current.map((route) => (route.id === tripId ? { ...route, status: nextStatus } : route)),
      );
      dispatch(
        pushNotification({
          message: `Route status updated to ${getStatusLabel(nextStatus)}.`,
          variant: 'success',
        }),
      );
      if (onStatusUpdated) {
        await onStatusUpdated();
      }
    } catch (updateError) {
      const message =
        updateError instanceof Error ? updateError.message : 'Unable to update route status.';
      dispatch(pushNotification({ message, variant: 'error' }));
    } finally {
      setUpdatingId(null);
    }
  };

  /**
   * Delete a planned route after user confirmation.
   *
   * @param tripId - Identifier of the route to delete.
   * @returns Promise resolving once deletion finishes.
   */
  const handleDeleteRoute = async (tripId: string) => {
    const targetRoute = routes.find((route) => route.id === tripId);
    if (!targetRoute || targetRoute.status !== ROUTE_STATUS_DICTIONARY.planned) {
      return;
    }

    const confirmed = window.confirm(
      'Are you sure you want to delete this planned route? This action cannot be undone.',
    );

    if (!confirmed) {
      return;
    }

    setDeletingId(tripId);
    try {
      await RoutesService.deleteRoute(tripId);
      setRoutes((current) => current.filter((route) => route.id !== tripId));
      dispatch(
        pushNotification({
          message: 'Planned route deleted.',
          variant: 'success',
        }),
      );
      if (onStatusUpdated) {
        await onStatusUpdated();
      }
    } catch (deleteError) {
      const message =
        deleteError instanceof Error ? deleteError.message : 'Unable to delete this route.';
      dispatch(pushNotification({ message, variant: 'error' }));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <div className={styles.headerTitle}>
          <h2>Saved routes</h2>
          <p>Manage route statuses and review latest plans.</p>
        </div>
        <button type="button" className={styles.refreshButton} onClick={handleRefresh} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </header>

      <div className={styles.tableWrapper}>
        <table>
          <thead>
            <tr>
              <th>Vehicle ID</th>
              <th>Carriers</th>
              <th>Commodity</th>
              <th>Locations</th>
              <th className={styles.statusCell}>Status</th>
              <th className={styles.metaCell}>Created</th>
              <th className={styles.actionsCell}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && routes.length === 0 ? (
              <tr className={styles.loadingRow}>
                <td colSpan={7}>Loading routes…</td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={7}>
                  <div className={styles.errorState}>
                    {error}
                    <br />
                    <button type="button" onClick={handleRefresh}>
                      Try again
                    </button>
                  </div>
                </td>
              </tr>
            ) : routes.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className={styles.emptyState}>
                    <strong>No routes saved yet.</strong>
                    Create a new route to see it listed here.
                  </div>
                </td>
              </tr>
            ) : (
              routes.map((route) => {
                const isDisabled = updatingId === route.id || deletingId === route.id;
                return (
                  <tr key={route.id}>
                    <td>{route.tractorNumber}</td>
                    <td>{route.carrierNames.join(', ') || '—'}</td>
                    <td>{route.commodity}</td>
                    <td>
                      <div className={styles.locationGroup}>
                        <span className={styles.locationLabel}>{formatLocation('Start', route.startLocation)}</span>
                        <span className={styles.locationLabel}>{formatLocation('Pickup', route.pickupLocation)}</span>
                        <span className={styles.locationLabel}>{formatLocation('Dropoff', route.dropoffLocation)}</span>
                      </div>
                    </td>
                    <td>
                      <select
                        className={styles.statusSelect}
                        value={route.status}
                        disabled={isDisabled}
                        onChange={(event) =>
                          handleStatusChange(route.id, event.target.value as TripStatus)
                        }
                      >
                        {getRouteOptions(route).map((option) => (
                          <option
                            key={option.value}
                            value={option.value}
                            disabled={option.disabled}
                          >
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className={styles.metaCell}>
                      {new Date(route.createdAt).toLocaleString()}
                    </td>
                    <td className={styles.actionsCell}>
                      {route.status === ROUTE_STATUS_DICTIONARY.completed ? (
                        <button
                          type="button"
                          className={styles.viewReportButton}
                          onClick={() => handleViewReport(route.id)}
                          disabled={isDisabled}
                          aria-label="View completed route report"
                        >
                          View Report
                        </button>
                      ) : route.status === ROUTE_STATUS_DICTIONARY.planned ? (
                        <button
                          type="button"
                          className={styles.deleteButton}
                          onClick={() => handleDeleteRoute(route.id)}
                          disabled={isDisabled}
                          aria-label="Delete planned route"
                          title="Delete planned route"
                        >
                          🗑
                        </button>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
