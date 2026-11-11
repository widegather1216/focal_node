import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, CheckCircle2, Download, Loader2, RotateCcw, X } from 'lucide-react';
import { open } from '@tauri-apps/plugin-dialog';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';
import {
  evaluateExportOutcome,
  ExportFeedback,
  ExportOutcomeKind,
  ExportResult,
  isAbortError,
} from '../utils/exportStream';

const SUCCESS_AUTO_CLEAR_MS = 1800;

interface BannerTheme {
  border: string;
  backgroundColor: string;
  textColor: string;
}

function getBannerTheme(feedbackKind: ExportOutcomeKind | null): BannerTheme {
  if (feedbackKind === 'error') {
    return {
      border: '1px solid rgba(225, 29, 72, 0.55)',
      backgroundColor: 'rgba(32, 14, 20, 0.95)',
      textColor: '#fda4af',
    };
  }
  if (feedbackKind === 'partial') {
    return {
      border: '1px solid rgba(245, 158, 11, 0.5)',
      backgroundColor: 'rgba(28, 20, 12, 0.95)',
      textColor: '#fde68a',
    };
  }
  if (feedbackKind === 'success') {
    return {
      border: '1px solid rgba(16, 185, 129, 0.45)',
      backgroundColor: 'rgba(18, 18, 21, 0.94)',
      textColor: 'var(--text-primary)',
    };
  }
  return {
    border: '1px solid var(--border-subtle)',
    backgroundColor: 'rgba(18, 18, 21, 0.92)',
    textColor: 'var(--text-primary)',
  };
}

function renderFeedbackIcon(feedbackKind: ExportOutcomeKind) {
  if (feedbackKind === 'error') {
    return <AlertTriangle size={14} color="var(--accent-focal-hover)" style={{ flexShrink: 0 }} />;
  }
  if (feedbackKind === 'partial') {
    return <AlertTriangle size={14} color="var(--accent-amber)" style={{ flexShrink: 0 }} />;
  }
  return <CheckCircle2 size={14} color="var(--accent-emerald)" style={{ flexShrink: 0 }} />;
}

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

export function ActionBar() {
  const { apiPort, selectedPhotoIds, clearSelection, deselectPhotoIds } = useAppStore();
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

  const formatCaughtErrorFeedback = (caughtErr: unknown): ExportFeedback => {
    const rawMsg =
      caughtErr instanceof Error && caughtErr.message.trim()
        ? caughtErr.message.trim()
        : '내보내기 도중 오류가 발생했습니다.';
    const formattedMsg = rawMsg.startsWith('내보내기 실패') ? rawMsg : `내보내기 실패: ${rawMsg}`;
    return { kind: 'error', message: formattedMsg, detail: rawMsg };
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

  const theme = getBannerTheme(feedback ? feedback.kind : null);
  const canRecover = feedback?.kind === 'error' || feedback?.kind === 'partial';

  return (
    <AnimatePresence>
      {selectedPhotoIds.size > 0 && (
        <motion.div
          role={canRecover ? 'alert' : 'status'}
          initial={{ y: 100, opacity: 0, x: '-50%' }}
          animate={{ y: 0, opacity: 1, x: '-50%' }}
          exit={{ y: 100, opacity: 0, x: '-50%' }}
          style={{
            position: 'fixed',
            bottom: '24px',
            left: '50%',
            maxWidth: 'calc(100vw - 48px)',
            backgroundColor: theme.backgroundColor,
            border: theme.border,
            color: theme.textColor,
            padding: '8px 16px',
            borderRadius: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            boxShadow: '0 16px 36px rgba(0,0,0,0.7)',
            zIndex: 50,
            backdropFilter: 'blur(16px)',
            userSelect: 'none',
          }}
        >
          <span
            title={feedback?.detail ? `${feedback.message}\n${feedback.detail}` : feedback?.message}
            style={{
              fontWeight: 500,
              fontSize: '12px',
              color: theme.textColor,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              minWidth: 0,
            }}
          >
            {feedback ? (
              <>
                {renderFeedbackIcon(feedback.kind)}
                <span
                  style={{
                    maxWidth: '420px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {feedback.message}
                </span>
              </>
            ) : (
              <>
                <span className="font-mono" style={{ fontWeight: 700, color: 'var(--accent-focal)' }}>
                  {selectedPhotoIds.size}
                </span>
                <span style={{ color: 'var(--text-secondary)' }}>장의 사진 선택됨</span>
              </>
            )}
          </span>

          {!feedback && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
              <motion.button
                onClick={handleExport}
                disabled={exporting}
                whileHover={exporting ? {} : { scale: 1.02, backgroundColor: 'var(--accent-focal-hover)' }}
                whileTap={exporting ? {} : { scale: 0.97 }}
                transition={{ type: 'spring', stiffness: 400, damping: 15 }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: 'var(--accent-focal)',
                  color: '#fff',
                  border: 'none',
                  padding: '6px 14px',
                  borderRadius: '16px',
                  cursor: exporting ? 'not-allowed' : 'pointer',
                  fontWeight: 600,
                  fontSize: '12px',
                }}
              >
                {exporting ? <Loader2 size={13} className="spin" /> : <Download size={13} />}
                {exporting ? '내보내는 중...' : '내보내기'}
              </motion.button>

              <motion.button
                onClick={clearSelection}
                disabled={exporting}
                whileHover={exporting ? {} : { scale: 1.1, backgroundColor: 'var(--bg-elevated)', color: 'var(--text-primary)' }}
                whileTap={exporting ? {} : { scale: 0.9 }}
                transition={{ type: 'spring', stiffness: 500, damping: 15 }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: 'var(--bg-card)',
                  color: 'var(--text-muted)',
                  border: '1px solid var(--border-subtle)',
                  padding: '6px',
                  borderRadius: '50%',
                  cursor: exporting ? 'not-allowed' : 'pointer',
                  opacity: exporting ? 0.5 : 1,
                }}
                title="선택 해제"
              >
                <X size={13} />
              </motion.button>
            </div>
          )}

          {canRecover && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
              <button
                onClick={handleExport}
                disabled={exporting}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  backgroundColor: 'var(--accent-focal)',
                  color: '#fff',
                  border: 'none',
                  padding: '5px 12px',
                  borderRadius: '14px',
                  cursor: exporting ? 'not-allowed' : 'pointer',
                  fontWeight: 600,
                  fontSize: '11px',
                }}
              >
                <RotateCcw size={12} />
                다시 시도
              </button>
              <button
                onClick={dismissFeedback}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: 'rgba(255, 255, 255, 0.08)',
                  color: theme.textColor,
                  border: '1px solid rgba(255, 255, 255, 0.14)',
                  padding: '5px',
                  borderRadius: '50%',
                  cursor: 'pointer',
                }}
                title="알림 닫기"
              >
                <X size={12} />
              </button>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
