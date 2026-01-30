const CSRF_COOKIE_NAME = 'csrftoken';

const CSRF_ENDPOINT = '/api/csrf/';

const parseCookies = () => {
  if (typeof document === 'undefined') {
    return {} as Record<string, string>;
  }

  return document.cookie.split(';').reduce<Record<string, string>>((accumulator, segment) => {
    const [rawName, ...rest] = segment.trim().split('=');
    if (!rawName) {
      return accumulator;
    }

    const name = decodeURIComponent(rawName);
    const value = decodeURIComponent(rest.join('=') ?? '');
    return { ...accumulator, [name]: value };
  }, {});
};

export const getCsrfToken = (): string | null => {
  const cookies = parseCookies();
  return cookies[CSRF_COOKIE_NAME] ?? null;
};

export const buildCsrfHeaders = async (headers?: HeadersInit) => {
  const token = await getCsrfToken();

  return {
    ...(headers ?? {}),
    ...(token ? { 'X-CSRFToken': token } : {}),
  } satisfies HeadersInit;
};

let inflightRequest: Promise<void> | null = null;

const requestCsrfToken = async () => {
  await fetch(CSRF_ENDPOINT, {
    credentials: 'include',
    headers: {
      Accept: 'application/json',
    },
  });
};

export const ensureCsrfToken = async (): Promise<void> => {
  if (getCsrfToken()) {
    return;
  }

  if (!inflightRequest) {
    inflightRequest = requestCsrfToken().finally(() => {
      inflightRequest = null;
    });
  }

  await inflightRequest;
};
