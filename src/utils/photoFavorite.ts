import type { InfiniteData, Query, QueryClient, QueryKey } from '@tanstack/react-query';
import type { PhotoDetail, PhotoSummary, SearchFilters } from '../types/photo';

export type PhotosCacheData = InfiniteData<PhotoSummary[]> | PhotoSummary[];

export type ToggleFavoriteApi = (photoId: string) => Promise<{ id: string; is_favorite: boolean }>;

interface BaselinePhotosSnapshot {
  queryKey: QueryKey;
  cacheValue: PhotosCacheData;
  updatedAt: number;
}

interface BaselineDetailSnapshot {
  detailValue: PhotoDetail;
  updatedAt: number;
}

interface FavoriteFlightEntry {
  activeSeqs: Set<number>;
  nextSeq: number;
  optimisticFavorite: boolean | null;
  confirmedFavorite: boolean | null;
  hadBaseline: boolean;
  hadPendingDetailFetch: boolean;
  baselinePhotos: BaselinePhotosSnapshot[];
  baselineDetail: BaselineDetailSnapshot | null;
  tailPromise: Promise<unknown>;
}

export interface FavoriteMutationContext {
  photoId: string;
  seq: number;
}

const flightStatesByClient = new WeakMap<object, Map<string, FavoriteFlightEntry>>();

function getFlightMap(queryClient: QueryClient): Map<string, FavoriteFlightEntry> {
  let flightMap = flightStatesByClient.get(queryClient);
  if (!flightMap) {
    flightMap = new Map<string, FavoriteFlightEntry>();
    flightStatesByClient.set(queryClient, flightMap);
  }
  return flightMap;
}

function getOrCreateFlightEntry(
  flightMap: Map<string, FavoriteFlightEntry>,
  photoId: string,
): FavoriteFlightEntry {
  let entry = flightMap.get(photoId);
  if (!entry) {
    entry = {
      activeSeqs: new Set<number>(),
      nextSeq: 0,
      optimisticFavorite: null,
      confirmedFavorite: null,
      hadBaseline: false,
      hadPendingDetailFetch: false,
      baselinePhotos: [],
      baselineDetail: null,
      tailPromise: Promise.resolve(),
    };
    flightMap.set(photoId, entry);
  }
  return entry;
}

function findPhotoInCacheValue(
  cacheValue: PhotosCacheData | undefined,
  photoId: string,
): PhotoSummary | undefined {
  if (!cacheValue) return undefined;
  if (Array.isArray(cacheValue)) {
    return cacheValue.find((photo) => photo.id === photoId);
  }
  if (!('pages' in cacheValue) || !Array.isArray(cacheValue.pages)) {
    return undefined;
  }
  for (const page of cacheValue.pages) {
    const matched = page.find((photo) => photo.id === photoId);
    if (matched) return matched;
  }
  return undefined;
}

function resolveCurrentFavorite(queryClient: QueryClient, photoId: string): boolean | null {
  const detailValue = queryClient.getQueryData<PhotoDetail | null>(['photoDetail', photoId]);
  if (detailValue) {
    return detailValue.is_favorite;
  }
  const photosQueries = queryClient.getQueriesData<PhotosCacheData>({ queryKey: ['photos'] });
  for (const [, cacheValue] of photosQueries) {
    const matched = findPhotoInCacheValue(cacheValue, photoId);
    if (matched) return matched.is_favorite;
  }
  return null;
}

function buildUpdatedPhotosCacheValue(
  cacheValue: PhotosCacheData,
  photoId: string,
  nextFavorite: boolean,
): PhotosCacheData {
  if (Array.isArray(cacheValue)) {
    return cacheValue.map((photo) =>
      photo.id === photoId ? { ...photo, is_favorite: nextFavorite } : photo,
    );
  }
  return {
    ...cacheValue,
    pages: cacheValue.pages.map((page) =>
      page.map((photo) =>
        photo.id === photoId ? { ...photo, is_favorite: nextFavorite } : photo,
      ),
    ),
  };
}

function setQueryDataPreservingUpdatedAt<TValue>(
  queryClient: QueryClient,
  queryKey: QueryKey,
  nextValue: TValue,
  updatedAt: number | undefined,
): void {
  if (typeof updatedAt === 'number' && updatedAt > 0) {
    queryClient.setQueryData<TValue>(queryKey, nextValue, { updatedAt });
    return;
  }
  queryClient.setQueryData<TValue>(queryKey, nextValue);
}

function captureBaselineSnapshots(
  queryClient: QueryClient,
  photoId: string,
  entry: FavoriteFlightEntry,
): void {
  if (entry.hadBaseline) return;
  const photosQueries = queryClient.getQueriesData<PhotosCacheData>({ queryKey: ['photos'] });
  for (const [queryKey, cacheValue] of photosQueries) {
    if (!cacheValue || !findPhotoInCacheValue(cacheValue, photoId)) continue;
    const updatedAt = queryClient.getQueryState(queryKey)?.dataUpdatedAt ?? 0;
    entry.baselinePhotos.push({ queryKey, cacheValue, updatedAt });
  }
  const detailKey: QueryKey = ['photoDetail', photoId];
  const detailValue = queryClient.getQueryData<PhotoDetail | null>(detailKey);
  if (detailValue) {
    entry.baselineDetail = {
      detailValue,
      updatedAt: queryClient.getQueryState(detailKey)?.dataUpdatedAt ?? 0,
    };
  }
  entry.hadBaseline = true;
}

function applyFavoriteAcrossCaches(
  queryClient: QueryClient,
  photoId: string,
  nextFavorite: boolean,
): void {
  const detailKey: QueryKey = ['photoDetail', photoId];
  const detailValue = queryClient.getQueryData<PhotoDetail | null>(detailKey);
  if (detailValue && detailValue.is_favorite !== nextFavorite) {
    const detailUpdatedAt = queryClient.getQueryState(detailKey)?.dataUpdatedAt;
    setQueryDataPreservingUpdatedAt<PhotoDetail | null>(
      queryClient,
      detailKey,
      { ...detailValue, is_favorite: nextFavorite },
      detailUpdatedAt,
    );
  }
  const photosQueries = queryClient.getQueriesData<PhotosCacheData>({ queryKey: ['photos'] });
  for (const [queryKey, cacheValue] of photosQueries) {
    if (!cacheValue) continue;
    const matched = findPhotoInCacheValue(cacheValue, photoId);
    if (!matched || matched.is_favorite === nextFavorite) continue;
    const prevUpdatedAt = queryClient.getQueryState(queryKey)?.dataUpdatedAt;
    const nextCacheValue = buildUpdatedPhotosCacheValue(cacheValue, photoId, nextFavorite);
    setQueryDataPreservingUpdatedAt(queryClient, queryKey, nextCacheValue, prevUpdatedAt);
  }
}

function restoreBaselineSnapshots(
  queryClient: QueryClient,
  photoId: string,
  entry: FavoriteFlightEntry,
): void {
  for (const snapshot of entry.baselinePhotos) {
    setQueryDataPreservingUpdatedAt(
      queryClient,
      snapshot.queryKey,
      snapshot.cacheValue,
      snapshot.updatedAt,
    );
  }
  if (entry.baselineDetail) {
    setQueryDataPreservingUpdatedAt<PhotoDetail | null>(
      queryClient,
      ['photoDetail', photoId],
      entry.baselineDetail.detailValue,
      entry.baselineDetail.updatedAt,
    );
  }
}

function hasFavoriteFilter(queryKey: QueryKey): boolean {
  const maybeFilters = queryKey[3];
  if (typeof maybeFilters !== 'object' || maybeFilters === null) {
    return false;
  }
  return (maybeFilters as SearchFilters).is_favorite !== undefined;
}

function invalidateDependentQueries(
  queryClient: QueryClient,
  photoId: string,
  shouldInvalidateDetail: boolean,
): void {
  void queryClient.invalidateQueries({
    queryKey: ['photos'],
    predicate: (query: Query) => hasFavoriteFilter(query.queryKey),
  });
  const detailFetchStatus = queryClient.getQueryState(['photoDetail', photoId])?.fetchStatus;
  if (shouldInvalidateDetail || detailFetchStatus === 'fetching') {
    void queryClient.invalidateQueries({ queryKey: ['photoDetail', photoId] });
  }
}

async function cancelPopulatedQueries(queryClient: QueryClient, photoId: string): Promise<void> {
  await Promise.all([
    queryClient.cancelQueries({
      queryKey: ['photos'],
      predicate: (query: Query) => query.state.data !== undefined,
    }),
    queryClient.cancelQueries({
      queryKey: ['photoDetail', photoId],
      predicate: (query: Query) => query.state.data !== undefined,
    }),
  ]);
}

function enqueueSerializedToggle(
  queryClient: QueryClient,
  toggleFavoriteApi: ToggleFavoriteApi,
  photoId: string,
): Promise<{ id: string; is_favorite: boolean }> {
  const flightMap = getFlightMap(queryClient);
  const entry = getOrCreateFlightEntry(flightMap, photoId);
  const queuedRun = entry.tailPromise.then(
    () => toggleFavoriteApi(photoId),
    () => toggleFavoriteApi(photoId),
  );
  // Keep per-photo serialization chain alive after rejection; caller still awaits queuedRun.
  entry.tailPromise = queuedRun.catch(() => undefined);
  return queuedRun;
}

async function handleFavoriteMutate(
  queryClient: QueryClient,
  photoId: string,
): Promise<FavoriteMutationContext> {
  const flightMap = getFlightMap(queryClient);
  const entry = getOrCreateFlightEntry(flightMap, photoId);
  const seq = ++entry.nextSeq;
  entry.activeSeqs.add(seq);

  const detailState = queryClient.getQueryState(['photoDetail', photoId]);
  if (detailState?.fetchStatus === 'fetching' && detailState.data === undefined) {
    entry.hadPendingDetailFetch = true;
  }
  if (entry.optimisticFavorite !== null) {
    entry.optimisticFavorite = !entry.optimisticFavorite;
  } else {
    const currentFavorite = resolveCurrentFavorite(queryClient, photoId);
    entry.optimisticFavorite = currentFavorite === null ? null : !currentFavorite;
  }

  try {
    await cancelPopulatedQueries(queryClient, photoId);
    captureBaselineSnapshots(queryClient, photoId, entry);
    if (entry.optimisticFavorite !== null) {
      applyFavoriteAcrossCaches(queryClient, photoId, entry.optimisticFavorite);
    }
    return { photoId, seq };
  } catch (err: unknown) {
    entry.activeSeqs.delete(seq);
    if (entry.activeSeqs.size === 0) flightMap.delete(photoId);
    throw err;
  }
}

function handleFavoriteSuccess(
  queryClient: QueryClient,
  response: { id: string; is_favorite: boolean },
  photoId: string,
  context: FavoriteMutationContext | undefined,
): void {
  const flightMap = getFlightMap(queryClient);
  const entry = flightMap.get(photoId);
  if (!entry) {
    applyFavoriteAcrossCaches(queryClient, photoId, response.is_favorite);
    invalidateDependentQueries(queryClient, photoId, false);
    return;
  }
  if (context) entry.activeSeqs.delete(context.seq);
  entry.confirmedFavorite = response.is_favorite;
  if (entry.activeSeqs.size > 0) return;

  applyFavoriteAcrossCaches(queryClient, photoId, response.is_favorite);
  invalidateDependentQueries(queryClient, photoId, entry.hadPendingDetailFetch);
  flightMap.delete(photoId);
}

function handleFavoriteError(
  queryClient: QueryClient,
  photoId: string,
  context: FavoriteMutationContext | undefined,
): void {
  const flightMap = getFlightMap(queryClient);
  const entry = flightMap.get(photoId);
  if (!entry) return;
  if (context) entry.activeSeqs.delete(context.seq);
  if (entry.activeSeqs.size > 0) return;

  if (entry.confirmedFavorite !== null) {
    applyFavoriteAcrossCaches(queryClient, photoId, entry.confirmedFavorite);
    invalidateDependentQueries(queryClient, photoId, entry.hadPendingDetailFetch);
  } else if (entry.hadBaseline) {
    restoreBaselineSnapshots(queryClient, photoId, entry);
    if (entry.hadPendingDetailFetch) {
      void queryClient.invalidateQueries({ queryKey: ['photoDetail', photoId] });
    }
  }
  flightMap.delete(photoId);
}

/**
 * Builds TanStack Query mutation options for favorite toggling with cross-cache
 * synchronization across all `['photos']` lists and `['photoDetail', photoId]`.
 */
export function createFavoriteMutationOptions(
  queryClient: QueryClient,
  toggleFavoriteApi: ToggleFavoriteApi,
) {
  return {
    mutationFn: (photoId: string) =>
      enqueueSerializedToggle(queryClient, toggleFavoriteApi, photoId),
    onMutate: (photoId: string) => handleFavoriteMutate(queryClient, photoId),
    onSuccess: (
      response: { id: string; is_favorite: boolean },
      photoId: string,
      context: FavoriteMutationContext | undefined,
    ) => handleFavoriteSuccess(queryClient, response, photoId, context),
    onError: (
      _error: unknown,
      photoId: string,
      context: FavoriteMutationContext | undefined,
    ) => handleFavoriteError(queryClient, photoId, context),
  };
}
