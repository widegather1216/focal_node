import React from 'react';
import { motion } from 'framer-motion';
import { Award, Check, Copy, RefreshCw, ChevronUp, ChevronDown, X, Loader2, AlertCircle } from 'lucide-react';
import { CritiqueSummaryResponse } from '../../types/critique';

interface CritiqueSummaryCardProps {
  isGeneratingSummary: boolean;
  summaryData: CritiqueSummaryResponse | null;
  summaryError: string | null;
  copiedSummary: boolean;
  isSummaryExpanded: boolean;
  totalCritiques: number;
  onCopySummary: () => void;
  onGenerateSummary: () => void;
  onToggleExpand: () => void;
  onCloseSummary: () => void;
}

export const CritiqueSummaryCard: React.FC<CritiqueSummaryCardProps> = ({
  isGeneratingSummary,
  summaryData,
  summaryError,
  copiedSummary,
  isSummaryExpanded,
  totalCritiques,
  onCopySummary,
  onGenerateSummary,
  onToggleExpand,
  onCloseSummary
}) => {
  if (!isGeneratingSummary && !summaryData && !summaryError) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -15, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -15, scale: 0.98 }}
      transition={{ duration: 0.3 }}
      style={{
        maxWidth: '1600px',
        margin: '0 auto 28px auto',
        background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.08) 0%, rgba(99, 102, 241, 0.05) 100%)',
        border: '1px solid rgba(168, 85, 247, 0.25)',
        borderRadius: '16px',
        overflow: 'hidden',
        boxShadow: '0 8px 32px rgba(168, 85, 247, 0.12)',
        position: 'relative'
      }}
    >
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: isSummaryExpanded ? '1px solid rgba(168, 85, 247, 0.15)' : 'none',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(24, 24, 27, 0.4)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Award size={20} color="#c084fc" />
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#fff' }}>
            AI 포트폴리오 비평 종합 리포트
          </h3>
          {summaryData && (
            <span style={{
              background: 'rgba(168, 85, 247, 0.2)',
              color: '#e9d5ff',
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '10px',
              fontWeight: 500
            }}>
              {summaryData.total_critiques_analyzed}개 비평 종합 분석
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {summaryData && (
            <>
              <button
                onClick={onCopySummary}
                style={{
                  background: copiedSummary ? 'rgba(74, 222, 128, 0.15)' : 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: copiedSummary ? '#4ade80' : '#e4e4e7',
                  padding: '5px 10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px'
                }}
              >
                {copiedSummary ? <Check size={13} /> : <Copy size={13} />}
                {copiedSummary ? '복사됨' : '요약 복사'}
              </button>
              <button
                onClick={onGenerateSummary}
                disabled={isGeneratingSummary}
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#e4e4e7',
                  padding: '5px 10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px'
                }}
              >
                <RefreshCw size={13} className={isGeneratingSummary ? 'spin' : ''} />
                다시 요약
              </button>
            </>
          )}

          <button
            onClick={onToggleExpand}
            style={{
              background: 'none',
              border: 'none',
              color: '#a1a1aa',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            {isSummaryExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>

          <button
            onClick={onCloseSummary}
            style={{
              background: 'none',
              border: 'none',
              color: '#71717a',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center'
            }}
            title="요약 닫기"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Body */}
      {isSummaryExpanded && (
        <div style={{ padding: '20px 24px' }}>
          {isGeneratingSummary && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#c084fc', padding: '12px 0' }}>
              <Loader2 size={20} className="spin" />
              <span style={{ fontSize: '14px', fontWeight: 500 }}>
                Gemma VLM이 {totalCritiques}개의 사진 비평 데이터와 EXIF 정보를 종합하여 포트폴리오를 총체적으로 분석하고 있습니다...
              </span>
            </div>
          )}

          {summaryError && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ef4444', fontSize: '13px' }}>
              <AlertCircle size={16} />
              <span>{summaryError}</span>
            </div>
          )}

          {!isGeneratingSummary && summaryData && (
            <div style={{
              fontSize: '14px',
              lineHeight: '1.75',
              color: '#f4f4f5',
              whiteSpace: 'pre-line',
              maxHeight: '400px',
              overflowY: 'auto',
              paddingRight: '8px'
            }}>
              {summaryData.summary}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
};
