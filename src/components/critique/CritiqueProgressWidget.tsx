import React from 'react';
import { motion } from 'framer-motion';
import { BarChart3, FileText, Languages, Sparkles, CheckCircle2, Loader2 } from 'lucide-react';
import { CritiqueStatus } from '../../types/critique';

interface CritiqueProgressWidgetProps {
  status: CritiqueStatus | null;
  photoId: string;
}

const STEPS = [
  { id: 1, label: '점수 산출 중', icon: BarChart3 },
  { id: 2, label: '비평 작성 중', icon: FileText },
  { id: 3, label: '비평 번역 중', icon: Languages },
  { id: 4, label: '비평 다듬는 중', icon: Sparkles },
];

export const CritiqueProgressWidget: React.FC<CritiqueProgressWidgetProps> = ({ status }) => {
  const currentStep = status?.step || 1;
  const progress = status?.progress || 15;
  const currentMessage = status?.message || '점수 산출 중';

  return (
    <div style={{
      background: 'linear-gradient(145deg, rgba(24, 24, 27, 0.95) 0%, rgba(18, 18, 22, 0.98) 100%)',
      border: '1px solid rgba(168, 85, 247, 0.25)',
      borderRadius: '12px',
      padding: '18px 20px',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
      color: '#f4f4f5',
      marginBottom: '16px',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Glow background effect */}
      <div style={{
        position: 'absolute',
        top: '-40px',
        right: '-40px',
        width: '120px',
        height: '120px',
        background: 'radial-gradient(circle, rgba(168, 85, 247, 0.15) 0%, rgba(0, 0, 0, 0) 70%)',
        pointerEvents: 'none'
      }} />

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '8px',
            background: 'rgba(168, 85, 247, 0.15)',
            border: '1px solid rgba(168, 85, 247, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Loader2 size={16} color="#c084fc" className="spin" />
          </div>
          <div>
            <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#fff', letterSpacing: '-0.01em' }}>
              {currentMessage}
            </h4>
            <span style={{ fontSize: '11px', color: '#a1a1aa' }}>
              AI 모델 추론 진행 중... ({progress}%)
            </span>
          </div>
        </div>
        <span style={{
          fontSize: '12px',
          fontWeight: 700,
          color: '#c084fc',
          background: 'rgba(168, 85, 247, 0.1)',
          padding: '3px 10px',
          borderRadius: '12px',
          border: '1px solid rgba(168, 85, 247, 0.2)'
        }}>
          {currentStep} / {STEPS.length}
        </span>
      </div>

      {/* Progress Bar */}
      <div style={{
        height: '6px',
        backgroundColor: 'rgba(255, 255, 255, 0.08)',
        borderRadius: '3px',
        overflow: 'hidden',
        marginBottom: '16px'
      }}>
        <motion.div
          initial={{ width: '0%' }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          style={{
            height: '100%',
            background: 'linear-gradient(90deg, #a855f7 0%, #6366f1 100%)',
            borderRadius: '3px',
            boxShadow: '0 0 10px rgba(168, 85, 247, 0.5)'
          }}
        />
      </div>

      {/* Step Indicators */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '8px'
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
                gap: '6px',
                padding: '8px 4px',
                borderRadius: '8px',
                backgroundColor: isCurrent ? 'rgba(168, 85, 247, 0.12)' : 'transparent',
                border: isCurrent ? '1px solid rgba(168, 85, 247, 0.3)' : '1px solid transparent',
                transition: 'all 0.3s ease'
              }}
            >
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: isDone
                  ? '#a855f7'
                  : isCurrent
                  ? 'rgba(168, 85, 247, 0.25)'
                  : 'rgba(255, 255, 255, 0.05)',
                color: isDone ? '#fff' : isCurrent ? '#c084fc' : '#71717a',
              }}>
                {isDone ? <CheckCircle2 size={14} /> : <Icon size={13} className={isCurrent ? 'spin-slow' : ''} />}
              </div>
              <span style={{
                fontSize: '11px',
                fontWeight: isCurrent ? 600 : 400,
                color: isDone ? '#e4e4e7' : isCurrent ? '#c084fc' : '#71717a',
                textAlign: 'center',
                whiteSpace: 'nowrap'
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
