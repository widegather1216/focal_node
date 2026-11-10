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
    setIndexingError,
    reportIndexingError,
    markIndexingTerminal,
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
    let idleClearTimerId: ReturnType<typeof setTimeout> | null = null;

    const clearIdleTimer = () => {
      if (idleClearTimerId) {
        clearTimeout(idleClearTimerId);
        idleClearTimerId = null;
      }
    };

    const scheduleNext = (delay: number) => {
      if (!isMounted) return;
      if (timerId) clearTimeout(timerId);
      timerId = setTimeout(checkStatus, delay);
    };

    const checkStatus = async () => {
      try {
        const data = await api.getIndexingStatus();
        if (!isMounted || !data) return;

        const currentStatus = data.status; // 'idle' | 'processing' | 'paused' | 'cancelled' | 'error'
        const runId: number | null = typeof data.run_id === 'number' ? data.run_id : null;
        const storeState = useAppStore.getState();

        if (currentStatus === 'processing') {
          if (runId !== null && runId > 0 && runId <= storeState.lastTerminalRunId) {
            scheduleNext(storeState.isIndexing ? 1500 : 10000);
            return;
          }
          clearIdleTimer();
          setIndexingError(null);
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
          if (runId !== null && runId > 0 && runId <= storeState.lastTerminalRunId) {
            scheduleNext(storeState.isIndexing ? 2000 : 10000);
            return;
          }
          clearIdleTimer();
          setIndexingState('paused');
          scheduleNext(2000);
        } else if (currentStatus === 'error') {
          clearIdleTimer();
          const isNewErrorRun =
            runId === null ||
            (runId > storeState.lastTerminalRunId && runId !== storeState.dismissedErrorRunId);
          if (isNewErrorRun && (data.total_files > 0 || data.processed_files > 0)) {
            setIndexingProgress({
              processed: data.processed_files || 0,
              total: data.total_files || 0,
              filePath: data.current_file || 'Indexing failed',
            });
          }
          reportIndexingError(
            data.error_message || '데이터베이스 저장 중 오류가 발생했습니다.',
            runId
          );
          if (wasIndexingRef.current) {
            queryClient.invalidateQueries({ queryKey: ['photos'] });
            queryClient.invalidateQueries({ queryKey: ['analyticsStats'] });
          }
          scheduleNext(10000);
        } else {
          // Status is 'idle' or 'cancelled'
          if (runId !== null && runId > 0) {
            markIndexingTerminal(runId);
          }
          if (wasIndexingRef.current) {
            setIndexingState('idle');
            clearIdleTimer();
            idleClearTimerId = setTimeout(() => {
              if (isMounted && useAppStore.getState().indexingState === 'idle') {
                setIsIndexing(false);
                setIndexingProgress(null);
              }
            }, 800);
            queryClient.invalidateQueries({ queryKey: ['photos'] });
            queryClient.invalidateQueries({ queryKey: ['analyticsStats'] });
          }
          scheduleNext(10000);
        }
      } catch (err) {
        console.warn('Failed to poll indexing status:', err);
        scheduleNext(10000);
      }
    };

    // Trigger initial check
    checkStatus();

    return () => {
      isMounted = false;
      clearIdleTimer();
      if (timerId) clearTimeout(timerId);
    };
  }, [
    apiPort,
    setIsIndexing,
    setIndexingState,
    setIndexingProgress,
    setIndexingError,
    reportIndexingError,
    markIndexingTerminal,
    queryClient,
  ]);
}
