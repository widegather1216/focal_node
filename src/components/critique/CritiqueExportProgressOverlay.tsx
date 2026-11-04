import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, FileText, FileDown, ExternalLink, Loader2 } from 'lucide-react';
import { ExportProgressState } from '../../utils/critiqueExporter';

interface CritiqueExportProgressOverlayProps {
  exportProgress: ExportProgressState;
  photoName?: string | null;
  lastSavedPath: string | null;
  onRevealFile: (path: string) => void;
  onClose: () => void;
}

export const CritiqueExportProgressOverlay: React.FC<CritiqueExportProgressOverlayProps> = ({
  exportProgress,
  photoName,
  lastSavedPath,
  onRevealFile,
  onClose,
}) => {
  return (
    <AnimatePresence>
      {exportProgress.active && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.78)',
            backdropFilter: 'blur(8px)',
            zIndex: 99,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px'
          }}
        >
          <motion.div
            initial={{ scale: 0.94, opacity: 0, y: 10 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.94, opacity: 0, y: 10 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
            style={{
              width: '100%',
              maxWidth: '460px',
              backgroundColor: '#121216',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '16px',
              boxShadow: '0 25px 60px rgba(0, 0, 0, 0.9), 0 0 35px rgba(225, 29, 72, 0.18)',
              padding: '26px 28px',
              boxSizing: 'border-box',
              display: 'flex',
              flexDirection: 'column',
              gap: '18px'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  backgroundColor: exportProgress.percent === 100 ? 'rgba(34, 197, 94, 0.15)' : 'rgba(225, 29, 72, 0.15)',
                  border: `1px solid ${exportProgress.percent === 100 ? 'rgba(34, 197, 94, 0.35)' : 'rgba(225, 29, 72, 0.35)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}
              >
                {exportProgress.percent === 100 ? (
                  <Check size={20} color="#22c55e" />
                ) : exportProgress.type === 'md' ? (
                  <FileText size={20} color="var(--accent-focal-hover)" />
                ) : (
                  <FileDown size={20} color="var(--accent-focal-hover)" />
                )}
              </div>
              <div style={{ overflow: 'hidden' }}>
                <h3 style={{ margin: '0 0 3px 0', fontSize: '15px', fontWeight: 700, color: '#f4f4f5' }}>
                  {exportProgress.title}
                </h3>
                <p style={{ margin: 0, fontSize: '12px', color: '#a1a1aa', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {exportProgress.type === 'md'
                    ? `${photoName ? photoName.replace(/\.[^/.]+$/, "") : "photo"}_AI비평.md`
                    : photoName}
                </p>
              </div>
            </div>

            {/* Progress Gauge Section */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ fontSize: '12.5px', fontWeight: 600, color: '#e4e4e7' }}>
                  {exportProgress.step}
                </span>
                <span
                  className="font-mono"
                  style={{
                    fontSize: '13px',
                    fontWeight: 700,
                    color: exportProgress.percent === 100 ? '#22c55e' : 'var(--accent-focal-hover)'
                  }}
                >
                  {exportProgress.percent}%
                </span>
              </div>

              {/* Progress Bar Track */}
              <div
                style={{
                  width: '100%',
                  height: '7px',
                  backgroundColor: 'rgba(255, 255, 255, 0.08)',
                  borderRadius: '4px',
                  overflow: 'hidden',
                  position: 'relative'
                }}
              >
                <motion.div
                  style={{
                    height: '100%',
                    borderRadius: '4px',
                    background: exportProgress.percent === 100
                      ? 'linear-gradient(90deg, #16a34a 0%, #22c55e 100%)'
                      : 'linear-gradient(90deg, #e11d48 0%, #f43f5e 100%)',
                    boxShadow: exportProgress.percent === 100
                      ? '0 0 10px rgba(34, 197, 94, 0.5)'
                      : '0 0 10px rgba(225, 29, 72, 0.5)',
                    width: `${exportProgress.percent}%`
                  }}
                  transition={{ ease: 'easeOut', duration: 0.3 }}
                />
              </div>

              <span style={{ fontSize: '11.5px', color: '#71717a', lineHeight: 1.4 }}>
                {exportProgress.detail}
              </span>
            </div>

            {/* Footer Action or Status Notice */}
            {exportProgress.percent === 100 && (exportProgress.savedPath || lastSavedPath) ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px', paddingTop: '4px' }}>
                <button
                  onClick={() => onRevealFile(exportProgress.savedPath || lastSavedPath || '')}
                  style={{
                    background: 'rgba(225, 29, 72, 0.15)',
                    border: '1px solid rgba(225, 29, 72, 0.35)',
                    color: 'var(--accent-focal-hover)',
                    padding: '7px 12px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <ExternalLink size={13} />
                  <span>Finder에서 파일 열기</span>
                </button>
                <button
                  onClick={onClose}
                  style={{
                    background: 'rgba(255, 255, 255, 0.08)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#f4f4f5',
                    padding: '7px 14px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  닫기
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: '7px', fontSize: '11px', color: '#71717a' }}>
                <Loader2 size={12} className="spin" color="var(--accent-focal)" />
                <span>{exportProgress.type === 'md' ? '마크다운 리포트를 파일로 저장하고 있습니다...' : '고해상도 렌더링 중입니다. 잠시만 기다려주세요...'}</span>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
