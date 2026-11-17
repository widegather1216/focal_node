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
    setCurrentIndexingRunId,
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

    const syncProgressIfPresent = (
      totalFiles: number,
      processedFiles: number,
      currentFile: string,
      fallbackLabel: string,
    ) => {
      if (totalFiles > 0 || processedFiles > 0) {
        setIndexingProgress({
          processed: processedFiles || 0,
          total: totalFiles || 0,
          filePath: currentFile || fallbackLabel,
        });
      }
    };

    const checkStatus = async () => {
      try {
        const seqBeforeFetch = useAppStore.getState().terminalEventSeq;
        const data = await api.getIndexingStatus();
        if (!isMounted || !data) return;

        const storeState = useAppStore.getState();
        if (storeState.terminalEventSeq !== seqBeforeFetch) {
          scheduleNext(storeState.isIndexing ? 1000 : 10000);
          return;
        }

        const currentStatus = data.status; // 'idle' | 'processing' | 'paused' | 'cancelling' | 'cancelled' | 'error'
        const runId: number | null = typeof data.run_id === 'number' ? data.run_id : null;
        const inFlight = Boolean(data.active_run_in_flight);
        const isSameRunOptimisticCancel =
          storeState.indexingState === 'cancelling' &&
          runId !== null &&
          runId > 0 &&
          runId === storeState.currentIndexingRunId &&
          (currentStatus === 'processing' || currentStatus === 'paused');
        const isCancelling =
          currentStatus === 'cancelling' ||
          isSameRunOptimisticCancel ||
          (inFlight && currentStatus !== 'processing' && currentStatus !== 'paused');

        if (currentStatus === 'processing' || currentStatus === 'paused' || isCancelling) {
          if (!inFlight && runId !== null && runId > 0 && runId <= storeState.lastTerminalRunId) {
            scheduleNext(storeState.isIndexing ? 1500 : 10000);
            return;
          }
          clearIdleTimer();
          setIndexingError(null);
          if (runId !== null && runId > 0) {
            setCurrentIndexingRunId(runId);
          }

          if (isCancelling) {
            setIndexingState('cancelling');
            syncProgressIfPresent(data.total_files, data.processed_files, data.current_file, 'Cancelling indexing...');
            scheduleNext(500);
            return;
          }

          if (currentStatus === 'paused') {
            setIndexingState('paused');
            scheduleNext(2000);
            return;
          }

          setIsIndexing(true);
          setIndexingState('processing');
          syncProgressIfPresent(data.total_files, data.processed_files, data.current_file, 'Indexing photos...');
          scheduleNext(1500);
          return;
        }

        if (currentStatus === 'error') {
          clearIdleTimer();
          setCurrentIndexingRunId(null);
          const isNewErrorRun =
            runId === null ||
            (runId > storeState.lastTerminalRunId && runId !== storeState.dismissedErrorRunId);
          if (isNewErrorRun) {
            syncProgressIfPresent(data.total_files, data.processed_files, data.current_file, 'Indexing failed');
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
          return;
        }

        // Terminal state: 'idle' or 'cancelled' with active_run_in_flight === false
        if (runId !== null && runId > 0) {
          markIndexingTerminal(runId);
        }
        setCurrentIndexingRunId(null);
        if (wasIndexingRef.current) {
          clearIdleTimer();
          if (currentStatus === 'cancelled') {
            setIndexingState('cancelled');
            setIndexingProgress(null);
          } else {
            setIndexingState('idle');
            idleClearTimerId = setTimeout(() => {
              if (isMounted && useAppStore.getState().indexingState === 'idle') {
                setIsIndexing(false);
                setIndexingProgress(null);
              }
            }, 800);
          }
          queryClient.invalidateQueries({ queryKey: ['photos'] });
          queryClient.invalidateQueries({ queryKey: ['analyticsStats'] });
        }
        scheduleNext(10000);
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
    setCurrentIndexingRunId,
    reportIndexingError,
    markIndexingTerminal,
    queryClient,
  ]);
}
