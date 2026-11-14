import { QueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store/useAppStore';
import { CritiqueItem } from '../types/critique';

export interface ActivePhotoEntry {
  id: string;
}

function hasPhotoId(candidate: unknown): candidate is { id: string } {
  return (
    typeof candidate === 'object' &&
    candidate !== null &&
    'id' in candidate &&
    typeof (candidate as { id: unknown }).id === 'string'
  );
}

function extractPhotosFromQueryData(queryData: unknown): ActivePhotoEntry[] {
  if (typeof queryData === 'object' && queryData !== null && 'pages' in queryData) {
    const pages = (queryData as { pages: unknown }).pages;
    if (Array.isArray(pages)) {
      return pages
        .flatMap((page) => (Array.isArray(page) ? page : []))
        .filter(hasPhotoId)
        .map((photo) => ({ id: photo.id }));
    }
  }

  if (Array.isArray(queryData)) {
    return queryData.filter(hasPhotoId).map((photo) => ({ id: photo.id }));
  }

  return [];
}

function getLatestCritiqueList(queryClient: QueryClient): ActivePhotoEntry[] {
  const critiqueQueries = queryClient.getQueriesData<CritiqueItem[]>({ queryKey: ['critiques'] });
  let latestEntries: ActivePhotoEntry[] = [];
  let latestUpdatedAt = -1;

  for (const [queryKey, critiqueItems] of critiqueQueries) {
    if (!Array.isArray(critiqueItems) || critiqueItems.length === 0) continue;
    const updatedAt = queryClient.getQueryState(queryKey)?.dataUpdatedAt ?? 0;
    if (updatedAt > latestUpdatedAt) {
      latestUpdatedAt = updatedAt;
      latestEntries = critiqueItems.map((item) => ({ id: item.photo_id }));
    }
  }

  return latestEntries;
}

/**
 * Resolves the active ordered photo ID list from React Query cache
 * matching the current workspace tab (critique archive vs. photo gallery).
 */
export function getActivePhotoList(queryClient: QueryClient): ActivePhotoEntry[] {
  if (useAppStore.getState().activeTab === 'critique') {
    const critiqueEntries = getLatestCritiqueList(queryClient);
    if (critiqueEntries.length > 0) {
      return critiqueEntries;
    }
  }

  const photoQueries = queryClient.getQueriesData<unknown>({ queryKey: ['photos'] });
  let latestEntries: ActivePhotoEntry[] = [];
  let latestUpdatedAt = -1;

  for (const [queryKey, queryData] of photoQueries) {
    const entries = extractPhotosFromQueryData(queryData);
    if (entries.length === 0) continue;
    const updatedAt = queryClient.getQueryState(queryKey)?.dataUpdatedAt ?? 0;
    if (updatedAt > latestUpdatedAt) {
      latestUpdatedAt = updatedAt;
      latestEntries = entries;
    }
  }

  return latestEntries;
}
