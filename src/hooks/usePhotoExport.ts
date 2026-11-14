import { useEffect, useRef, useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { api } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import {
  evaluateExportOutcome,
  ExportFeedback,
  ExportResult,
  isAbortError,
} from '../utils/exportStream';

const SUCCESS_AUTO_CLEAR_MS = 1800;

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

function formatCaughtErrorFeedback(caughtErr: unknown): ExportFeedback {
  const rawMsg =
    caughtErr instanceof Error && caughtErr.message.trim()
      ? caughtErr.message.trim()
      : '내보내기 도중 오류가 발생했습니다.';
  const formattedMsg = rawMsg.startsWith('내보내기 실패') ? rawMsg : `내보내기 실패: ${rawMsg}`;
  return { kind: 'error', message: formattedMsg, detail: rawMsg };
}

export function usePhotoExport() {
  const { apiPort, selectedPhotoIds, deselectPhotoIds } = useAppStore();
  const [exporting, setExporting] = useState(false);
  const [feedback, setFeedback] = useState<ExportFeedback | null>(null);

  const isMountedRef = useRef(true);
  const isBusyRef = useRef(false);
  const requestIdRef = useRef(0);
  const feedbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const clearFeedbackTimer = () => {
    if (feedbackTimerRef.current !== null) {
      clearTimeout(feedbackTimerRef.current);
      feedbackTimerRef.current = null;
    }
  };

  useEffect(() => {
    // Re-arm on mount because React.StrictMode invokes cleanup once between initial checks.
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      clearFeedbackTimer();
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (selectedPhotoIds.size === 0) {
      clearFeedbackTimer();
      setFeedback(null);
    }
  }, [selectedPhotoIds.size]);

  const dismissFeedback = () => {
    clearFeedbackTimer();
    setFeedback(null);
  };

  const applyExportOutcome = (exportResult: ExportResult, targetPhotoIds: string[]) => {
    const outcome = evaluateExportOutcome(exportResult, targetPhotoIds.length);
    setFeedback(outcome);

    if (outcome.kind === 'success') {
      feedbackTimerRef.current = setTimeout(() => {
        if (!isMountedRef.current) return;
        deselectPhotoIds(targetPhotoIds);
        setFeedback(null);
        feedbackTimerRef.current = null;
      }, SUCCESS_AUTO_CLEAR_MS);
      return;
    }

    if (outcome.kind === 'partial' && exportResult.exported_ids.length > 0 && exportResult.failed_ids.length > 0) {
      // Keep failed items selected so retrying only re-exports failed photos without duplicating successes.
      deselectPhotoIds(exportResult.exported_ids);
    }
  };

  const handleExport = async () => {
    if (!apiPort || isBusyRef.current) return;
    if (useAppStore.getState().selectedPhotoIds.size === 0) return;

    clearFeedbackTimer();
    isBusyRef.current = true;
    const currentRequestId = ++requestIdRef.current;
    setExporting(true);
    setFeedback(null);

    let controller: AbortController | null = null;
    try {
      const targetFolder = await pickExportDestinationFolder();
      if (!targetFolder || !isMountedRef.current || requestIdRef.current !== currentRequestId) {
        return;
      }

      const targetPhotoIds = Array.from(new Set(useAppStore.getState().selectedPhotoIds));
      if (targetPhotoIds.length === 0) return;

      controller = new AbortController();
      abortControllerRef.current = controller;

      const exportResult = await api.exportPhotos(targetPhotoIds, targetFolder, controller.signal);
      if (!isMountedRef.current || requestIdRef.current !== currentRequestId) {
        return;
      }
      applyExportOutcome(exportResult, targetPhotoIds);
    } catch (caughtErr: unknown) {
      if (isAbortError(caughtErr)) {
        // Explicit abort on unmount/reset must not surface as a user-facing export failure.
        return;
      }
      if (!isMountedRef.current || requestIdRef.current !== currentRequestId) {
        return;
      }
      console.error('Export error:', caughtErr);
      setFeedback(formatCaughtErrorFeedback(caughtErr));
    } finally {
      if (controller && abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
      if (requestIdRef.current === currentRequestId) {
        isBusyRef.current = false;
        if (isMountedRef.current) {
          setExporting(false);
        }
      }
    }
  };

  return { exporting, feedback, dismissFeedback, handleExport };
}
