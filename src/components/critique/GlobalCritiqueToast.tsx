import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Sparkles, X, ChevronRight } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { api } from '../../services/api';
import { CritiqueStatus } from '../../types/critique';

export const GlobalCritiqueToast: React.FC = () => {
  const {
    activeCritiqueJob,
    setActiveCritiqueJob,
    cancelActiveCritique,
    selectedPhotoId,
    setSelectedPhotoId
  } = useAppStore();
  const [status, setStatus] = useState<CritiqueStatus | null>(null);

  // Poll status when active job exists
  useEffect(() => {
    if (!activeCritiqueJob?.photoId) {
      setStatus(null);
      return;
    }

    let isMounted = true;
    let timerId: ReturnType<typeof setTimeout> | null = null;
    let dismissTimerId: ReturnType<typeof setTimeout> | null = null;

    const pollStatus = async () => {
      try {
        const res = await api.getCritiqueStatus(activeCritiqueJob.photoId);
        if (!isMounted) return;

        if (res) {
          setStatus(res);
          const isDone = res.status === 'completed' || res.status === 'error' || res.status === 'cancelled' || res.progress === 100;
          if (isDone) {
            dismissTimerId = setTimeout(() => {
              if (isMounted) {
                setActiveCritiqueJob(null);
              }
            }, 4000);
            return;
          }
        }
      } catch {
        // Silently ignore transient network errors
      }

      if (isMounted) {
        timerId = setTimeout(pollStatus, 1200);
      }
    };

    pollStatus();

    return () => {
      isMounted = false;
      if (timerId) clearTimeout(timerId);
      if (dismissTimerId) clearTimeout(dismissTimerId);
    };
  }, [activeCritiqueJob?.photoId, setActiveCritiqueJob]);

  // Show floating toast only when job exists AND DetailPanel for that photo is closed
  const isDetailOpen = selectedPhotoId === activeCritiqueJob?.photoId;
  const isVisible = Boolean(activeCritiqueJob && !isDetailOpen);

  if (!activeCritiqueJob) return null;

  const currentMessage = status?.message || '비평 생성 진행 중';
  const progress = status?.progress || 15;
  const isCompleted = status?.status === 'completed' || status?.status === 'error' || status?.status === 'cancelled' || progress === 100;

  const handleCloseOrCancel = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!isCompleted && activeCritiqueJob?.photoId) {
      await cancelActiveCritique(activeCritiqueJob.photoId);
    } else {
      setActiveCritiqueJob(null);
    }
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 15, scale: 0.95 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          onClick={() => setSelectedPhotoId(activeCritiqueJob.photoId)}
          style={{
            position: 'fixed',
            left: '14px',
            bottom: '16px',
            zIndex: 100,
            width: '260px',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '10px',
            padding: '12px 14px',
            boxShadow: '0 12px 32px rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(16px)',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            overflow: 'hidden',
            boxSizing: 'border-box',
            userSelect: 'none'
          }}
        >
          {/* Header Row */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '6px',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}>
                {isCompleted ? (
                  <Sparkles size={13} color="var(--accent-focal)" />
                ) : (
                  <Loader2 size={13} color="var(--accent-focal)" className="spin" />
                )}
              </div>
              <span style={{
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-primary)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                flex: 1
              }}>
                {isCompleted ? '비평 생성 완료' : currentMessage}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
              <span className="font-mono" style={{ fontSize: '11px', color: 'var(--accent-focal)', fontWeight: 700, whiteSpace: 'nowrap' }}>
                {progress}%
              </span>
              <button
                onClick={handleCloseOrCancel}
                style={{
                  background: 'none',
                  border: 'none',
                  color: isCompleted ? 'var(--text-muted)' : '#f87171',
                  cursor: 'pointer',
                  padding: '2px',
                  display: 'flex',
                  alignItems: 'center',
                  borderRadius: '4px',
                  flexShrink: 0
                }}
                title={isCompleted ? "닫기" : "비평 중단"}
              >
                <X size={14} />
              </button>
            </div>
          </div>

          {/* File Name & Subtext */}
          <div style={{
            fontSize: '11px',
            color: 'var(--text-muted)',
            marginBottom: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px'
          }}>
            <span style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flex: 1,
              color: 'var(--text-secondary)'
            }}>
              {activeCritiqueJob.fileName || '사진 AI 비평 중'}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '2px', color: 'var(--accent-focal)', fontSize: '10px', fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0 }}>
              상세보기 <ChevronRight size={11} style={{ flexShrink: 0 }} />
            </span>
          </div>

          {/* Animated Progress Bar */}
          <div style={{
            height: '4px',
            backgroundColor: 'rgba(255, 255, 255, 0.08)',
            borderRadius: '2px',
            overflow: 'hidden'
          }}>
            <motion.div
              initial={{ width: '0%' }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
              style={{
                height: '100%',
                backgroundColor: 'var(--accent-focal)',
                borderRadius: '2px'
              }}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
