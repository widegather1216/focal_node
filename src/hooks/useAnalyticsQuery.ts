import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';

export function useAnalyticsQuery() {
  const { apiPort } = useAppStore();

  return useQuery({
    queryKey: ['analyticsStats'],
    queryFn: async () => {
      if (!apiPort) return null;
      return await api.getAnalyticsStats();
    },
    enabled: Boolean(apiPort),
    staleTime: 1000 * 60 * 5, // 5 minutes cache
  });
}
