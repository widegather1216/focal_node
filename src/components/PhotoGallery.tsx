import { useRef, useEffect, useState, useCallback } from 'react';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';
import { useDebounce } from '../hooks/useDebounce';
import { PhotoCard } from './gallery/PhotoCard';
import { LoadingSpinner } from './common/LoadingSpinner';

interface PhotoGalleryProps {
  selectedFolder: string | null;
}

export function PhotoGallery({ selectedFolder }: PhotoGalleryProps) {
  const { apiPort, searchQuery, searchFilters, selectedPhotoIds, togglePhotoSelection, setSelectedPhotoId } = useAppStore();
  const queryClient = useQueryClient();
  const parentRef = useRef<HTMLDivElement>(null);
  const [columnCount, setColumnCount] = useState(4);
  
  const debouncedSearchQuery = useDebounce(searchQuery, 500);

  // Measure container width and compute responsive column count
  useEffect(() => {
    const el = parentRef.current;
    if (!el) return;

    const updateColumns = () => {
      const width = el.clientWidth;
      if (width > 0) {
        // Compute columns such that each photo card is roughly 220px ~ 280px wide
        const cols = Math.max(2, Math.min(8, Math.floor(width / 240)));
        setColumnCount(cols);
      }
    };

    updateColumns();
    const observer = new ResizeObserver(updateColumns);
    observer.observe(el);

    return () => observer.disconnect();
  }, []);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status
  } = useInfiniteQuery({
    queryKey: ['photos', selectedFolder, debouncedSearchQuery, searchFilters],
    queryFn: async ({ pageParam = 0 }) => {
      if (!apiPort) return [];
      const hasFilters = searchFilters && Object.keys(searchFilters).length > 0;
      const hasQuery = debouncedSearchQuery && debouncedSearchQuery.trim() !== '';
      if (hasQuery || hasFilters) {
        return api.searchPhotos(debouncedSearchQuery, searchFilters, 50, (pageParam as number) * 50);
      } else {
        return api.fetchPhotos(50, (pageParam as number) * 50, selectedFolder);
      }
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
    getScrollElement: () => parentRef.current,
    estimateSize: () => 240,
    overscan: 3,
  });

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
      const res = await api.toggleFavorite(photoId);
      queryClient.setQueryData(
        ['photos', selectedFolder, debouncedSearchQuery, searchFilters],
        (oldData: any) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            pages: oldData.pages.map((page: any[]) =>
              page.map(p =>
                p.id === photoId ? { ...p, is_favorite: res.is_favorite } : p
              )
            )
          };
        }
      );
    } catch (err) {
      console.error("Failed to toggle favorite:", err);
    }
  }, [queryClient, selectedFolder, debouncedSearchQuery, searchFilters]);

  if (status === 'pending') {
    return (
      <div style={{ padding: '20px', color: '#fff', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        {debouncedSearchQuery ? (
          <LoadingSpinner message={`"${debouncedSearchQuery}" 관련 사진 검색 중...`} />
        ) : (
          <LoadingSpinner message="사진 불러오는 중..." />
        )}
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div style={{ padding: '20px', color: '#ef4444', display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        사진 목록을 불러오는 도중 오류가 발생했습니다.
      </div>
    );
  }
  
  if (allPhotos.length === 0 && !hasNextPage) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa', flexDirection: 'column', height: '100%' }}>
        <h2 style={{ fontSize: '22px', marginBottom: '8px', color: '#fff', fontWeight: 600 }}>표시할 사진이 없습니다</h2>
        <p style={{ fontSize: '14px', color: '#71717a' }}>사이드바에서 사진 폴더를 추가하거나 검색 필터를 재설정해보세요.</p>
      </div>
    );
  }

  return (
    <div 
      ref={parentRef}
      style={{
        flex: 1,
        overflow: 'auto',
        backgroundColor: '#111',
        padding: '20px',
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
                gap: '16px',
                paddingBottom: '16px',
                boxSizing: 'border-box'
              }}
            >
              {isLoaderRow ? (
                hasNextPage ? (
                  <div style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#a1a1aa', fontSize: '13px' }}>
                    사진 추가 로딩 중...
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
