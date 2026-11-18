import { useRef, useEffect, useLayoutEffect, useState, useCallback } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';
import { useDebounce } from '../hooks/useDebounce';
import { useToggleFavoriteMutation } from '../hooks/usePhotosQuery';
import { hasActiveSearchFilters } from '../utils/searchFilters';
import {
  DEFAULT_GALLERY_COLUMNS,
  type VirtualizerScrollState,
  bindGalleryContainerResize,
  buildGalleryQueryContextKey,
  observeGalleryElementOffset,
  resetVirtualizerScrollPosition,
  syncVirtualizerOnContainerMount,
} from '../utils/galleryLayout';
import { PhotoCard } from './gallery/PhotoCard';
import { LoadingSpinner } from './common/LoadingSpinner';
import { Loader2, SearchX } from 'lucide-react';

interface PhotoGalleryProps {
  selectedFolder: string | null;
}

export function PhotoGallery({ selectedFolder }: PhotoGalleryProps) {
  const { apiPort, searchQuery, searchFilters, selectedPhotoIds, togglePhotoSelection, setSelectedPhotoId } = useAppStore();
  const { mutateAsync: toggleFavoriteAsync } = useToggleFavoriteMutation();
  const scrollElementRef = useRef<HTMLDivElement | null>(null);
  const virtualizerRef = useRef<VirtualizerScrollState | null>(null);
  const [scrollContainer, setScrollContainer] = useState<HTMLDivElement | null>(null);
  const [columnCount, setColumnCount] = useState(DEFAULT_GALLERY_COLUMNS);
  
  const debouncedSearchQuery = useDebounce(searchQuery, 500);
  const trimmedSearchQuery = searchQuery.trim();
  const effectiveSearchQuery = trimmedSearchQuery.startsWith('similar:')
    ? trimmedSearchQuery
    : debouncedSearchQuery;
  const queryContextKey = buildGalleryQueryContextKey(
    selectedFolder,
    effectiveSearchQuery,
    searchFilters,
  );
  const prevQueryContextKeyRef = useRef<string>(queryContextKey);

  const handleScrollContainerRef = useCallback((containerElement: HTMLDivElement | null) => {
    scrollElementRef.current = containerElement;
    syncVirtualizerOnContainerMount(virtualizerRef.current, containerElement);
    setScrollContainer(containerElement);
  }, []);

  // Re-bind ResizeObserver whenever the scroll container mounts or remounts after pending/empty states.
  useEffect(
    () => bindGalleryContainerResize(scrollContainer, setColumnCount),
    [scrollContainer],
  );

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status
  } = useInfiniteQuery({
    queryKey: ['photos', selectedFolder, effectiveSearchQuery, searchFilters],
    queryFn: async ({ pageParam = 0, signal }) => {
      if (!apiPort) return [];
      const hasFilters = hasActiveSearchFilters(searchFilters);
      const hasQuery = Boolean(effectiveSearchQuery && effectiveSearchQuery.trim() !== '');
      if (hasQuery || hasFilters) {
        return api.searchPhotos(
          effectiveSearchQuery,
          searchFilters,
          50,
          (pageParam as number) * 50,
          selectedFolder,
          signal,
        );
      }
      return api.fetchPhotos(50, (pageParam as number) * 50, selectedFolder, signal);
    },
    getNextPageParam: (lastPage, allPages) => {
      if (lastPage.length < 50) return undefined;
      return allPages.length;
    },
    initialPageParam: 0,
    enabled: !!apiPort,
  });

  const allPhotos = data ? data.pages.flatMap(page => page) : [];
  const rowCount = Math.ceil(allPhotos.length / columnCount);

  const virtualizer = useVirtualizer({
    count: hasNextPage ? rowCount + 1 : rowCount,
    getScrollElement: () => scrollElementRef.current,
    estimateSize: () => 220,
    overscan: 3,
    observeElementOffset: observeGalleryElementOffset,
  });
  virtualizerRef.current = virtualizer;

  // Reset residual scrollOffset before getVirtualItems() so the initial commit after a query switch renders row 0.
  if (prevQueryContextKeyRef.current !== queryContextKey) {
    resetVirtualizerScrollPosition(virtualizer, null);
  }

  useLayoutEffect(() => {
    if (prevQueryContextKeyRef.current === queryContextKey) {
      return;
    }
    prevQueryContextKeyRef.current = queryContextKey;
    resetVirtualizerScrollPosition(virtualizerRef.current, scrollElementRef.current);
  }, [queryContextKey]);

  const virtualItems = virtualizer.getVirtualItems();

  useEffect(() => {
    if (!virtualItems.length) return;
    const lastItem = virtualItems[virtualItems.length - 1];

    if (
      lastItem &&
      lastItem.index >= rowCount - 1 &&
      hasNextPage &&
      !isFetchingNextPage
    ) {
      fetchNextPage();
    }
  }, [virtualItems, rowCount, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const handleToggleFavorite = useCallback(async (photoId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await toggleFavoriteAsync(photoId);
    } catch (err: unknown) {
      console.error("Failed to toggle favorite:", err);
    }
  }, [toggleFavoriteAsync]);

  if (status === 'pending') {
    return (
      <div style={{
        padding: '20px',
        color: 'var(--text-primary)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        backgroundColor: 'var(--bg-canvas)'
      }}>
        {effectiveSearchQuery ? (
          <LoadingSpinner
            message={
              effectiveSearchQuery.startsWith('similar:')
                ? "유사한 무드 사진을 찾는 중..."
                : `"${effectiveSearchQuery}" 시각 임베딩 분석 및 검색 중...`
            }
          />
        ) : (
          <LoadingSpinner message="사진 라이브러리를 불러오는 중..." />
        )}
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div style={{
        padding: '20px',
        color: 'var(--accent-focal)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100%',
        backgroundColor: 'var(--bg-canvas)'
      }}>
        사진 목록을 불러오는 도중 오류가 발생했습니다.
      </div>
    );
  }
  
  if (allPhotos.length === 0 && !hasNextPage) {
    return (
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: 'var(--bg-canvas)',
        userSelect: 'none'
      }}>
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '16px'
        }}>
          <SearchX size={24} color="var(--text-muted)" />
        </div>
        <h2 style={{ fontSize: '16px', marginBottom: '6px', color: 'var(--text-primary)', fontWeight: 600 }}>
          일치하는 사진이 없습니다
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>
          자연어 검색어 또는 EXIF 필터 조건을 변경하거나, 새 사진 폴더를 추가해 보세요.
        </p>
      </div>
    );
  }

  return (
    <div 
      ref={handleScrollContainerRef}
      style={{
        flex: 1,
        overflow: 'auto',
        backgroundColor: 'var(--bg-canvas)',
        padding: '10px',
        height: '100%',
        boxSizing: 'border-box'
      }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualItems.map(virtualRow => {
          const isLoaderRow = virtualRow.index > rowCount - 1;
          const fromIndex = virtualRow.index * columnCount;
          const toIndex = Math.min(fromIndex + columnCount, allPhotos.length);
          const rowPhotos = allPhotos.slice(fromIndex, toIndex);

          return (
            <div
              key={virtualRow.key}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
                display: 'flex',
                gap: '8px',
                paddingBottom: '8px',
                boxSizing: 'border-box'
              }}
            >
              {isLoaderRow ? (
                hasNextPage ? (
                  <div style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '12px' }}>
                    <Loader2 size={14} className="spin" color="var(--accent-focal)" />
                    <span>추가 사진 불러오는 중...</span>
                  </div>
                ) : null
              ) : (
                rowPhotos.map((photo) => (
                  <PhotoCard
                    key={photo.id}
                    photo={photo}
                    isSelected={selectedPhotoIds.has(photo.id)}
                    onSelectPhoto={setSelectedPhotoId}
                    onToggleSelection={togglePhotoSelection}
                    onToggleFavorite={handleToggleFavorite}
                  />
                ))
              )}
              {rowPhotos.length < columnCount && Array.from({ length: columnCount - rowPhotos.length }).map((_, i) => (
                <div key={`empty-${i}`} style={{ flex: 1, minWidth: 0 }} />
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
