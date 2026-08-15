import { useEffect, useRef } from 'react';
import { listen, UnlistenFn } from '@tauri-apps/api/event';
import { useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store/useAppStore';

export function useTauriEvents() {
  const {
    setIsIndexing,
    setIndexingState,
    setIndexingProgress,
    setIsDownloadingModel,
    setDownloadProgress,
    setDownloadModelName
  } = useAppStore();
  const queryClient = useQueryClient();
  const invalidateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let isSubscribed = true;
    const unlisteners: UnlistenFn[] = [];

    const registerListener = async <T>(
      eventName: string,
      handler: (event: { payload: T }) => void
    ) => {
      try {
        const unlisten = await listen<T>(eventName, handler);
        if (isSubscribed) {
          unlisteners.push(unlisten);
        } else {
          unlisten();
        }
      } catch (err) {
        console.error(`Failed to register Tauri event listener [${eventName}]:`, err);
      }
    };

    // 1. Indexing Progress
    registerListener<{ processed: number; total: number; file_path: string }>(
      "indexing-progress",
      (event) => {
        setIndexingState('processing');
        setIndexingProgress({
          processed: event.payload.processed,
          total: event.payload.total,
          filePath: event.payload.file_path,
        });

        // Throttled intermediate query invalidation
        if (event.payload.processed % 100 === 0) {
          if (invalidateTimerRef.current) clearTimeout(invalidateTimerRef.current);
          invalidateTimerRef.current = setTimeout(() => {
            queryClient.invalidateQueries({ queryKey: ['photos'] });
          }, 1500);
        }
      }
    );

    // 2. Indexing Lifecycle
    registerListener("indexing-completed", () => {
      if (invalidateTimerRef.current) clearTimeout(invalidateTimerRef.current);
      setIndexingState('idle');
      setTimeout(() => {
        setIsIndexing(false);
        setIndexingProgress(null);
      }, 1200);
      queryClient.invalidateQueries({ queryKey: ['photos'] });
      queryClient.invalidateQueries({ queryKey: ['analyticsStats'] });
    });

    registerListener("indexing-paused", () => {
      setIndexingState('paused');
    });

    registerListener("indexing-resumed", () => {
      setIndexingState('processing');
      setIsIndexing(true);
    });

    registerListener("indexing-cancelled", () => {
      if (invalidateTimerRef.current) clearTimeout(invalidateTimerRef.current);
      setIndexingState('idle');
      setIsIndexing(false);
      setIndexingProgress(null);
      queryClient.invalidateQueries({ queryKey: ['photos'] });
      queryClient.invalidateQueries({ queryKey: ['analyticsStats'] });
    });

    registerListener("sync-completed", () => {
      queryClient.invalidateQueries({ queryKey: ['photos'] });
    });

    // 3. Model Download Lifecycle
    registerListener<string>("model-download-started", (event) => {
      setIsDownloadingModel(true);
      setDownloadProgress(0);
      if (event.payload) {
        setDownloadModelName(event.payload);
      }
    });

    registerListener<number>("model-download-progress", (event) => {
      setDownloadProgress(event.payload);
    });

    registerListener("model-download-completed", () => {
      setIsDownloadingModel(false);
    });

    return () => {
      isSubscribed = false;
      if (invalidateTimerRef.current) {
        clearTimeout(invalidateTimerRef.current);
      }
      unlisteners.forEach((unlisten) => unlisten());
    };
  }, [
    setIsIndexing,
    setIndexingState,
    setIndexingProgress,
    queryClient,
    setIsDownloadingModel,
    setDownloadProgress,
    setDownloadModelName
  ]);
}
