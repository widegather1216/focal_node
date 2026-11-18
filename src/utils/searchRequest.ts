import { extractResponseErrorMessage } from './apiError.ts';
import type { PhotoSummary, SearchFilters } from '../types/photo.ts';

export type SearchFetchFn = typeof fetch;

export interface FetchPhotosRequestOptions {
  baseUrl: string;
  limit: number;
  offset: number;
  folder: string | null;
  signal?: AbortSignal;
  fetchImpl?: SearchFetchFn;
}

export interface PostJsonRequestOptions {
  baseUrl: string;
  endpoint: string;
  payload: Record<string, unknown>;
  errorContext: string;
  signal?: AbortSignal;
  fetchImpl?: SearchFetchFn;
}

export interface SearchPhotosRequestOptions {
  baseUrl: string;
  query: string | undefined;
  filters: SearchFilters | undefined;
  limit: number;
  offset: number;
  folder?: string | null;
  signal?: AbortSignal;
  fetchImpl?: SearchFetchFn;
}

/**
 * Fetches paginated gallery photos, forwarding an optional AbortSignal to fetch.
 */
export async function fetchPhotosRequest(
  options: FetchPhotosRequestOptions,
): Promise<PhotoSummary[]> {
  const { baseUrl, limit, offset, folder, signal, fetchImpl = fetch } = options;
  let requestUrl = `${baseUrl}/api/photos?limit=${limit}&offset=${offset}`;
  if (folder) {
    requestUrl += `&parent_dir=${encodeURIComponent(folder)}`;
  }
  const response = signal ? await fetchImpl(requestUrl, { signal }) : await fetchImpl(requestUrl);
  if (!response.ok) {
    const errorMessage = await extractResponseErrorMessage(response, 'Failed to fetch photos');
    throw new Error(errorMessage);
  }
  return response.json();
}

/**
 * Sends a JSON POST request with optional AbortSignal cancellation support.
 */
export async function postJsonRequest<T>(options: PostJsonRequestOptions): Promise<T> {
  const {
    baseUrl,
    endpoint,
    payload,
    errorContext,
    signal,
    fetchImpl = fetch,
  } = options;
  const requestInit: RequestInit = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    ...(signal ? { signal } : {}),
  };
  const response = await fetchImpl(`${baseUrl}${endpoint}`, requestInit);
  if (!response.ok) {
    const errorMessage = await extractResponseErrorMessage(response, errorContext);
    throw new Error(errorMessage);
  }
  return response.json();
}

export interface SearchRequestSpec {
  endpoint: '/api/search' | '/api/search/similar';
  payload: Record<string, unknown>;
  errorContext: string;
}

/**
 * Builds the endpoint, payload, and error context for standard or similar photo search.
 */
export function buildSearchRequestSpec(
  query: string | undefined,
  filters: SearchFilters | undefined,
  limit: number,
  offset: number,
  folder?: string | null,
): SearchRequestSpec {
  const cleanQuery = query ? query.trim() : undefined;
  const folderPayload = folder ? { parent_dir: folder } : {};

  if (cleanQuery && cleanQuery.startsWith('similar:')) {
    const photoId = cleanQuery.slice('similar:'.length);
    return {
      endpoint: '/api/search/similar',
      payload: { photo_id: photoId, filters, limit, offset, ...folderPayload },
      errorContext: 'Failed to search similar photos',
    };
  }

  return {
    endpoint: '/api/search',
    payload: { query: cleanQuery, filters, limit, offset, ...folderPayload },
    errorContext: 'Failed to search photos',
  };
}

/**
 * Routes semantic/EXIF or K-NN similar photo searches with optional AbortSignal forwarding.
 */
export async function searchPhotosRequest(
  options: SearchPhotosRequestOptions,
): Promise<PhotoSummary[]> {
  const {
    baseUrl,
    query,
    filters,
    limit,
    offset,
    folder,
    signal,
    fetchImpl = fetch,
  } = options;
  const spec = buildSearchRequestSpec(query, filters, limit, offset, folder);
  return postJsonRequest<PhotoSummary[]>({
    baseUrl,
    endpoint: spec.endpoint,
    payload: spec.payload,
    errorContext: spec.errorContext,
    signal,
    fetchImpl,
  });
}
