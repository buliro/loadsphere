import { graphqlRequest } from './graphql';
import type {
  ActiveRouteSummary,
  LocationJSON,
  RawTrip,
  RouteListTrip,
  TripStatus,
} from '../types/routes';

const ROUTE_QUERIES = {
  activeTrip: `
    query DashboardActiveTrip {
      myTrips(status: "IN_PROGRESS") {
        id
        status
        tractorNumber
        trailerNumbers
        carrierNames
        mainOfficeAddress
        homeTerminalAddress
        coDriverName
        shipperName
        commodity
        startLocation
        pickupLocation
        dropoffLocation
        route {
          polyline
          totalDistance
          estimatedDuration
        }
        logs {
          id
          dayNumber
          logDate
          notes
          totalDistanceMiles
          totalDrivingMinutes
          totalOnDutyMinutes
          totalOffDutyMinutes
          totalSleeperMinutes
          segments {
            id
            status
            startTime
            endTime
            location
            activity
            remarks
          }
        }
      }
    }
  `,
  allTrips: `
    query RoutesList {
      myTrips {
        id
        status
        tractorNumber
        trailerNumbers
        carrierNames
        shipperName
        commodity
        startLocation
        pickupLocation
        dropoffLocation
        createdAt
      }
    }
  `,
  updateStatus: `
    mutation UpdateTripStatus($tripId: ID!, $status: String!) {
      updateTripStatus(tripId: $tripId, status: $status) {
        success
        errors
        trip {
          id
          status
        }
      }
    }
  `,
  deleteTrip: `
    mutation DeleteTrip($tripId: ID!) {
      deleteTrip(tripId: $tripId) {
        success
        errors
      }
    }
  `,
} as const;

/**
 * Convert various GraphQL location representations into a consistent JSON shape.
 *
 * @param value - Raw location value coming from the API response.
 * @returns LocationJSON object or null when the value cannot be interpreted.
 */
const parseLocation = (value: unknown): LocationJSON | null => {
  if (!value) {
    return null;
  }

  if (typeof value === 'string') {
    try {
      return JSON.parse(value) as LocationJSON;
    } catch (error) {
      return { address: value };
    }
  }

  if (typeof value === 'object') {
    return value as LocationJSON;
  }

  return null;
};

/**
 * Coerce string or array inputs into a trimmed array of strings.
 *
 * @param value - Incoming value that may represent a list of strings.
 * @returns Array of non-empty strings.
 */
const normaliseStringArray = (value: unknown): string[] => {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value
      .map((entry) => (typeof entry === 'string' ? entry.trim() : ''))
      .filter((entry): entry is string => Boolean(entry));
  }

  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) {
      return [];
    }

    try {
      const parsed = JSON.parse(trimmed);
      return normaliseStringArray(parsed);
    } catch (error) {
      if (trimmed.includes(',')) {
        return trimmed
          .split(',')
          .map((part) => part.trim())
          .filter(Boolean);
      }

      return [trimmed];
    }
  }

  return [];
};

/**
 * Transform a raw GraphQL trip response into an ActiveRouteSummary model.
 *
 * @param trip - Raw trip object from the API.
 * @returns Normalised ActiveRouteSummary or null when input is undefined.
 */
const normaliseTrip = (trip: RawTrip | undefined): ActiveRouteSummary | null => {
  if (!trip) {
    return null;
  }

  const logs = trip.logs ?? [];
  const totalDrivingMinutes = logs.reduce((sum, log) => sum + (log.totalDrivingMinutes ?? 0), 0);
  const totalOnDutyMinutes = logs.reduce((sum, log) => sum + (log.totalOnDutyMinutes ?? 0), 0);

  return {
    id: trip.id,
    tractorNumber: trip.tractorNumber?.trim() || '—',
    trailerNumbers: normaliseStringArray(trip.trailerNumbers),
    carrierNames: normaliseStringArray(trip.carrierNames),
    mainOfficeAddress: trip.mainOfficeAddress?.trim() || '—',
    homeTerminalAddress: trip.homeTerminalAddress?.trim() || '—',
    coDriverName: trip.coDriverName?.trim() || null,
    shipperName: trip.shipperName?.trim() || '—',
    commodity: trip.commodity?.trim() || '—',
    startLocation: parseLocation(trip.startLocation),
    pickupLocation: parseLocation(trip.pickupLocation),
    dropoffLocation: parseLocation(trip.dropoffLocation),
    totalDistanceMiles: trip.route?.totalDistance ?? null,
    totalDurationHours: trip.route?.estimatedDuration ?? null,
    routePolyline: trip.route?.polyline ?? null,
    logs,
    totalDrivingHours: Number((totalDrivingMinutes / 60).toFixed(2)),
    totalOnDutyHours: Number((totalOnDutyMinutes / 60).toFixed(2)),
    remainingCycleHours: null,
  };
};

export const RoutesService = {
  async fetchActiveRouteSummary(): Promise<ActiveRouteSummary | null> {
    /**
     * Retrieve the currently active in-progress trip summary for the dashboard.
     *
     * @returns Active route summary or null when no active trip exists.
     */
    const data = await graphqlRequest<{
      myTrips: RawTrip[];
    }>(ROUTE_QUERIES.activeTrip);

    const [activeTrip] = data?.myTrips ?? [];
    return normaliseTrip(activeTrip);
  },
  async fetchRoutesList(): Promise<RouteListTrip[]> {
    /**
     * Fetch all trips for the authenticated user in a list-friendly format.
     *
     * @returns Sorted array of RouteListTrip objects.
     */
    const data = await graphqlRequest<{ myTrips: RawTrip[] }>(ROUTE_QUERIES.allTrips);
    const trips = data?.myTrips ?? [];

    return trips
      .map((trip) => ({
        id: trip.id,
        status: (trip.status?.toUpperCase?.() as TripStatus) ?? 'PLANNED',
        tractorNumber: trip.tractorNumber?.trim() || '—',
        trailerNumbers: normaliseStringArray(trip.trailerNumbers),
        carrierNames: normaliseStringArray(trip.carrierNames),
        shipperName: trip.shipperName?.trim() || '—',
        commodity: trip.commodity?.trim() || '—',
        startLocation: parseLocation(trip.startLocation),
        pickupLocation: parseLocation(trip.pickupLocation),
        dropoffLocation: parseLocation(trip.dropoffLocation),
        createdAt: trip.createdAt ?? new Date().toISOString(),
      }))
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  },
  async updateRouteStatus(tripId: string, status: TripStatus): Promise<void> {
    /**
     * Request a status update for a specific trip.
     *
     * @param tripId - Identifier of the trip to mutate.
     * @param status - Desired status value to apply to the trip.
     * @returns Promise resolving when the update succeeds.
     * @throws Error when GraphQL mutation reports failure.
     */
    const response = await graphqlRequest<{
      updateTripStatus: { success: boolean; errors?: string[] | null };
    }>(ROUTE_QUERIES.updateStatus, {
      variables: { tripId, status },
    });

    if (!response?.updateTripStatus?.success) {
      const message = response?.updateTripStatus?.errors?.join('\n') || 'Unable to update trip status';
      throw new Error(message);
    }
  },
  async deleteRoute(tripId: string): Promise<void> {
    /**
     * Delete a planned trip from the user's account.
     *
     * @param tripId - Identifier of the trip to delete.
     * @returns Promise resolving when deletion succeeds.
     * @throws Error when the backend rejects the delete request.
     */
    const response = await graphqlRequest<{
      deleteTrip: { success: boolean; errors?: string[] | null };
    }>(ROUTE_QUERIES.deleteTrip, {
      variables: { tripId },
    });

    if (!response?.deleteTrip?.success) {
      const message = response?.deleteTrip?.errors?.join('\n') || 'Unable to delete trip';
      throw new Error(message);
    }
  },
  getRouteReportUrl(tripId: string, disposition: 'attachment' | 'inline' = 'attachment'): string {
    /**
     * Build the URL for fetching a trip PDF report with the desired disposition.
     *
     * @param tripId - Identifier of the trip whose report should be fetched.
     * @param disposition - Content disposition preference for the response.
     * @returns Fully qualified URL pointing to the PDF resource.
     */
    const url = new URL(`/api/routes/${tripId}/report.pdf`, window.location.origin);
    url.searchParams.set('disposition', disposition);
    return url.toString();
  },
  async downloadRouteReport(tripId: string): Promise<void> {
    /**
     * Initiate a browser download for the trip PDF report.
     *
     * @param tripId - Identifier of the trip whose report should be downloaded.
     * @returns Promise resolving once the download process has been triggered.
     * @throws Error when the HTTP request fails.
     */
    const response = await fetch(this.getRouteReportUrl(tripId, 'attachment'), {
      credentials: 'include',
    });

    if (!response.ok) {
      let errorMessage = 'Unable to download route report';
      const contentType = response.headers.get('Content-Type');
      if (contentType && contentType.includes('application/json')) {
        try {
          const payload = (await response.json()) as { detail?: string };
          if (payload.detail) {
            errorMessage = payload.detail;
          }
        } catch (error) {
          /* ignore JSON parse errors */
        }
      }
      throw new Error(errorMessage);
    }

    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition') ?? '';
    const filenameMatch = disposition.match(/filename="?([^";]+)"?/);
    const filename = filenameMatch?.[1] ?? `route_${tripId}_report.pdf`;

    const url = window.URL.createObjectURL(blob);
    try {
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } finally {
      window.URL.revokeObjectURL(url);
    }
  },
};
