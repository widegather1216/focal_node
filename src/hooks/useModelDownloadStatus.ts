import { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';

export function useModelDownloadStatus() {
  const {
    apiPort,
    setIsDownloadingModel,
    setDownloadModelName,
    setDownloadProgress,
  } = useAppStore();

  useEffect(() => {
    if (!apiPort) return;

    let isMounted = true;
    let smoothProgress = 10;

    const checkStatus = async () => {
      try {
        const data = await api.getModelDownloadStatus();
        if (!isMounted || !data || !data.statuses) return;

        const statusList = Object.values(data.statuses);
        const downloadingModel = statusList.find((item) => item.status === 'downloading');

        if (downloadingModel) {
          setIsDownloadingModel(true);
          setDownloadModelName(downloadingModel.label);

          // Smoothly advance progress up to 95% without ever dropping back down
          smoothProgress = Math.min(95, smoothProgress + Math.floor(Math.random() * 3) + 2);
          setDownloadProgress(smoothProgress);
        } else {
          const isAllDone = statusList.length > 0 && statusList.every(item => item.status === 'completed' || item.status === 'cached');
          if (isAllDone) {
            setDownloadProgress(100);
            setTimeout(() => {
              if (isMounted) {
                setIsDownloadingModel(false);
              }
            }, 800);
          }
        }
      } catch (err) {
        // Silently ignore during initial boot or transient network glitches
      }
    };

    // Immediate check + interval polling every 2 seconds
    checkStatus();
    const interval = setInterval(checkStatus, 2000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [apiPort, setIsDownloadingModel, setDownloadModelName, setDownloadProgress]);
}
