import { InfiniteData, useMutation, useQueryClient } from '@tanstack/react-query';
import { SearchFilters } from '../store/useAppStore';
import { api } from '../services/api';
import { PhotoSummary } from '../types/photo';

type PhotosCacheData = InfiniteData<PhotoSummary[]> | PhotoSummary[];

export function useToggleFavoriteMutation(
  selectedFolder: string | null,
  searchQuery: string,
  searchFilters: SearchFilters
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (photoId: string) => {
      return await api.toggleFavorite(photoId);
    },
    onMutate: async (photoId: string) => {
      const queryKey = ['photos', selectedFolder, searchQuery, searchFilters];
      await queryClient.cancelQueries({ queryKey });

      const previousData = queryClient.getQueryData<PhotosCacheData>(queryKey);

      queryClient.setQueryData<PhotosCacheData>(queryKey, (oldData) => {
        if (!oldData) return oldData;
        if ('pages' in oldData) {
          return {
            ...oldData,
            pages: oldData.pages.map((page) =>
              page.map((photo) =>
                photo.id === photoId ? { ...photo, is_favorite: !photo.is_favorite } : photo
              )
            ),
          };
        }
        if (Array.isArray(oldData)) {
          return oldData.map((photo) =>
            photo.id === photoId ? { ...photo, is_favorite: !photo.is_favorite } : photo
          );
        }
        return oldData;
      });

      return { previousData, queryKey };
    },
    onError: (_err, _photoId, context) => {
      if (context?.previousData && context?.queryKey) {
        queryClient.setQueryData(context.queryKey, context.previousData);
      }
    },
  });
}
