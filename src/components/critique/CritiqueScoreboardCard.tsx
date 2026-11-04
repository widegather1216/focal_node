import React, { useState } from 'react';
import { Sliders, HelpCircle, Sparkles, Camera, Layers } from 'lucide-react';
import { ParsedScores } from '../../utils/critiqueParser';
import { ScoringGuideModal } from './ScoringGuideModal';

interface CritiqueScoreboardCardProps {
  scores: ParsedScores;
  isCompact?: boolean;
}

const ScoreBar: React.FC<{ 
  label: string; 
  score: number; 
  color: string; 
  isCompact: boolean;
  icon?: React.ReactNode;
}> = ({
  label,
  score,
  color,
  isCompact,
  icon
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: isCompact ? '11px' : '12px' }}>
        <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '5px' }}>
          {icon}
          <span>{label}</span>
        </span>
        <span style={{ color: '#fff', fontWeight: 600 }} className="font-mono">{score}</span>
      </div>
      <div style={{
        height: isCompact ? '3px' : '4px',
        backgroundColor: 'rgba(255, 255, 255, 0.06)',
        borderRadius: '2px',
        overflow: 'hidden'
      }}>
        <div
          style={{
            height: '100%',
            width: `${Math.min(100, Math.max(0, score))}%`,
            backgroundColor: color,
            borderRadius: '2px',
            transition: 'width 0.8s ease'
          }}
        />
      </div>
    </div>
  );
};

export const CritiqueScoreboardCard: React.FC<CritiqueScoreboardCardProps> = ({ 
  scores, 
  isCompact = false 
}) => {
  const [isGuideOpen, setIsGuideOpen] = useState(false);

  return (
    <div
      style={{
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid var(--border-subtle)',
        borderRadius: isCompact ? '8px' : '10px',
        padding: isCompact ? '12px 14px' : '16px 20px',
        marginBottom: isCompact ? '12px' : '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: isCompact ? '10px' : '14px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={isCompact ? 14 : 16} color="var(--accent-focal)" />
          <span style={{ fontSize: isCompact ? '12.5px' : '14px', fontWeight: 600, color: '#f4f4f5', letterSpacing: '-0.01em' }}>
            6-Way 지각 앙상블 평점
          </span>
        </div>
        <button
          type="button"
          onClick={() => setIsGuideOpen(true)}
          title="점수 산출 기준 가이드 열기"
          aria-label="점수 산출 기준 가이드"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            padding: isCompact ? '2px 6px' : '3px 8px',
            color: 'var(--text-secondary)',
            fontSize: isCompact ? '10.5px' : '11.5px',
            cursor: 'pointer',
            transition: 'color 0.15s ease, background-color 0.15s ease, border-color 0.15s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = 'var(--text-primary)';
            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)';
            e.currentTarget.style.borderColor = 'rgba(225, 29, 72, 0.3)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = 'var(--text-secondary)';
            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
            e.currentTarget.style.borderColor = 'var(--border-subtle)';
          }}
        >
          <HelpCircle size={isCompact ? 11 : 13} color="var(--accent-focal)" />
          <span>점수 산출 가이드</span>
        </button>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: isCompact ? '1fr' : '120px 1fr',
        gap: isCompact ? '10px' : '24px',
        alignItems: 'center'
      }}>
        {scores.overall !== null && (
          <div style={{
            display: 'flex',
            flexDirection: isCompact ? 'row' : 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: isCompact ? '8px' : '2px',
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '8px',
            padding: isCompact ? '8px 12px' : '12px 14px'
          }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.06em' }}>
              SCORE
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '3px' }}>
              <span className="font-mono" style={{ fontSize: isCompact ? '20px' : '26px', fontWeight: 700, color: '#fff', letterSpacing: '-0.02em', lineHeight: 1 }}>
                {scores.overall}
              </span>
              <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>/ 100</span>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: isCompact ? '6px' : '8px' }}>
          {scores.iaa !== null && (
            <ScoreBar 
              icon={<Sparkles size={12} color="var(--accent-focal-hover)" style={{ flexShrink: 0 }} />}
              label="미학 & 구도 지수 (IAA)" 
              score={scores.iaa} 
              color="var(--accent-focal-hover)" 
              isCompact={isCompact} 
            />
          )}
          {scores.iqa !== null && (
            <ScoreBar 
              icon={<Camera size={12} color="var(--accent-focal)" style={{ flexShrink: 0 }} />}
              label="화질 & 광학 지수 (IQA)" 
              score={scores.iqa} 
              color="var(--accent-focal)" 
              isCompact={isCompact} 
            />
          )}
          {scores.ista !== null && (
            <ScoreBar 
              icon={<Layers size={12} color="var(--accent-focal-deep)" style={{ flexShrink: 0 }} />}
              label="구조 & 질감 지수 (ISTA)" 
              score={scores.ista} 
              color="var(--accent-focal-deep)" 
              isCompact={isCompact} 
            />
          )}
        </div>
      </div>

      {isGuideOpen && (
        <ScoringGuideModal 
          isOpen={isGuideOpen} 
          onClose={() => setIsGuideOpen(false)} 
        />
      )}
    </div>
  );
};
