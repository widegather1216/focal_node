import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ZoomOut, ZoomIn, RotateCcw, Eye, Info } from 'lucide-react';

interface FullscreenToolbarProps {
  fileName?: string;
  isVisible: boolean;
  scale: number;
  fitMode: 'fit-height' | 'contain' | 'cover';
  showMetadata: boolean;
  onZoomOut: () => void;
  onZoomIn: () => void;
  onResetZoom: () => void;
  onSelectFitMode: (mode: 'fit-height' | 'contain') => void;
  onToggleZenMode: () => void;
  onToggleMetadata: () => void;
  onClose: () => void;
}

export const FullscreenToolbar: React.FC<FullscreenToolbarProps> = ({
  fileName,
  isVisible,
  scale,
  fitMode,
  showMetadata,
  onZoomOut,
  onZoomIn,
  onResetZoom,
  onSelectFitMode,
  onToggleZenMode,
  onToggleMetadata,
  onClose,
}) => {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -50, opacity: 0 }}
          transition={{ duration: 0.2 }}
          style={{
            position: 'absolute',
            top: '20px',
            left: '20px',
            right: '20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            zIndex: 120,
            pointerEvents: 'none',
          }}
        >
          {/* File Title */}
          <div
            className="glass-panel"
            style={{
              padding: '8px 16px',
              borderRadius: '10px',
              color: '#fff',
              fontSize: '14px',
              fontWeight: 500,
              maxWidth: '300px',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              pointerEvents: 'auto',
            }}
          >
            {fileName || '사진 뷰어'}
          </div>

          {/* Toolbar Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', pointerEvents: 'auto' }}>
            {/* Zoom Controls */}
            <div
              className="glass-panel"
              style={{
                display: 'flex',
                alignItems: 'center',
                borderRadius: '10px',
                padding: '4px',
              }}
            >
              <button
                onClick={onZoomOut}
                style={{ background: 'none', border: 'none', color: '#a1a1aa', padding: '6px', cursor: 'pointer', display: 'flex' }}
                title="축소 (-)"
              >
                <ZoomOut size={16} />
              </button>
              <span style={{ color: '#fff', fontSize: '12px', minWidth: '45px', textAlign: 'center', fontWeight: 600 }}>
                {Math.round(scale * 100)}%
              </span>
              <button
                onClick={onZoomIn}
                style={{ background: 'none', border: 'none', color: '#a1a1aa', padding: '6px', cursor: 'pointer', display: 'flex' }}
                title="확대 (+)"
              >
                <ZoomIn size={16} />
              </button>
              <button
                onClick={onResetZoom}
                style={{
                  background: 'none',
                  border: 'none',
                  color: scale !== 1 ? 'var(--accent-focal-hover)' : '#71717a',
                  padding: '6px',
                  cursor: 'pointer',
                  display: 'flex',
                }}
                title="100% 원본 비율 (0)"
              >
                <RotateCcw size={15} />
              </button>
            </div>

            {/* Fit Mode Switcher */}
            <div
              className="glass-panel"
              style={{
                display: 'flex',
                alignItems: 'center',
                borderRadius: '10px',
                padding: '4px',
                flexShrink: 0,
              }}
            >
              <button
                onClick={() => onSelectFitMode('fit-height')}
                style={{
                  background: fitMode === 'fit-height' ? 'var(--bg-elevated)' : 'none',
                  border: 'none',
                  color: fitMode === 'fit-height' ? '#fff' : 'var(--text-secondary)',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  fontWeight: 500,
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
                title="높이 맞춤"
              >
                높이 맞춤
              </button>
              <button
                onClick={() => onSelectFitMode('contain')}
                style={{
                  background: fitMode === 'contain' ? 'var(--bg-elevated)' : 'none',
                  border: 'none',
                  color: fitMode === 'contain' ? '#fff' : 'var(--text-secondary)',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  fontWeight: 500,
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
                title="전체 맞춤"
              >
                전체 맞춤
              </button>
            </div>

            {/* Zen Mode Button */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onToggleZenMode}
              className="glass-button"
              style={{
                padding: '8px 12px',
                fontSize: '12px',
                fontWeight: 500,
                whiteSpace: 'nowrap',
                flexShrink: 0,
              }}
              title="몰입 모드 (F)"
            >
              <Eye size={15} style={{ flexShrink: 0 }} /> 몰입 모드
            </motion.button>

            {/* EXIF Info Toggle */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onToggleMetadata}
              className="glass-button"
              style={{
                borderColor: showMetadata ? 'var(--accent-focal)' : undefined,
                color: showMetadata ? 'var(--accent-focal)' : undefined,
                padding: '8px 12px',
                fontSize: '12px',
                fontWeight: 500,
                whiteSpace: 'nowrap',
                flexShrink: 0,
              }}
              title="메타데이터 오버레이 토글 (I)"
            >
              <Info size={15} style={{ flexShrink: 0 }} /> EXIF 오버레이
            </motion.button>

            {/* Close Button */}
            <motion.button
              whileHover={{ scale: 1.1, backgroundColor: '#ef4444', color: '#fff' }}
              whileTap={{ scale: 0.9 }}
              onClick={onClose}
              style={{
                background: '#27272a',
                border: 'none',
                color: '#f4f4f5',
                borderRadius: '50%',
                padding: '8px',
                cursor: 'pointer',
                display: 'flex',
                marginLeft: '8px',
                transition: 'all 0.15s ease',
              }}
              title="닫기 (Esc)"
            >
              <X size={20} />
            </motion.button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
