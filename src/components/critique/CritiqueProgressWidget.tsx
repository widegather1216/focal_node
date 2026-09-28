import React from 'react';
import { motion } from 'framer-motion';
import { BarChart3, FileText, Languages, Sparkles, CheckCircle2, Loader2, Square } from 'lucide-react';
import { CritiqueStatus } from '../../types/critique';

interface CritiqueProgressWidgetProps {
  status: CritiqueStatus | null;
  photoId: string;
  onCancel?: () => void;
}

const STEPS = [
  { id: 1, label: '시각 채점', icon: BarChart3 },
  { id: 2, label: '심층 비평', icon: FileText },
  { id: 3, label: '한국어 번역', icon: Languages },
  { id: 4, label: '평론 완성', icon: Sparkles },
];

export const CritiqueProgressWidget: React.FC<CritiqueProgressWidgetProps> = ({ status, onCancel }) => {
  const currentStep = status?.step || 1;
  const progress = status?.progress || 15;
  const currentMessage = status?.message || '시각 점수 산출 중';

  return (
    <div style={{
      backgroundColor: 'var(--bg-surface)',
      border: '1px solid var(--border-subtle)',
      borderRadius: '8px',
      padding: '14px 16px',
      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4)',
      color: 'var(--text-primary)',
      marginBottom: '14px',
      position: 'relative',
      overflow: 'hidden',
      userSelect: 'none'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
          <div style={{
            width: '26px',
            height: '26px',
            borderRadius: '6px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            <Loader2 size={14} color="var(--accent-focal)" className="spin" />
          </div>
          <div style={{ minWidth: 0, flex: 1, overflow: 'hidden' }}>
            <h4 style={{
              margin: 0,
              fontSize: '13px',
              fontWeight: 600,
              color: 'var(--text-primary)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}>
              {currentMessage}
            </h4>
            <div style={{
              fontSize: '11px',
              color: 'var(--text-muted)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              marginTop: '1px'
            }}>
              <span>AI 모델 추론 진행 중</span>
              <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>({progress}%)</span>
            </div>
          </div>
        </div>

        {/* Right Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
          <span className="font-mono" style={{
            fontSize: '11px',
            fontWeight: 600,
            color: 'var(--accent-focal)',
            backgroundColor: 'var(--bg-card)',
            padding: '2px 8px',
            borderRadius: '4px',
            border: '1px solid var(--border-subtle)',
            whiteSpace: 'nowrap'
          }}>
            {currentStep} / {STEPS.length}
          </span>
          {onCancel && (
            <button
              onClick={onCancel}
              style={{
                background: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#f87171',
                borderRadius: '4px',
                padding: '3px 7px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                whiteSpace: 'nowrap',
                flexShrink: 0
              }}
              title="비평 생성 중단"
            >
              <Square size={9} fill="#f87171" style={{ flexShrink: 0 }} />
              <span>중단</span>
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div style={{
        height: '4px',
        backgroundColor: 'rgba(255, 255, 255, 0.08)',
        borderRadius: '2px',
        overflow: 'hidden',
        marginBottom: '12px'
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

      {/* Step Indicators (Compact 4-column grid with no awkward text wrap) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '4px'
      }}>
        {STEPS.map((step) => {
          const Icon = step.icon;
          const isDone = currentStep > step.id;
          const isCurrent = currentStep === step.id;

          return (
            <div
              key={step.id}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '5px',
                padding: '6px 2px',
                borderRadius: '6px',
                backgroundColor: isCurrent ? 'var(--bg-card)' : 'transparent',
                border: isCurrent ? '1px solid var(--border-active)' : '1px solid transparent',
                transition: 'all 0.2s ease',
                overflow: 'hidden'
              }}
            >
              <div
                style={{
                  width: '22px',
                  height: '22px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: isDone
                    ? 'var(--accent-focal)'
                    : isCurrent
                    ? 'var(--accent-focal-subtle)'
                    : 'rgba(255, 255, 255, 0.05)',
                  border: isCurrent
                    ? '1px solid var(--accent-focal)'
                    : isDone
                    ? '1px solid var(--accent-focal)'
                    : '1px solid var(--border-subtle)',
                  color: isDone ? '#fff' : isCurrent ? 'var(--accent-focal)' : 'var(--text-muted)',
                  flexShrink: 0
                }}
              >
                {isDone ? (
                  <CheckCircle2 size={13} />
                ) : isCurrent ? (
                  <Loader2 size={12} className="spin" />
                ) : (
                  <Icon size={12} />
                )}
              </div>
              <span style={{
                fontSize: '10.5px',
                fontWeight: isCurrent ? 600 : 400,
                color: isDone ? 'var(--text-primary)' : isCurrent ? 'var(--accent-focal)' : 'var(--text-muted)',
                textAlign: 'center',
                whiteSpace: 'nowrap',
                letterSpacing: '-0.02em',
                lineHeight: 1.2
              }}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
