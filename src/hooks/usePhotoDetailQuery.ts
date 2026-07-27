import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';
import { PhotoDetail } from './usePhotoDetail';

export function usePhotoDetailQuery(photoId: string | null) {
  const { apiPort } = useAppStore();

  return useQuery<PhotoDetail | null>({
    queryKey: ['photoDetail', photoId],
    queryFn: async () => {
      if (!photoId || !apiPort) return null;
      return await api.getPhotoDetail(photoId);
    },
    enabled: Boolean(photoId && apiPort),
    staleTime: 1000 * 60 * 5,
  });
}

export function useUpdatePhotoMetadataMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ photoId, caption, tags }: { photoId: string; caption: string; tags: string[] }) => {
      return await api.updatePhotoMetadata(photoId, caption, tags);
    },
    onSuccess: (updatedPhoto, variables) => {
      queryClient.setQueryData<PhotoDetail>(['photoDetail', variables.photoId], (old) => {
        if (!old) return old;
        return {
          ...old,
          ai_analysis: updatedPhoto.ai_analysis,
        };
      });
      queryClient.invalidateQueries({ queryKey: ['photos'] });
    },
  });
}
