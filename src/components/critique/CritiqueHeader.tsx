import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Search, Wand2, Loader2, Clock, Award } from 'lucide-react';

export type CritiqueSortBy = 'recent' | 'overall_score' | 'iaa_score';

interface CritiqueHeaderProps {
  critiqueCount: number;
  sortBy: CritiqueSortBy;
  onSortByChange: (sortBy: CritiqueSortBy) => void;
  filterQuery: string;
  onFilterQueryChange: (query: string) => void;
  onGenerateSummary: () => void;
  isGeneratingSummary: boolean;
}

export const CritiqueHeader: React.FC<CritiqueHeaderProps> = ({
  critiqueCount,
  sortBy,
  onSortByChange,
  filterQuery,
  onFilterQueryChange,
  onGenerateSummary,
  isGeneratingSummary,
}) => {
  return (
    <header style={{
      padding: '16px 28px',
      borderBottom: '1px solid var(--border-subtle)',
      backgroundColor: 'var(--bg-surface)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '20px',
      zIndex: 10
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '8px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Sparkles size={18} color="var(--accent-focal)" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '16px', fontWeight: 600, margin: 0, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
              AI 사진 비평 & 큐레이션
            </h1>
            <span className="font-mono" style={{
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-subtle)',
              padding: '2px 8px',
              borderRadius: '10px',
              fontSize: '11px',
              fontWeight: 500
            }}>
              {critiqueCount} 컷
            </span>
          </div>
          <p style={{ margin: '2px 0 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>
            AI가 분석한 사진의 미학적 구도와 광학적 디테일 평론 보관함
          </p>
        </div>
      </div>

      {/* Right Header Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {critiqueCount > 0 && (
          <>
            {/* Sort By Segmented Toggle */}
            <div
              style={{
                display: 'inline-flex',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '2px',
                gap: '2px',
                alignItems: 'center',
                flexShrink: 0
              }}
            >
              {(
                [
                  { id: 'recent', label: '최신순', icon: <Clock size={12} /> },
                  { id: 'overall_score', label: '종합평점순', icon: <Award size={12} /> },
                  { id: 'iaa_score', label: '미학점수순', icon: <Sparkles size={12} /> },
                ] as const
              ).map((opt) => {
                const isActive = sortBy === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => onSortByChange(opt.id)}
                    style={{
                      border: 'none',
                      borderRadius: '4px',
                      padding: '4px 9px',
                      fontSize: '11.5px',
                      fontWeight: isActive ? 600 : 500,
                      cursor: 'pointer',
                      backgroundColor: isActive ? 'var(--accent-focal-subtle)' : 'transparent',
                      color: isActive ? 'var(--accent-focal-hover)' : 'var(--text-secondary)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      transition: 'all 0.15s ease',
                      outline: 'none',
                      whiteSpace: 'nowrap'
                    }}
                    title={`${opt.label}으로 정렬`}
                  >
                    {opt.icon}
                    <span>{opt.label}</span>
                  </button>
                );
              })}
            </div>

            <div style={{ position: 'relative', width: '220px' }}>
              <Search size={13} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                placeholder="비평 / 태그 검색..."
                value={filterQuery}
                onChange={(e) => onFilterQueryChange(e.target.value)}
                style={{
                  width: '100%',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '6px 10px 6px 28px',
                  color: 'var(--text-primary)',
                  fontSize: '12px',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            <motion.button
              onClick={onGenerateSummary}
              disabled={isGeneratingSummary}
              whileHover={!isGeneratingSummary ? { scale: 1.02, backgroundColor: 'var(--bg-elevated)', borderColor: 'var(--border-active)' } : {}}
              whileTap={!isGeneratingSummary ? { scale: 0.98 } : {}}
              style={{
                backgroundColor: 'var(--bg-card)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-subtle)',
                padding: '7px 14px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 500,
                cursor: isGeneratingSummary ? 'not-allowed' : 'pointer',
                opacity: isGeneratingSummary ? 0.6 : 1,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                whiteSpace: 'nowrap',
                flexShrink: 0,
                transition: 'all 0.15s ease'
              }}
            >
              {isGeneratingSummary ? (
                <>
                  <Loader2 size={13} className="spin" color="var(--accent-focal)" style={{ flexShrink: 0 }} />
                  <span style={{ whiteSpace: 'nowrap' }}>요약 분석 중...</span>
                </>
              ) : (
                <>
                  <Wand2 size={13} color="var(--accent-focal)" style={{ flexShrink: 0 }} />
                  <span style={{ whiteSpace: 'nowrap' }}>종합 포트폴리오 요약</span>
                </>
              )}
            </motion.button>
          </>
        )}
      </div>
    </header>
  );
};
