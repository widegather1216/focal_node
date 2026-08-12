import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Sparkles, X, ChevronRight } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { api } from '../../services/api';
import { CritiqueStatus } from '../../types/critique';

export const GlobalCritiqueToast: React.FC = () => {
  const { activeCritiqueJob, setActiveCritiqueJob, selectedPhotoId, setSelectedPhotoId } = useAppStore();
  const [status, setStatus] = useState<CritiqueStatus | null>(null);

  // Poll status when active job exists
  useEffect(() => {
    if (!activeCritiqueJob?.photoId) {
      setStatus(null);
      return;
    }

    let isMounted = true;
    let intervalId: any = null;

    const pollStatus = async () => {
      try {
        const res = await api.getCritiqueStatus(activeCritiqueJob.photoId);
        if (isMounted && res) {
          setStatus(res);
          if (res.status === 'completed' || res.status === 'error' || res.progress === 100) {
            if (intervalId) clearInterval(intervalId);
            setTimeout(() => {
              if (isMounted) {
                setActiveCritiqueJob(null);
              }
            }, 4000);
          }
        }
      } catch (e) {
        // Silently ignore transient errors
      }
    };

    pollStatus();
    intervalId = setInterval(pollStatus, 1200);

    return () => {
      isMounted = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, [activeCritiqueJob?.photoId, setActiveCritiqueJob]);

  // Show floating toast only when job exists AND DetailPanel for that photo is closed
  const isDetailOpen = selectedPhotoId === activeCritiqueJob?.photoId;
  const isVisible = Boolean(activeCritiqueJob && !isDetailOpen);

  if (!activeCritiqueJob) return null;

  const currentMessage = status?.message || '비평 생성 진행 중';
  const progress = status?.progress || 15;
  const isCompleted = status?.status === 'completed' || progress === 100;

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
            left: '10px',
            bottom: '16px',
            zIndex: 100,
            width: '240px',
            background: 'linear-gradient(145deg, rgba(24, 24, 27, 0.98) 0%, rgba(15, 15, 18, 0.99) 100%)',
            border: '1px solid rgba(168, 85, 247, 0.35)',
            borderRadius: '12px',
            padding: '14px 14px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6), 0 0 16px rgba(168, 85, 247, 0.2)',
            backdropFilter: 'blur(16px)',
            color: '#f4f4f5',
            cursor: 'pointer',
            overflow: 'hidden',
            boxSizing: 'border-box'
          }}
        >
          {/* Ambient Glow */}
          <div style={{
            position: 'absolute',
            top: '-30px',
            right: '-30px',
            width: '90px',
            height: '90px',
            background: 'radial-gradient(circle, rgba(168, 85, 247, 0.2) 0%, rgba(0, 0, 0, 0) 70%)',
            pointerEvents: 'none'
          }} />

          {/* Header Row */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '6px',
                background: isCompleted ? 'rgba(34, 197, 94, 0.2)' : 'rgba(168, 85, 247, 0.2)',
                border: isCompleted ? '1px solid rgba(34, 197, 94, 0.4)' : '1px solid rgba(168, 85, 247, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}>
                {isCompleted ? (
                  <Sparkles size={13} color="#4ade80" />
                ) : (
                  <Loader2 size={13} color="#c084fc" className="spin" />
                )}
              </div>
              <span style={{ fontSize: '12px', fontWeight: 600, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '130px' }}>
                {isCompleted ? '비평 완료' : currentMessage}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '2px', flexShrink: 0 }}>
              <span style={{ fontSize: '11px', color: '#c084fc', fontWeight: 700 }}>
                {progress}%
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveCritiqueJob(null);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#71717a',
                  cursor: 'pointer',
                  padding: '2px',
                  display: 'flex',
                  alignItems: 'center'
                }}
                title="닫기"
              >
                <X size={13} />
              </button>
            </div>
          </div>

          {/* File Name & Subtext */}
          <div style={{
            fontSize: '11px',
            color: '#a1a1aa',
            marginBottom: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <span style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              maxWidth: '140px',
              color: '#d4d4d8'
            }}>
              {activeCritiqueJob.fileName || '사진 AI 비평 중'}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '1px', color: '#c084fc', fontSize: '10px', fontWeight: 600 }}>
              상세보기 <ChevronRight size={11} />
            </span>
          </div>

          {/* Animated Progress Bar */}
          <div style={{
            height: '5px',
            backgroundColor: 'rgba(255, 255, 255, 0.08)',
            borderRadius: '3px',
            overflow: 'hidden'
          }}>
            <motion.div
              initial={{ width: '0%' }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
              style={{
                height: '100%',
                background: isCompleted
                  ? 'linear-gradient(90deg, #22c55e 0%, #4ade80 100%)'
                  : 'linear-gradient(90deg, #a855f7 0%, #6366f1 100%)',
                borderRadius: '3px',
                boxShadow: isCompleted
                  ? '0 0 10px rgba(34, 197, 94, 0.5)'
                  : '0 0 10px rgba(168, 85, 247, 0.5)'
              }}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
