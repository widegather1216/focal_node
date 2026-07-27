import { useEffect } from 'react';
import { listen } from '@tauri-apps/api/event';
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

  useEffect(() => {
    const unlistenProgress = listen<{ processed: number; total: number; file_path: string }>(
      "indexing-progress",
      (event) => {
        setIndexingState('processing');
        setIndexingProgress({
          processed: event.payload.processed,
          total: event.payload.total,
          filePath: event.payload.file_path,
        });

        if (event.payload.processed % 100 === 0) {
          setTimeout(() => {
            queryClient.invalidateQueries({ queryKey: ['photos'] });
          }, 1500);
        }
      }
    );

    const unlistenCompleted = listen("indexing-completed", () => {
      setIndexingState('idle');
      setIsIndexing(false);
      setIndexingProgress(null);
      queryClient.invalidateQueries({ queryKey: ['photos'] });
      queryClient.invalidateQueries({ queryKey: ['analyticsStats'] });
    });

    const unlistenPaused = listen("indexing-paused", () => {
      setIndexingState('paused');
    });

    const unlistenResumed = listen("indexing-resumed", () => {
      setIndexingState('processing');
      setIsIndexing(true);
    });

    const unlistenCancelled = listen("indexing-cancelled", () => {
      setIndexingState('idle');
      setIsIndexing(false);
      setIndexingProgress(null);
      queryClient.invalidateQueries({ queryKey: ['photos'] });
      queryClient.invalidateQueries({ queryKey: ['analyticsStats'] });
    });

    const unlistenSync = listen("sync-completed", () => {
      queryClient.invalidateQueries({ queryKey: ['photos'] });
    });

    const unlistenDownloadStarted = listen<string>("model-download-started", (event) => {
      setIsDownloadingModel(true);
      setDownloadProgress(0);
      if (event.payload) {
        setDownloadModelName(event.payload);
      }
    });

    const unlistenDownloadProgress = listen<number>("model-download-progress", (event) => {
      setDownloadProgress(event.payload);
    });

    const unlistenDownloadCompleted = listen("model-download-completed", () => {
      setIsDownloadingModel(false);
    });

    return () => {
      unlistenProgress.then((unlisten) => unlisten());
      unlistenCompleted.then((unlisten) => unlisten());
      unlistenPaused.then((unlisten) => unlisten());
      unlistenResumed.then((unlisten) => unlisten());
      unlistenCancelled.then((unlisten) => unlisten());
      unlistenSync.then((unlisten) => unlisten());
      unlistenDownloadStarted.then((unlisten) => unlisten());
      unlistenDownloadProgress.then((unlisten) => unlisten());
      unlistenDownloadCompleted.then((unlisten) => unlisten());
    };
  }, [setIsIndexing, setIndexingState, setIndexingProgress, queryClient, setIsDownloadingModel, setDownloadProgress, setDownloadModelName]);
}
