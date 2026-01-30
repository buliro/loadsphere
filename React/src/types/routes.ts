import type { RawDriverLog } from './logs';

export type TripStatus = 'PLANNED' | 'IN_PROGRESS' | 'COMPLETED';

export const ROUTE_STATUS_DICTIONARY: Record<'planned' | 'inProgress' | 'completed', TripStatus> = {
  planned: 'PLANNED',
  inProgress: 'IN_PROGRESS',
  completed: 'COMPLETED',
};

export const TRIP_STATUS_LABELS: Record<TripStatus, string> = {
  PLANNED: 'Planned',
  IN_PROGRESS: 'In progress',
  COMPLETED: 'Completed',
};

export type LocationJSON = {
  lat?: number | null;
  lng?: number | null;
  address?: string | null;
};

export type RawTripRoute = {
  totalDistance?: number | null;
  estimatedDuration?: number | null;
  polyline?: string | null;
};

export type RawTrip = {
  id: string;
  status: string;
  tractorNumber?: string | null;
  trailerNumbers?: string[] | null;
  carrierNames?: string[] | null;
  mainOfficeAddress?: string | null;
  homeTerminalAddress?: string | null;
  coDriverName?: string | null;
  shipperName?: string | null;
  commodity?: string | null;
  startLocation?: unknown;
  pickupLocation?: unknown;
  dropoffLocation?: unknown;
  route?: RawTripRoute | null;
  logs?: RawDriverLog[] | null;
  createdAt?: string | null;
};

export type RouteListTrip = {
  id: string;
  status: TripStatus;
  tractorNumber: string;
  trailerNumbers: string[];
  carrierNames: string[];
  shipperName: string;
  commodity: string;
  startLocation: LocationJSON | null;
  pickupLocation: LocationJSON | null;
  dropoffLocation: LocationJSON | null;
  createdAt: string;
};

export type ActiveRouteSummary = {
  id: string;
  tractorNumber: string;
  trailerNumbers: string[];
  carrierNames: string[];
  mainOfficeAddress: string;
  homeTerminalAddress: string;
  coDriverName: string | null;
  shipperName: string;
  commodity: string;
  startLocation: LocationJSON | null;
  pickupLocation: LocationJSON | null;
  dropoffLocation: LocationJSON | null;
  totalDistanceMiles: number | null;
  totalDurationHours: number | null;
  routePolyline: string | null;
  logs: RawDriverLog[];
  totalDrivingHours: number;
  totalOnDutyHours: number;
  remainingCycleHours: number | null;
};

export type RouteFormState = {
  tractorNumber: string;
  trailerNumbers: string;
  carrierNames: string;
  mainOfficeAddress: string;
  homeTerminalAddress: string;
  coDriverName: string;
  shipperName: string;
  commodity: string;
  startAddress: string;
  pickupAddress: string;
  dropoffAddress: string;
  cycleHoursUsed: string;
};
