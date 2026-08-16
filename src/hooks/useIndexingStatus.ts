import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';

export function useIndexingStatus() {
  const {
    apiPort,
    isIndexing,
    setIsIndexing,
    setIndexingState,
    setIndexingProgress,
  } = useAppStore();
  const queryClient = useQueryClient();
  const wasIndexingRef = useRef(isIndexing);

  useEffect(() => {
    wasIndexingRef.current = isIndexing;
  }, [isIndexing]);

  useEffect(() => {
    if (!apiPort) return;

    let isMounted = true;
    let timerId: ReturnType<typeof setTimeout> | null = null;

    const checkStatus = async () => {
      try {
        const data = await api.getIndexingStatus();
        if (!isMounted || !data) return;

        const currentStatus = data.status; // 'idle' | 'processing' | 'paused' | 'cancelled' | 'error'

        if (currentStatus === 'processing') {
          setIsIndexing(true);
          setIndexingState('processing');
          if (data.total_files > 0 || data.processed_files > 0) {
            setIndexingProgress({
              processed: data.processed_files || 0,
              total: data.total_files || 0,
              filePath: data.current_file || 'Indexing photos...',
            });
          }
          scheduleNext(1500);
        } else if (currentStatus === 'paused') {
          setIndexingState('paused');
          scheduleNext(2000);
        } else {
          // Status is 'idle', 'cancelled', or 'error'
          if (wasIndexingRef.current) {
            setIndexingState('idle');
            setTimeout(() => {
              if (isMounted) {
                setIsIndexing(false);
                setIndexingProgress(null);
              }
            }, 800);
            queryClient.invalidateQueries({ queryKey: ['photos'] });
            queryClient.invalidateQueries({ queryKey: ['analyticsStats'] });
          }
          // Slow poll when idle
          scheduleNext(10000);
        }
      } catch (err) {
        scheduleNext(10000);
      }
    };

    const scheduleNext = (delay: number) => {
      if (!isMounted) return;
      if (timerId) clearTimeout(timerId);
      timerId = setTimeout(checkStatus, delay);
    };

    // Trigger initial check
    checkStatus();

    return () => {
      isMounted = false;
      if (timerId) clearTimeout(timerId);
    };
  }, [apiPort, setIsIndexing, setIndexingState, setIndexingProgress, queryClient]);
}
