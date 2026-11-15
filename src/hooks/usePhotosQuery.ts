import { useMutation, useQueryClient } from '@tanstack/react-query';
import { SearchFilters } from '../store/useAppStore';
import { api } from '../services/api';

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
