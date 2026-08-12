import { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';

export function useModelDownloadStatus() {
  const {
    apiPort,
    setIsDownloadingModel,
    setDownloadModelName,
    setDownloadProgress,
    setDownloadBytes,
    setDownloadError,
  } = useAppStore();

  useEffect(() => {
    if (!apiPort) return;

    let isMounted = true;
    let timerId: any = null;

    const checkStatus = async () => {
      try {
        const data = await api.getModelDownloadStatus();
        if (!isMounted || !data || !data.statuses) return;

        const statusList = Object.values(data.statuses);
        const downloadingModel = statusList.find((item) => item.status === 'downloading');

        if (downloadingModel) {
          setIsDownloadingModel(true);
          setDownloadError(null);
          setDownloadModelName(downloadingModel.label);

          const realProgress = typeof downloadingModel.progress === 'number' ? downloadingModel.progress : 0;
          setDownloadProgress(realProgress);

          if (typeof downloadingModel.downloaded_bytes === 'number' && typeof downloadingModel.total_bytes === 'number') {
            setDownloadBytes(downloadingModel.downloaded_bytes, downloadingModel.total_bytes);
          }
          // Fast poll when downloading
          scheduleNext(2000);
        } else {
          const errorModel = statusList.find((item) => item.status === 'error');
          if (errorModel) {
            setIsDownloadingModel(true);
            setDownloadModelName(errorModel.label);
            setDownloadError(errorModel.error_message || '모델 다운로드 중 오류가 발생했습니다.');
            scheduleNext(5000);
          } else {
            const isAllDone = data.overall?.is_all_done || (statusList.length > 0 && statusList.every(item => item.status === 'completed' || item.status === 'cached'));
            if (isAllDone) {
              setDownloadProgress(100);
              setDownloadError(null);
              setTimeout(() => {
                if (isMounted) {
                  setIsDownloadingModel(false);
                }
              }, 800);
            }
            // Slow poll (15s) when all models are cached/idle
            scheduleNext(15000);
          }
        }
      } catch (err) {
        scheduleNext(15000);
      }
    };

    const scheduleNext = (delay: number) => {
      if (!isMounted) return;
      if (timerId) clearTimeout(timerId);
      timerId = setTimeout(checkStatus, delay);
    };

    checkStatus();

    return () => {
      isMounted = false;
      if (timerId) clearTimeout(timerId);
    };
  }, [apiPort, setIsDownloadingModel, setDownloadModelName, setDownloadProgress, setDownloadBytes, setDownloadError]);
}
