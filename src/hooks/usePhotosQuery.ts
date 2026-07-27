import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAppStore, SearchFilters } from '../store/useAppStore';
import { api } from '../services/api';

export function usePhotosQuery(
  selectedFolder: string | null,
  searchQuery: string,
  searchFilters: SearchFilters
) {
  const { apiPort } = useAppStore();

  return useQuery({
    queryKey: ['photos', selectedFolder, searchQuery, searchFilters],
    queryFn: async () => {
      if (!apiPort) return [];
      const hasFilters = searchFilters && Object.keys(searchFilters).length > 0;
      const hasQuery = searchQuery && searchQuery.trim() !== '';
      if (hasQuery || hasFilters) {
        return api.searchPhotos(searchQuery, searchFilters, 100, 0);
      } else {
        return api.fetchPhotos(100, 0, selectedFolder);
      }
    },
    enabled: Boolean(apiPort),
    staleTime: 1000 * 60 * 5, // 5 minutes cache validity
  });
}

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

      const previousData = queryClient.getQueryData(queryKey);

      queryClient.setQueryData(queryKey, (oldData: any) => {
        if (!oldData) return oldData;
        if (oldData.pages) {
          return {
            ...oldData,
            pages: oldData.pages.map((page: any[]) =>
              page.map((p: any) =>
                p.id === photoId ? { ...p, is_favorite: !p.is_favorite } : p
              )
            ),
          };
        }
        if (Array.isArray(oldData)) {
          return oldData.map((p: any) =>
            p.id === photoId ? { ...p, is_favorite: !p.is_favorite } : p
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
