import { useRef, useEffect } from 'react';
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
  
  const debouncedSearchQuery = useDebounce(searchQuery, 500);

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

  const COLUMN_COUNT = 4;
  const rowCount = Math.ceil(allPhotos.length / COLUMN_COUNT);

  const virtualizer = useVirtualizer({
    count: hasNextPage ? rowCount + 1 : rowCount,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 250,
    overscan: 2,
  });

  useEffect(() => {
    const [lastItem] = [...virtualizer.getVirtualItems()].reverse();
    if (!lastItem) return;

    if (
      lastItem.index >= rowCount - 1 &&
      hasNextPage &&
      !isFetchingNextPage
    ) {
      fetchNextPage();
    }
  }, [hasNextPage, fetchNextPage, allPhotos.length, isFetchingNextPage, virtualizer.getVirtualItems(), rowCount]);

  const handleToggleFavorite = async (photoId: string, e: React.MouseEvent) => {
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
    } catch(err) {
      console.error(err);
    }
  };

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

  if (status === 'error') return <div style={{ padding: '20px', color: '#ef4444' }}>Error loading photos</div>;
  
  if (allPhotos.length === 0 && !hasNextPage) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa', flexDirection: 'column' }}>
        <h2 style={{ fontSize: '24px', marginBottom: '8px', color: '#fff' }}>No photos found</h2>
        <p>Add a folder from the sidebar to get started.</p>
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
        height: '100vh',
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
        {virtualizer.getVirtualItems().map(virtualRow => {
          const isLoaderRow = virtualRow.index > rowCount - 1;
          const fromIndex = virtualRow.index * COLUMN_COUNT;
          const toIndex = Math.min(fromIndex + COLUMN_COUNT, allPhotos.length);
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
                hasNextPage ? <div style={{ width: '100%', textAlign: 'center', color: '#aaa' }}>Loading more...</div> : null
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
              {rowPhotos.length < COLUMN_COUNT && Array.from({ length: COLUMN_COUNT - rowPhotos.length }).map((_, i) => (
                <div key={`empty-${i}`} style={{ flex: 1, maxWidth: `calc(25% - 12px)` }} />
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
