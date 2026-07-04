import { useRef, useEffect, useState } from 'react';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { CheckCircle2, Heart } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';

interface PhotoGalleryProps {
  selectedFolder: string | null;
}

export function PhotoGallery({ selectedFolder }: PhotoGalleryProps) {
  const { apiPort, searchQuery, searchFilters, selectedPhotoIds, togglePhotoSelection, setSelectedPhotoId } = useAppStore();
  const queryClient = useQueryClient();
  const parentRef = useRef<HTMLDivElement>(null);
  
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState(searchQuery);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 500);

    return () => {
      clearTimeout(handler);
    };
  }, [searchQuery]);

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
    estimateSize: () => 250, // estimated row height
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

  if (status === 'pending') {
    return (
      <div style={{ padding: '20px', color: '#fff', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        {debouncedSearchQuery ? (
          <>
            <h3 style={{ marginBottom: '8px' }}>Searching...</h3>
            <p style={{ color: '#aaa' }}>Finding photos related to "{debouncedSearchQuery}"</p>
          </>
        ) : (
          <h3>Loading photos...</h3>
        )}
      </div>
    );
  }
  if (status === 'error') return <div style={{ padding: '20px', color: 'red' }}>Error loading photos</div>;
  
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
              {isLoaderRow
                ? hasNextPage ? <div style={{ width: '100%', textAlign: 'center', color: '#aaa' }}>Loading more...</div> : null
                : rowPhotos.map((photo) => {
                    const isSelected = selectedPhotoIds.has(photo.id);
                    return (
                      <div 
                        key={photo.id}
                        onClick={() => setSelectedPhotoId(photo.id)}
                        style={{
                          flex: 1,
                          maxWidth: `calc(25% - 12px)`, // (100% / 4) - gap
                          backgroundColor: '#222',
                          borderRadius: '8px',
                          overflow: 'hidden',
                          cursor: 'pointer',
                          position: 'relative',
                          transition: 'transform 0.2s',
                          border: isSelected ? '2px solid #4CAF50' : '2px solid transparent',
                          boxSizing: 'border-box'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
                        onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                      >
                        <div 
                          onClick={(e) => {
                            e.stopPropagation();
                            togglePhotoSelection(photo.id);
                          }}
                          style={{
                            position: 'absolute',
                            top: '8px',
                            left: '8px',
                            zIndex: 2,
                            color: isSelected ? '#4CAF50' : '#fff',
                            opacity: isSelected ? 1 : 0.6,
                            cursor: 'pointer',
                            background: isSelected ? '#fff' : 'rgba(0,0,0,0.5)',
                            borderRadius: '50%',
                            display: 'flex',
                            padding: '2px',
                            transition: 'opacity 0.2s'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                          onMouseLeave={(e) => e.currentTarget.style.opacity = isSelected ? '1' : '0.6'}
                        >
                          <CheckCircle2 size={20} fill={isSelected ? '#4CAF50' : 'none'} color={isSelected ? '#fff' : '#fff'} />
                        </div>
                        <div 
                          onClick={async (e) => {
                            e.stopPropagation();
                            try {
                              const res = await api.toggleFavorite(photo.id);
                              // Optimistic UI update using setQueryData to avoid massive network refetches
                              queryClient.setQueryData(
                                ['photos', selectedFolder, debouncedSearchQuery, searchFilters],
                                (oldData: any) => {
                                  if (!oldData) return oldData;
                                  return {
                                    ...oldData,
                                    pages: oldData.pages.map((page: any[]) =>
                                      page.map(p =>
                                        p.id === photo.id ? { ...p, is_favorite: res.is_favorite } : p
                                      )
                                    )
                                  };
                                }
                              );
                            } catch(err) {
                              console.error(err);
                            }
                          }}
                          style={{
                            position: 'absolute',
                            top: '8px',
                            right: '8px',
                            zIndex: 2,
                            color: photo.is_favorite ? '#ef4444' : '#fff',
                            opacity: photo.is_favorite ? 1 : 0.6,
                            cursor: 'pointer',
                            display: 'flex',
                            padding: '4px',
                            transition: 'all 0.2s',
                            filter: 'drop-shadow(0px 2px 4px rgba(0,0,0,0.5))'
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.transform = 'scale(1.1)'; }}
                          onMouseLeave={(e) => { e.currentTarget.style.opacity = photo.is_favorite ? '1' : '0.6'; e.currentTarget.style.transform = 'scale(1)'; }}
                        >
                          <Heart size={20} fill={photo.is_favorite ? '#ef4444' : 'rgba(0,0,0,0.3)'} color={photo.is_favorite ? '#ef4444' : '#fff'} />
                        </div>
                        <img 
                        src={api.getPhotoThumbnailUrl(photo.id)}
                        alt={photo.file_name}
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: 'cover',
                          display: 'block',
                          backgroundColor: '#2a2a2a'
                        }}
                        loading="lazy"
                        onError={(e) => {
                          // Replace broken image with a fallback SVG "File Missing" placeholder
                          e.currentTarget.src = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><rect width="100%" height="100%" fill="%232a2a2a"/><text x="50%" y="50%" font-family="sans-serif" font-size="8" fill="%23666" text-anchor="middle" dy=".3em">File Missing</text></svg>';
                        }}
                      />
                      <div style={{
                        position: 'absolute',
                        bottom: 0,
                        left: 0,
                        right: 0,
                        padding: '24px 12px 12px',
                        background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0) 100%)',
                        color: '#fff',
                        fontSize: '12px',
                        opacity: 0,
                        transition: 'opacity 0.2s'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                      onMouseLeave={(e) => e.currentTarget.style.opacity = '0'}
                      >
                        <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {photo.file_name}
                        </div>
                        {photo.capture_date && (
                          <div style={{ color: '#aaa', marginTop: '2px' }}>
                            {new Date(photo.capture_date).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              }
              {/* Fill empty spaces in the row */}
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
