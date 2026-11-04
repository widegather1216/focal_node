import React from 'react';
import { ParsedScores } from '../../utils/critiqueParser';

interface ScoreHudStripProps {
  scores: ParsedScores;
}

/**
 * Camera LCD HUD style compact score strip (Clean Metric).
 */
export const ScoreHudStrip: React.FC<ScoreHudStripProps> = ({ scores }) => {
  return (
    <div
      style={{
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '6px',
        padding: '8px 12px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px'
      }}
    >
      {/* Overall Score */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
        <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em' }}>
          SCORE
        </span>
        <span
          className="font-mono"
          style={{ fontSize: '17px', fontWeight: 700, color: '#fff', letterSpacing: '-0.02em', lineHeight: 1 }}
        >
          {scores.overall ?? '-'}
        </span>
        <span className="font-mono" style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>/ 100</span>
      </div>

      {/* Detail Metrics Chips */}
      <div
        className="font-mono"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '11px',
          color: 'var(--text-secondary)'
        }}
      >
        {scores.iaa !== null && (
          <span title="미학 & 구도 지수 (IAA)">
            <span style={{ color: 'var(--text-muted)', marginRight: '3px' }}>IAA</span>
            <strong style={{ color: '#f4f4f5' }}>{scores.iaa}</strong>
          </span>
        )}
        {scores.iaa !== null && (scores.iqa !== null || scores.ista !== null) && (
          <span style={{ color: 'rgba(255, 255, 255, 0.15)' }}>·</span>
        )}
        {scores.iqa !== null && (
          <span title="화질 & 광학 지수 (IQA)">
            <span style={{ color: 'var(--text-muted)', marginRight: '3px' }}>IQA</span>
            <strong style={{ color: '#f4f4f5' }}>{scores.iqa}</strong>
          </span>
        )}
        {scores.iqa !== null && scores.ista !== null && (
          <span style={{ color: 'rgba(255, 255, 255, 0.15)' }}>·</span>
        )}
        {scores.ista !== null && (
          <span title="구조 & 질감 지수 (ISTA)">
            <span style={{ color: 'var(--text-muted)', marginRight: '3px' }}>ISTA</span>
            <strong style={{ color: '#f4f4f5' }}>{scores.ista}</strong>
          </span>
        )}
      </div>
    </div>
  );
};
