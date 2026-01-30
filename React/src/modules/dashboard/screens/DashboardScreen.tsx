import React, { useCallback, useEffect, useMemo, useState } from 'react';

import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet';
import type { LatLngExpression, LatLngTuple } from 'leaflet';
import L from 'leaflet';
import polyline from '@mapbox/polyline';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

import { useAppDispatch, useAppSelector } from '../../../store/hooks';
import {
  logoutUser,
  resetAuthError,
  selectAuthViewModel,
} from '../../../store/slices/authSlice';
import { pushNotification } from '../../../store/slices/notificationsSlice';
import { RoutesService } from '../../../services/RoutesService';
import type { ActiveRouteSummary } from '../../../types/routes';
import { RoutesListScreen } from '../../routes/screens/RoutesListScreen';
import { CreateRouteScreen } from '../../routes/screens/CreateRouteScreen';
import LogsScreen from '../../logs/screens/LogsScreen';
import styles from './DashboardScreen.module.scss';

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const segmentMarkerIcon = L.divIcon({
  className: `${styles.mapMarker} ${styles.mapMarkerSegment}`,
  iconSize: [22, 22],
  iconAnchor: [11, 22],
  popupAnchor: [0, -16],
});

type NavSection = 'overview' | 'routes' | 'compliance' | 'alerts';

type NavItem = {
  id: NavSection;
  label: string;
  description: string;
};

const NAV_ITEMS: NavItem[] = [
  { id: 'overview', label: 'Overview', description: 'Summary and live metrics' },
  { id: 'routes', label: 'Routes', description: 'Planned & active itineraries' },
  // { id: 'compliance', label: 'Compliance', description: 'HOS & FMCSA insights' },
  // { id: 'alerts', label: 'Alerts', description: 'Exceptions and notifications' },
];

const METRICS = [
  {
    id: 'on-time',
    label: 'On-time departures',
    value: '92%',
    delta: '+4.6% vs last week',
  },
  {
    id: 'compliance',
    label: 'HOS compliance',
    value: '98%',
    delta: 'No violations in 5 days',
  },
  {
    id: 'distance',
    label: 'Total miles today',
    value: '18.7k',
    delta: 'Active across 23 routes',
  },
];

const SEGMENT_STATUS_LABELS: Record<string, string> = {
  OFF_DUTY: 'Off duty',
  SLEEPER_BERTH: 'Sleeper berth',
  DRIVING: 'Driving',
  ON_DUTY: 'On duty (not driving)',
};

const REST_STATUSES = new Set(['OFF_DUTY', 'SLEEPER_BERTH']);
const STOP_STATUSES = new Set(['ON_DUTY', 'OFF_DUTY', 'SLEEPER_BERTH']);

type SegmentMarker = {
  key: string;
  position: LatLngTuple;
  dayNumber: number;
  status: string;
  statusLabel: string;
  timeRange: string;
  address: string;
  activity?: string;
  remarks?: string;
  category: 'Rest' | 'Stop';
};

const distanceSquared = (a: LatLngTuple, b: LatLngTuple) => {
  const dLat = a[0] - b[0];
  const dLng = a[1] - b[1];
  return dLat * dLat + dLng * dLng;
};

const findNearestRouteIndex = (route: LatLngTuple[], point: LatLngTuple) => {
  if (route.length === 0) {
    return -1;
  }

  let bestIndex = 0;
  let bestDistance = Number.POSITIVE_INFINITY;

  route.forEach((candidate, index) => {
    const currentDistance = distanceSquared(candidate, point);
    if (currentDistance < bestDistance) {
      bestDistance = currentDistance;
      bestIndex = index;
    }
  });

  return bestDistance === Number.POSITIVE_INFINITY ? -1 : bestIndex;
};

const haversineMiles = (a: LatLngTuple, b: LatLngTuple) => {
  const toRadians = (value: number) => (value * Math.PI) / 180;
  const lat1 = toRadians(a[0]);
  const lat2 = toRadians(b[0]);
  const dLat = lat2 - lat1;
  const dLng = toRadians(b[1] - a[1]);
  const sinLat = Math.sin(dLat / 2);
  const sinLng = Math.sin(dLng / 2);
  const h = sinLat * sinLat + Math.cos(lat1) * Math.cos(lat2) * sinLng * sinLng;
  const c = 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
  const EARTH_RADIUS_MILES = 3958.8;
  return EARTH_RADIUS_MILES * c;
};

/**
 * Convert a minute duration into a rounded hours label for UI display.
 *
 * @param minutes - Total minutes to convert.
 * @returns Formatted string expressing the duration in hours.
 */
const formatMinutes = (minutes: number) => `${(minutes / 60).toFixed(1)} hrs`;

/**
 * Render the operational dashboard including metrics, maps, and route summaries.
 *
 * @returns Dashboard layout with navigation, metrics, and active route insight.
 */
export const DashboardScreen: React.FC = () => {
  const dispatch = useAppDispatch();
  const { user: sessionUser } = useAppSelector(selectAuthViewModel);
  const [activeNav, setActiveNav] = useState<NavSection>('overview');
  const [currentTime, setCurrentTime] = useState(() => new Date());
  const [activeRoute, setActiveRoute] = useState<ActiveRouteSummary | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState<string | null>(null);
  const [isCreateRouteModalOpen, setCreateRouteModalOpen] = useState(false);
  const [isLogsModalOpen, setLogsModalOpen] = useState(false);
  const isRoutesView = activeNav === 'routes';
  const hasActiveRoute = Boolean(activeRoute);

  /**
   * Fetch the latest active route summary for display panels.
   *
   * @returns Promise resolving when the active route data is refreshed.
   */
  const loadActiveRoute = useCallback(async () => {
    setRouteLoading(true);
    setRouteError(null);
    try {
      const summary = await RoutesService.fetchActiveRouteSummary();
      setActiveRoute(summary);
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : 'Unable to load active route right now.';
      setRouteError(message);
      setActiveRoute(null);
    } finally {
      setRouteLoading(false);
    }
  }, []);

  const handleCloseCreateRoute = useCallback(() => {
    setCreateRouteModalOpen(false);
  }, []);

  const handleCreateRouteOverlayClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (event.target === event.currentTarget) {
        handleCloseCreateRoute();
      }
    },
    [handleCloseCreateRoute],
  );

  const handleCloseLogsModal = useCallback(() => {
    setLogsModalOpen(false);
    void loadActiveRoute();
  }, [loadActiveRoute]);

  const handleLogsOverlayClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (event.target === event.currentTarget) {
        handleCloseLogsModal();
      }
    },
    [handleCloseLogsModal],
  );

  const handleRouteCreated = useCallback(() => {
    setActiveNav('routes');
    void loadActiveRoute();
  }, [loadActiveRoute]);

  useEffect(() => {
    const updateTime = () => setCurrentTime(new Date());
    updateTime();

    const interval = window.setInterval(updateTime, 60_000);

    return () => {
      window.clearInterval(interval);
    };
  }, []);

  const userName = useMemo(() => {
    const first = sessionUser?.first_name ?? '';
    const last = sessionUser?.last_name ?? '';
    return [first, last].filter(Boolean).join(' ') || sessionUser?.email || 'Planner';
  }, [sessionUser]);

  const formattedDate = useMemo(() => {
    return new Intl.DateTimeFormat('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    }).format(currentTime);
  }, [currentTime]);

  const formattedTime = useMemo(() => {
    return new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    }).format(currentTime);
  }, [currentTime]);

  const activeRouteLogs = useMemo(() => {
    if (!activeRoute?.logs) {
      return [] as ActiveRouteSummary['logs'];
    }

    return [...activeRoute.logs].sort((a, b) => a.dayNumber - b.dayNumber);
  }, [activeRoute]);

  const timelineStatusLabel = useMemo(() => {
    if (routeLoading) {
      return 'Loading driver logs…';
    }

    if (routeError) {
      return 'Unable to load driver logs';
    }

    if (!activeRoute) {
      return 'No active route available';
    }

    return activeRouteLogs.length > 0 ? 'Driver logs for the active route' : 'No driver logs recorded for this route yet';
  }, [routeLoading, routeError, activeRoute, activeRouteLogs.length]);

  /**
   * Sign the current user out and notify them of the result.
   *
   * @returns Promise resolving when the logout attempt finishes.
   */
  const handleLogout = async () => {
    try {
      await dispatch(logoutUser()).unwrap();
      dispatch(resetAuthError());
      dispatch(pushNotification({ message: 'Signed out', variant: 'info' }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to sign out';
      dispatch(pushNotification({ message, variant: 'error' }));
    }
  };

  /**
   * Navigate to the route creation screen while guarding concurrent fetches.
   */
  const handlePlanRoute = () => {
    if (routeLoading) {
      dispatch(
        pushNotification({
          message: 'Still checking active route status. Please try again in a moment.',
          variant: 'info',
        }),
      );
      return;
    }

    if (hasActiveRoute) {
      dispatch(
        pushNotification({
          message: 'New routes start in Planned status even while another is in progress.',
          variant: 'info',
        }),
      );
    }
    setCreateRouteModalOpen(true);
  };

  /**
   * Navigate to the logs management screen for the current user.
   */
  const handleManageLogs = () => {
    setLogsModalOpen(true);
  };

  useEffect(() => {
    void loadActiveRoute();
  }, [loadActiveRoute]);

  useEffect(() => {
    if (!isCreateRouteModalOpen && !isLogsModalOpen) {
      return undefined;
    }

    const { body } = document;
    const previousOverflow = body.style.overflow;
    body.style.overflow = 'hidden';

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (isLogsModalOpen) {
          handleCloseLogsModal();
          return;
        }
        if (isCreateRouteModalOpen) {
          handleCloseCreateRoute();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isCreateRouteModalOpen, isLogsModalOpen, handleCloseCreateRoute, handleCloseLogsModal]);

  const formattedDistance = useMemo(() => {
    if (!activeRoute?.totalDistanceMiles) return '—';
    return `${activeRoute.totalDistanceMiles.toFixed(1)} mi`;
  }, [activeRoute?.totalDistanceMiles]);

  const formattedDuration = useMemo(() => {
    if (!activeRoute?.totalDurationHours) return '—';
    return `${activeRoute.totalDurationHours.toFixed(1)} hrs`;
  }, [activeRoute?.totalDurationHours]);

  const plannedRoutePath: LatLngTuple[] = useMemo(() => {
    if (!activeRoute?.routePolyline) {
      return [];
    }

    try {
      return polyline
        .decode(activeRoute.routePolyline)
        .map(([lat, lng]: [number, number]) => [lat, lng] as LatLngTuple);
    } catch (error) {
      return [];
    }
  }, [activeRoute?.routePolyline]);

  const mapCenter: LatLngExpression | null = useMemo(() => {
    const candidate = activeRoute?.logs
      ?.flatMap((log) => log.segments ?? [])
      .map((segment) => segment.location)
      .find((location) => {
        if (!location) {
          return false;
        }

        try {
          const parsed = JSON.parse(location);
          return typeof parsed.lat === 'number' && typeof parsed.lng === 'number';
        } catch (error) {
          return false;
        }
      });

    if (candidate) {
      const parsed = JSON.parse(candidate) as { lat: number; lng: number };
      return [parsed.lat, parsed.lng];
    }

    if (plannedRoutePath.length > 0) {
      return plannedRoutePath[0];
    }

    if (activeRoute?.startLocation?.lat && activeRoute?.startLocation?.lng) {
      return [activeRoute.startLocation.lat, activeRoute.startLocation.lng];
    }

    return null;
  }, [activeRoute, plannedRoutePath]);

  const startPosition: LatLngExpression | null = useMemo(() => {
    if (!activeRoute?.startLocation?.lat || !activeRoute.startLocation.lng) {
      return null;
    }

    return [activeRoute.startLocation.lat, activeRoute.startLocation.lng];
  }, [activeRoute?.startLocation?.lat, activeRoute?.startLocation?.lng]);

  const pickupPosition: LatLngExpression | null = useMemo(() => {
    if (!activeRoute?.pickupLocation?.lat || !activeRoute.pickupLocation.lng) {
      return null;
    }

    return [activeRoute.pickupLocation.lat, activeRoute.pickupLocation.lng];
  }, [activeRoute?.pickupLocation?.lat, activeRoute?.pickupLocation?.lng]);

  const dropoffPosition: LatLngExpression | null = useMemo(() => {
    if (!activeRoute?.dropoffLocation?.lat || !activeRoute.dropoffLocation.lng) {
      return null;
    }

    return [activeRoute.dropoffLocation.lat, activeRoute.dropoffLocation.lng];
  }, [activeRoute?.dropoffLocation?.lat, activeRoute?.dropoffLocation?.lng]);

  const driverPolyline: LatLngTuple[] = useMemo(() => {
    if (!activeRoute?.logs) {
      return [];
    }

    const points: LatLngTuple[] = [];

    const sortedLogs = [...activeRoute.logs].sort((a, b) => a.dayNumber - b.dayNumber);

    sortedLogs.forEach((log) => {
      const sortedSegments = [...(log.segments ?? [])].sort((a, b) => {
        const aStart = a.startTime ?? '';
        const bStart = b.startTime ?? '';
        return aStart.localeCompare(bStart);
      });

      sortedSegments.forEach((segment) => {
        if (!segment.location) {
          return;
        }

        try {
          const parsed = JSON.parse(segment.location) as { lat?: number; lng?: number };
          if (typeof parsed.lat === 'number' && typeof parsed.lng === 'number') {
            points.push([parsed.lat, parsed.lng]);
          }
        } catch (error) {
          /* noop */
        }
      });
    });

    return points;
  }, [activeRoute?.logs]);

  const activeDriverMarker: LatLngExpression | null = useMemo(() => {
    if (driverPolyline.length === 0) {
      return null;
    }

    return driverPolyline[driverPolyline.length - 1];
  }, [driverPolyline]);

  const segmentMarkers: SegmentMarker[] = useMemo(() => {
    if (!activeRoute?.logs) {
      return [];
    }

    const markers: SegmentMarker[] = [];

    activeRoute.logs.forEach((log) => {
      log.segments?.forEach((segment, index) => {
        if (!segment.location) {
          return;
        }

        let parsed: { lat?: number; lng?: number; address?: string } | null = null;
        try {
          parsed = JSON.parse(segment.location);
        } catch (error) {
          parsed = null;
        }

        if (!parsed || typeof parsed.lat !== 'number' || typeof parsed.lng !== 'number') {
          return;
        }

        if (!STOP_STATUSES.has(segment.status)) {
          return;
        }

        const statusLabel = SEGMENT_STATUS_LABELS[segment.status] ?? segment.status.replaceAll('_', ' ').toLowerCase();
        const category = REST_STATUSES.has(segment.status) ? 'Rest' : 'Stop';
        const start = segment.startTime ? segment.startTime.slice(0, 5) : '';
        const end = segment.endTime ? segment.endTime.slice(0, 5) : '';
        const timeRange = start && end ? `${start} → ${end}` : start || end;
        const address = parsed.address && typeof parsed.address === 'string'
          ? parsed.address
          : `${parsed.lat.toFixed(4)}, ${parsed.lng.toFixed(4)}`;

        markers.push({
          key: `${log.id}-${segment.id ?? index}`,
          position: [parsed.lat, parsed.lng],
          dayNumber: log.dayNumber,
          status: segment.status,
          statusLabel,
          timeRange,
          address,
          activity: segment.activity || undefined,
          remarks: segment.remarks || undefined,
          category,
        });
      });
    });

    return markers;
  }, [activeRoute?.logs]);

  const drivenRoutePath: LatLngTuple[] = useMemo(() => {
    if (plannedRoutePath.length < 2 || driverPolyline.length === 0) {
      return [];
    }

    const nearestIndices = driverPolyline
      .map((point) => findNearestRouteIndex(plannedRoutePath, point))
      .filter((index) => index >= 0);

    if (nearestIndices.length === 0) {
      return [];
    }

    const furthestIndex = Math.max(...nearestIndices);
    const progressSegment = plannedRoutePath.slice(0, furthestIndex + 1);

    const lastDriverPoint = driverPolyline[driverPolyline.length - 1];
    const lastRoutePoint = plannedRoutePath[nearestIndices[nearestIndices.length - 1]];

    if (lastRoutePoint && distanceSquared(lastRoutePoint, lastDriverPoint) > 1e-8) {
      progressSegment.push(lastDriverPoint);
    }

    return progressSegment;
  }, [plannedRoutePath, driverPolyline]);

  const drivenMiles = useMemo(() => {
    const path: LatLngTuple[] = [];

    if (Array.isArray(startPosition)) {
      path.push(startPosition as LatLngTuple);
    }

    path.push(...driverPolyline);

    if (path.length < 2) {
      return 0;
    }

    return path.reduce((total, point, index) => {
      if (index === 0) {
        return total;
      }

      return total + haversineMiles(path[index - 1], point);
    }, 0);
  }, [startPosition, driverPolyline]);

  const fuelWarning = drivenMiles >= 900;
  const distanceValue = !activeRoute ? '—' : `${drivenMiles.toFixed(1)} mi`;
  const distanceStatus = !activeRoute
    ? 'Awaiting active route'
    : drivenMiles >= 1000
      ? 'Refuel immediately'
      : fuelWarning
        ? 'Approaching 1,000 mi — plan fuel stop'
        : 'Fuel range nominal';

  return (
    <div className={styles.screen}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandBadge}>RP</span>
          <div>
            <p>Route Planner</p>
            <small>Operations control</small>
          </div>
        </div>

        <nav className={styles.nav}>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`${styles.navItem} ${activeNav === item.id ? styles.navItemActive : ''}`}
              onClick={() => setActiveNav(item.id)}
            >
              <div>
                <span>{item.label}</span>
                <small>{item.description}</small>
              </div>
            </button>
          ))}
        </nav>

        <div className={styles.sidebarFooter}>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={handlePlanRoute}
            disabled={routeLoading}
          >
            Create route
          </button>
          <button type="button" className={styles.tertiaryButton} onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </aside>

      <section className={styles.content}>
        <header className={styles.header}>
          <div>
            <p className={styles.subtle}>Welcome back,</p>
            <h1>{userName}</h1>
          </div>
          <div className={styles.headerMeta}>
            <span>{formattedDate}</span>
            <span className={styles.timeBadge}>{formattedTime}</span>
          </div>
        </header>

        {!isRoutesView && (
          <div className={styles.metricsGrid}>
            {METRICS.map((metric) => (
              <article
                key={metric.id}
                className={`${styles.metricCard} ${
                  metric.id === 'distance' && fuelWarning ? styles.metricCardFuelAlert : ''
                }`}
              >
                <p className={styles.metricLabel}>
                  {metric.id === 'distance' ? 'Total miles travelled' : metric.label}
                </p>
                <h2>{metric.id === 'distance' ? distanceValue : metric.value}</h2>
                <span>{metric.id === 'distance' ? distanceStatus : metric.delta}</span>
              </article>
            ))}
          </div>
        )}

        {isRoutesView ? (
          <RoutesListScreen onStatusUpdated={loadActiveRoute} />
        ) : (
          <div className={styles.panels}>
            <article className={`${styles.panel} ${styles.activeRoutePanel}`}>
            <header>
              <div>
                <h3>Active route</h3>
                <span>
                  {routeLoading
                    ? 'Loading live route data…'
                    : activeRoute
                    ? `${activeRoute.tractorNumber} • ${activeRoute.shipperName}`
                    : 'No active route at the moment'}
                </span>
              </div>
              <div className={styles.routeActions}>
                <button type="button" onClick={handleManageLogs} disabled={!activeRoute}>
                  Manage logs
                </button>
              </div>
            </header>

            {routeError && <div className={styles.routeError}>{routeError}</div>}

            {!routeLoading && !routeError && !activeRoute && (
              <div className={styles.routeEmpty}>
                <p>No active route is currently running.</p>
              </div>
            )}

            {!routeLoading && activeRoute && (
              <div className={styles.routeSummaryStack}>
                <div className={styles.routeDetails}>
                  <dl className={styles.routeMeta}>
                    <div className={styles.routeMetaItem}>
                      <dt>Tractor</dt>
                      <dd>{activeRoute.tractorNumber}</dd>
                    </div>
                    <div className={styles.routeMetaItem}>
                      <dt>Trailers</dt>
                      <dd>{activeRoute.trailerNumbers.join(', ') || '—'}</dd>
                    </div>
                    <div className={styles.routeMetaItem}>
                      <dt>Carriers</dt>
                      <dd>{activeRoute.carrierNames.join(', ') || '—'}</dd>
                    </div>
                    <div className={styles.routeMetaItem}>
                      <dt>Shipper</dt>
                      <dd>{activeRoute.shipperName}</dd>
                    </div>
                    <div className={styles.routeMetaItem}>
                      <dt>Commodity</dt>
                      <dd>{activeRoute.commodity}</dd>
                    </div>
                    <div className={styles.routeMetaItem}>
                      <dt>Total distance</dt>
                      <dd>{formattedDistance}</dd>
                    </div>
                    <div className={styles.routeMetaItem}>
                      <dt>Estimated duration</dt>
                      <dd>{formattedDuration}</dd>
                    </div>
                    <div className={styles.routeMetaItem}>
                      <dt>Driving hours (cumulative)</dt>
                      <dd>{activeRoute.totalDrivingHours.toFixed(2)} hrs</dd>
                    </div>
                    <div className={styles.routeMetaItem}>
                      <dt>On duty hours (cumulative)</dt>
                      <dd>{activeRoute.totalOnDutyHours.toFixed(2)} hrs</dd>
                    </div>
                  </dl>
                </div>

              </div>
            )}
          </article>

          <article className={`${styles.panel} ${styles.timelinePanel}`}>
            <header>
              <div>
                <h3>Today&apos;s timeline</h3>
                <span>{timelineStatusLabel}</span>
              </div>
            </header>
            {routeLoading ? (
              <p className={styles.timelineMessage}>Loading driver logs…</p>
            ) : routeError ? (
              <p className={styles.timelineMessage}>{routeError}</p>
            ) : !activeRoute ? (
              <p className={styles.timelineMessage}>No active route available.</p>
            ) : activeRouteLogs.length === 0 ? (
              <p className={styles.timelineMessage}>No driver logs recorded for this route yet.</p>
            ) : (
              <ul className={styles.timeline}>
                {activeRouteLogs.map((log) => (
                  <li key={log.id} className={styles.timelineItem}>
                    <span className={styles.timelineTime}>Day {log.dayNumber}</span>
                    <div className={styles.timelineDetail}>
                      <p>{new Date(log.logDate).toLocaleDateString()}</p>
                      <small>
                        {`${formatMinutes(log.totalDrivingMinutes)} driving · ${formatMinutes(log.totalOnDutyMinutes)} on duty`}
                      </small>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </article>

          <article className={`${styles.panel} ${styles.mapPanel}`}>
            <header>
              <div>
                <h3>Map coverage</h3>
                <span>
                  {activeRoute
                    ? driverPolyline.length > 0
                      ? `${driverPolyline.length} position updates received`
                      : 'No live positions available yet'
                    : 'Awaiting active route to display map'}
                </span>
              </div>
            </header>
            <div className={styles.mapContainer}>
              {!activeRoute || !mapCenter ? (
                <div className={styles.mapFallback}>
                  <span>
                    {activeRoute
                      ? 'Waiting for driver telemetry…'
                      : 'No route in progress. Start a route to view live coverage.'}
                  </span>
                </div>
              ) : (
                <MapContainer center={mapCenter} zoom={6} className={styles.mapLeaflet} zoomControl={false}>
                  <TileLayer
                    attribution="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors"
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  {plannedRoutePath.length > 1 && (
                    <Polyline positions={plannedRoutePath} color="#f97316" weight={5} opacity={0.85} />
                  )}
                  {drivenRoutePath.length > 1 && (
                    <Polyline
                      positions={drivenRoutePath}
                      color="#3b82f6"
                      weight={6}
                      opacity={0.9}
                      lineCap="round"
                      lineJoin="round"
                    />
                  )}
                  {driverPolyline.length > 1 && (
                    <Polyline positions={driverPolyline} color="#60a5fa" weight={3} opacity={0.7} dashArray="8 8" />
                  )}
                  {segmentMarkers.map((marker) => (
                    <Marker key={marker.key} position={marker.position} icon={segmentMarkerIcon}>
                      <Popup className={styles.segmentPopup} closeButton={false} autoPan={false}>
                        <strong>{marker.category} • Day {marker.dayNumber}</strong>
                        <span>{marker.statusLabel}</span>
                        {marker.timeRange && <span>Time: {marker.timeRange}</span>}
                        <span>Location: {marker.address}</span>
                        {marker.activity && <span>Activity: {marker.activity}</span>}
                        {marker.remarks && <em>Notes: {marker.remarks}</em>}
                      </Popup>
                    </Marker>
                  ))}
                  {startPosition && <Marker position={startPosition} />}
                  {pickupPosition && <Marker position={pickupPosition} />}
                  {dropoffPosition && <Marker position={dropoffPosition} />}
                  {activeDriverMarker && <Marker position={activeDriverMarker} />}
                </MapContainer>
              )}
            </div>
          </article>
          </div>
        )}
      </section>

      {isCreateRouteModalOpen && (
        <div
          className={styles.modalOverlay}
          onClick={handleCreateRouteOverlayClick}
          role="dialog"
          aria-modal="true"
          aria-label="Create new route"
        >
          <div className={styles.modalContent} onClick={(event) => event.stopPropagation()}>
            <button
              type="button"
              className={styles.modalCloseButton}
              onClick={handleCloseCreateRoute}
              aria-label="Close create route form"
            >
              ×
            </button>
            <CreateRouteScreen onDismiss={handleCloseCreateRoute} onRouteCreated={handleRouteCreated} />
          </div>
        </div>
      )}

      {isLogsModalOpen && (
        <div
          className={styles.modalOverlay}
          onClick={handleLogsOverlayClick}
          role="dialog"
          aria-modal="true"
          aria-label="Manage driver logs"
        >
          <div
            className={`${styles.modalContent} ${styles.logsModalContent}`}
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              className={styles.modalCloseButton}
              onClick={handleCloseLogsModal}
              aria-label="Close driver logs"
            >
              ×
            </button>
            <LogsScreen asModal onDismiss={handleCloseLogsModal} />
          </div>
        </div>
      )}
    </div>
  );
};
