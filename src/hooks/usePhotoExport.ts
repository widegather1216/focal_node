import { useEffect, useRef, useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { api } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { ExportFeedback } from '../utils/exportStream';
import { createPhotoExportController, PhotoExportController } from '../utils/photoExport';

async function pickExportDestinationFolder(): Promise<string | null> {
  const selectedDir = await open({
    directory: true,
    multiple: false,
    title: '사진을 내보낼 대상 폴더를 선택하세요',
  });
  if (!selectedDir) return null;

  const targetFolder = Array.isArray(selectedDir) ? selectedDir[0] : selectedDir;
  return targetFolder || null;
}

export function usePhotoExport() {
  const [exporting, setExporting] = useState(false);
  const [feedback, setFeedback] = useState<ExportFeedback | null>(null);

  const isMountedRef = useRef(true);
  const controllerRef = useRef<PhotoExportController | null>(null);

  const getController = (): PhotoExportController => {
    if (controllerRef.current === null) {
      controllerRef.current = createPhotoExportController({
        getApiPort: () => useAppStore.getState().apiPort,
        getSelectedPhotoIds: () => useAppStore.getState().selectedPhotoIds,
        deselectPhotoIds: (ids) => useAppStore.getState().deselectPhotoIds(ids),
        pickDestinationFolder: pickExportDestinationFolder,
        exportPhotos: (photoIds, destinationFolder, signal) =>
          api.exportPhotos(photoIds, destinationFolder, signal),
        isMounted: () => isMountedRef.current,
        onExportingChange: setExporting,
        onFeedbackChange: setFeedback,
      });
    }
    return controllerRef.current;
  };

  useEffect(() => {
    // Re-arm on mount because React.StrictMode invokes cleanup once between initial checks.
    isMountedRef.current = true;
    const controller = getController();
    const unsubscribe = useAppStore.subscribe((currentState, previousState) => {
      if (currentState.selectedPhotoIds.size === 0 && previousState.selectedPhotoIds.size > 0) {
        controller.resetOnEmptySelection();
      }
    });
    if (useAppStore.getState().selectedPhotoIds.size === 0) {
      controller.resetOnEmptySelection();
    }
    return () => {
      isMountedRef.current = false;
      unsubscribe();
      controller.dispose();
    };
  }, []);

  return {
    exporting,
    feedback,
    dismissFeedback: () => getController().dismissFeedback(),
    handleExport: () => getController().handleExport(),
  };
}
