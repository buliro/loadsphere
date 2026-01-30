const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

const buildUrl = (path: string) => {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }

  if (!path.startsWith('/')) {
    return `${API_BASE}/${path}`;
  }

  return `${API_BASE}${path}`;
};

export type RestOptions = RequestInit & {
  skipJsonAcceptHeader?: boolean;
};

const DEFAULT_HEADERS: HeadersInit = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
};

export const restRequest = async (path: string, options: RestOptions = {}): Promise<Response> => {
  const { skipJsonAcceptHeader = false, headers, ...rest } = options;

  const mergedHeaders: HeadersInit = {
    ...(skipJsonAcceptHeader ? {} : DEFAULT_HEADERS),
    ...(headers ?? {}),
  };

  const requestInit: RequestInit = {
    credentials: 'include',
    ...rest,
    headers: mergedHeaders,
  };

  return fetch(buildUrl(path), requestInit);
};

export const restJson = async <T>(path: string, options?: RestOptions): Promise<{ response: Response; data: T | null }> => {
  const response = await restRequest(path, options);

  let data: T | null = null;
  try {
    data = (await response.json()) as T;
  } catch (error) {
    data = null;
  }

  return { response, data };
};
