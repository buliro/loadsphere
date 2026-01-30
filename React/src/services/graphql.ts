type GraphQLOptions = {
  variables?: Record<string, unknown>;
  operationName?: string;
  headers?: HeadersInit;
  fetchOptions?: RequestInit;
};

const resolveGraphqlEndpoint = () => {
  const rawEndpoint = import.meta.env.VITE_GRAPHQL_URL ?? '/graphql/';
  if (rawEndpoint.endsWith('/')) {
    return rawEndpoint;
  }
  return `${rawEndpoint}/`;
};

const GRAPHQL_ENDPOINT = resolveGraphqlEndpoint();

import { ensureCsrfToken, buildCsrfHeaders } from './csrf';

export const graphqlRequest = async <TData = unknown>(
  query: string,
  options: GraphQLOptions = {},
) => {
  const { variables, operationName, headers, fetchOptions } = options;

  await ensureCsrfToken();
  const csrfHeaders = await buildCsrfHeaders({
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(headers ?? {}),
  });

  const response = await fetch(GRAPHQL_ENDPOINT, {
    method: 'POST',
    credentials: 'include',
    headers: csrfHeaders,
    body: JSON.stringify({ query, variables, operationName }),
    ...fetchOptions,
  });

  const rawBody = await response.text();
  let payload: { data?: TData; errors?: unknown };

  try {
    payload = JSON.parse(rawBody) as { data?: TData; errors?: unknown };
  } catch (parseError) {
    const error = new Error('Received an invalid response from the GraphQL server');
    (error as Error & { response?: Response; rawBody?: string }).response = response;
    (error as Error & { response?: Response; rawBody?: string }).rawBody = rawBody;
    throw error;
  }

  if (!response.ok || payload.errors) {
    const error = new Error('GraphQL request failed');
    (error as Error & { response?: Response; payload?: unknown }).response = response;
    (error as Error & { response?: Response; payload?: unknown }).payload = payload;
    throw error;
  }

  return payload.data as TData;
};
