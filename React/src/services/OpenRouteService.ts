import { restJson } from './rest';

export type OpenRouteSuggestion = {
  id: string;
  label: string;
  address: string;
  lat: number;
  lng: number;
  context?: {
    country?: string | null;
    region?: string | null;
    county?: string | null;
    locality?: string | null;
  } | null;
};

type SearchLocationsResponse = {
  results: OpenRouteSuggestion[];
  detail?: string;
};

type RouteDistanceResponse = {
  total_distance_miles: number;
  total_duration_hours: number;
  polyline: string | null;
  segments: Array<{
    distance_miles: number;
    duration_minutes: number;
    duration_hours: number;
  }>;
  detail?: string;
};

const buildSearchUrl = (query: string, limit: number) => {
  const params = new URLSearchParams();
  params.set('q', query);
  params.set('limit', String(limit));
  return `/api/openroute/search/?${params.toString()}`;
};

const buildRouteUrl = () => '/api/openroute/route/';

export const OpenRouteService = {
  async searchLocations(query: string, limit = 5): Promise<OpenRouteSuggestion[]> {
    const trimmed = query.trim();
    if (!trimmed) {
      return [];
    }

    const { response, data } = await restJson<SearchLocationsResponse>(buildSearchUrl(trimmed, limit), {
      method: 'GET',
    });

    if (!response.ok) {
      const message = data?.detail ?? `OpenRouteService search failed with status ${response.status}`;
      throw new Error(message);
    }

    return data?.results ?? [];
  },
  async planRoute(locations: Array<{ lat: number; lng: number }>): Promise<RouteDistanceResponse> {
    if (locations.length < 2) {
      throw new Error('At least two locations are required to calculate a route.');
    }

    const { response, data } = await restJson<RouteDistanceResponse>(buildRouteUrl(), {
      method: 'POST',
      body: JSON.stringify({ locations }),
    });

    if (!response.ok || !data) {
      const message = data?.detail ?? `Routing request failed with status ${response.status}`;
      throw new Error(message);
    }

    return data;
  },
};
