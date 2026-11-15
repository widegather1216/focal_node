import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Sliders, X } from 'lucide-react';
import { ScoringGuideContent } from './ScoringGuideContent';

export interface ScoringGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ScoringGuideModal: React.FC<ScoringGuideModalProps> = ({ isOpen, onClose }) => {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialogRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      onClose();
    };

    // Capture phase prevents Escape from leaking to underlying CritiqueDocumentModal listeners.
    window.addEventListener('keydown', handleKeyDown, true);
    return () => {
      window.removeEventListener('keydown', handleKeyDown, true);
      previousFocus?.focus();
    };
  }, [isOpen, onClose]);

  if (!isOpen || typeof document === 'undefined') {
    return null;
  }

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label="점수 산출 기준 가이드"
      ref={dialogRef}
      tabIndex={-1}
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(9, 9, 11, 0.82)',
        backdropFilter: 'blur(8px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        outline: 'none',
      }}
    >
      <div
        onClick={(event) => event.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: '680px',
          maxHeight: '85vh',
          backgroundColor: 'var(--bg-canvas)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '12px',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.65)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-subtle)',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={18} color="var(--accent-focal)" />
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
              6-Way 지각 앙상블 평점 산출 가이드
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="가이드 닫기"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'color 0.15s ease, background 0.15s ease',
            }}
            onMouseEnter={(event) => {
              event.currentTarget.style.color = 'var(--text-primary)';
              event.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.06)';
            }}
            onMouseLeave={(event) => {
              event.currentTarget.style.color = 'var(--text-muted)';
              event.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <X size={18} />
          </button>
        </div>

        <ScoringGuideContent />

        <div
          style={{
            padding: '12px 20px',
            borderTop: '1px solid var(--border-subtle)',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            display: 'flex',
            justifyContent: 'flex-end',
          }}
        >
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '7px 18px',
              backgroundColor: 'var(--accent-focal)',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              fontSize: '12.5px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'background 0.15s ease',
            }}
            onMouseEnter={(event) => (event.currentTarget.style.backgroundColor = 'var(--accent-focal-hover)')}
            onMouseLeave={(event) => (event.currentTarget.style.backgroundColor = 'var(--accent-focal)')}
          >
            확인
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};
