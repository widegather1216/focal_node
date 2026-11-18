import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { createFavoriteMutationOptions } from '../utils/photoFavorite';

export function useToggleFavoriteMutation() {
  const queryClient = useQueryClient();

  return useMutation(
    createFavoriteMutationOptions(queryClient, (photoId) => api.toggleFavorite(photoId)),
  );
}
