import type { SearchFilters } from '../types/photo';

function isActiveFilterValue(filterValue: unknown): boolean {
  if (filterValue === undefined || filterValue === null) {
    return false;
  }
  if (typeof filterValue === 'string') {
    return filterValue.trim() !== '';
  }
  if (typeof filterValue === 'number') {
    return Number.isFinite(filterValue);
  }
  return typeof filterValue === 'boolean';
}

export function sanitizeSearchFilters(
  filters: SearchFilters | null | undefined,
): SearchFilters {
  if (!filters || typeof filters !== 'object') {
    return {};
  }
  const activeEntries = Object.entries(filters).filter(([, filterValue]) =>
    isActiveFilterValue(filterValue),
  );
  return Object.fromEntries(activeEntries) as SearchFilters;
}

export function toggleFavoriteFilter(
  filters: SearchFilters | null | undefined,
): SearchFilters {
  const normalized = sanitizeSearchFilters(filters);
  if (Boolean(normalized.is_favorite)) {
    const { is_favorite: _removedFavorite, ...remainingFilters } = normalized;
    return remainingFilters;
  }
  return { ...normalized, is_favorite: true };
}

export function countActiveSearchFilters(
  filters: SearchFilters | null | undefined,
): number {
  return Object.keys(sanitizeSearchFilters(filters)).length;
}

export function hasActiveSearchFilters(
  filters: SearchFilters | null | undefined,
): boolean {
  return countActiveSearchFilters(filters) > 0;
}
