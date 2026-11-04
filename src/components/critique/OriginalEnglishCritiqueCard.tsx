import React, { useState } from 'react';
import { Globe, ChevronDown, ChevronUp } from 'lucide-react';

interface OriginalEnglishCritiqueCardProps {
  critiqueEn: string;
  isCompact?: boolean;
}

/**
 * Dedicated Card for UniPercept 8B VQA English Original Feedback.
 */
export const OriginalEnglishCritiqueCard: React.FC<OriginalEnglishCritiqueCardProps> = ({ 
  critiqueEn, 
  isCompact = false 
}) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!critiqueEn || !critiqueEn.trim()) return null;

  return (
    <div
      style={{
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid var(--border-subtle)',
        borderRadius: isCompact ? '6px' : '8px',
        overflow: 'hidden',
        marginTop: isCompact ? '6px' : '14px'
      }}
    >
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: isCompact ? '8px 10px' : '10px 14px',
          background: 'rgba(255, 255, 255, 0.03)',
          border: 'none',
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          textAlign: 'left',
          transition: 'background 0.15s ease'
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)')}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Globe size={isCompact ? 13 : 15} color="var(--accent-focal-hover)" />
          <span style={{ fontSize: isCompact ? '12px' : '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
            UniPercept 8B VQA 영문 원문
          </span>
          <span
            className="font-mono"
            style={{
              fontSize: '10px',
              background: 'var(--accent-focal-subtle)',
              color: 'var(--accent-focal-hover)',
              border: '1px solid rgba(225, 29, 72, 0.25)',
              padding: '1px 5px',
              borderRadius: '4px',
              fontWeight: 600
            }}
          >
            RAW EN
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)', fontSize: '11px' }}>
          <span>{isOpen ? '접기' : '원문 보기'}</span>
          {isOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </div>
      </button>

      {isOpen && (
        <div
          style={{
            padding: isCompact ? '10px 12px' : '14px 18px',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: isCompact ? '12px' : '13.5px',
            lineHeight: '1.65',
            color: '#d4d4d8',
            fontFamily: 'var(--font-mono)',
            whiteSpace: 'pre-wrap',
            backgroundColor: 'rgba(0, 0, 0, 0.25)'
          }}
        >
          {critiqueEn.trim()}
        </div>
      )}
    </div>
  );
};
