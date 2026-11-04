import React from 'react';
import { Sparkles } from 'lucide-react';

interface ExecutiveSummaryCardProps {
  summary: string;
  isCompact?: boolean;
}

export const ExecutiveSummaryCard: React.FC<ExecutiveSummaryCardProps> = ({
  summary,
  isCompact = false
}) => {
  return (
    <div
      style={{
        background: 'rgba(255, 255, 255, 0.02)',
        borderLeft: '2.5px solid var(--accent-focal)',
        borderRadius: '0 6px 6px 0',
        padding: isCompact ? '10px 14px' : '14px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Sparkles size={isCompact ? 12 : 13} color="var(--accent-focal)" />
        <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-focal)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          통합 한 줄 총평
        </span>
      </div>
      <p style={{
        margin: 0,
        fontSize: isCompact ? '13px' : '15px',
        fontWeight: 400,
        color: '#f4f4f5',
        lineHeight: isCompact ? '1.6' : '1.7',
        fontStyle: 'italic',
        letterSpacing: '-0.01em'
      }}>
        "{summary}"
      </p>
    </div>
  );
};
