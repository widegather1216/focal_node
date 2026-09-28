import React, { useEffect, useState, useMemo } from 'react';
import { 
  Wand2, 
  RefreshCw, 
  Trash2, 
  FileText, 
  Square, 
  ArrowUpRight, 
  ChevronDown, 
  ChevronUp 
} from 'lucide-react';
import { api } from '../../services/api';
import { CritiqueStatus } from '../../types/critique';
import { CritiqueProgressWidget } from '../critique/CritiqueProgressWidget';
import { 
  CritiqueContentRenderer, 
  extractScoreboard, 
  parseMarkdownToBlocks,
  ParsedScores 
} from '../critique/CritiqueContentRenderer';
import { useAppStore } from '../../store/useAppStore';

interface PhotoCritiqueViewProps {
  photoId?: string;
  critique: string | null;
  loadingCritique: boolean;
  onRequestCritique: () => void;
  onCancelCritique?: () => void;
  onDeleteCritique?: () => void;
}

/**
 * Camera LCD HUD style compact score strip (Clean Metric).
 */
const ScoreHudStrip: React.FC<{ scores: ParsedScores }> = ({ scores }) => {
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

export const PhotoCritiqueView: React.FC<PhotoCritiqueViewProps> = ({
  photoId,
  critique,
  loadingCritique,
  onRequestCritique,
  onCancelCritique,
  onDeleteCritique
}) => {
  const { openCritiqueDocument } = useAppStore();
  const [status, setStatus] = useState<CritiqueStatus | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  // Status polling for running critique tasks
  useEffect(() => {
    if (!loadingCritique || !photoId) {
      setStatus(null);
      return;
    }

    let isMounted = true;
    let timerId: ReturnType<typeof setTimeout> | null = null;

    const pollStatus = async () => {
      try {
        const res = await api.getCritiqueStatus(photoId);
        if (!isMounted) return;

        if (res) {
          setStatus(res);
          if (res.status === 'completed' || res.status === 'error' || res.status === 'cancelled' || res.progress === 100) {
            return;
          }
        }
      } catch {
        // Silently ignore transient network errors
      }

      if (isMounted) {
        timerId = setTimeout(pollStatus, 1200);
      }
    };

    pollStatus();

    const handleWake = () => {
      if (isMounted) pollStatus();
    };
    window.addEventListener('focus', handleWake);
    window.addEventListener('online', handleWake);
    document.addEventListener('visibilitychange', handleWake);

    return () => {
      isMounted = false;
      if (timerId) clearTimeout(timerId);
      window.removeEventListener('focus', handleWake);
      window.removeEventListener('online', handleWake);
      document.removeEventListener('visibilitychange', handleWake);
    };
  }, [loadingCritique, photoId]);

  // Reset accordion collapse state when switching photos
  useEffect(() => {
    setIsExpanded(false);
  }, [photoId]);

  // Structured critique parsing (scores, executive summary, sections)
  const parsedCritique = useMemo(() => {
    if (!critique) return null;
    const { scores, remainingText } = extractScoreboard(critique);
    const blocks = parseMarkdownToBlocks(remainingText);
    const summaryBlock = blocks.find((b) => b.type === 'executive_summary');
    const summary = summaryBlock && 'summary' in summaryBlock ? summaryBlock.summary : null;
    const sectionCount = blocks.filter((b) => b.type === 'section').length;
    return { scores, summary, sectionCount, remainingText };
  }, [critique]);

  return (
    <div
      style={{
        marginTop: '20px',
        background: 'var(--bg-card)',
        padding: '16px',
        borderRadius: '8px',
        border: '1px solid var(--border-subtle)'
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: critique && !loadingCritique ? '12px' : '8px'
        }}
      >
        <h4
          style={{
            margin: 0,
            fontSize: '12px',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Wand2 size={14} color="var(--accent-focal)" /> AI 사진 비평
        </h4>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {loadingCritique ? (
            onCancelCritique && (
              <button
                onClick={onCancelCritique}
                style={{
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.35)',
                  color: '#ef4444',
                  cursor: 'pointer',
                  fontSize: '11px',
                  fontWeight: 600,
                  padding: '3px 8px',
                  borderRadius: '5px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 0.15s ease'
                }}
                title="진행 중인 비평 생성을 안전하게 중단합니다"
              >
                <Square size={10} fill="#ef4444" />
                중단
              </button>
            )
          ) : critique ? (
            <>
              <button
                onClick={onRequestCritique}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  fontSize: '11.5px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '2px 4px',
                  transition: 'color 0.15s ease'
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-focal)')}
                onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
                title="AI 비평 다시 분석"
              >
                <RefreshCw size={11} />
                <span>다시 분석</span>
              </button>

              {onDeleteCritique && (
                <button
                  onClick={() => {
                    if (confirm('저장된 비평을 삭제하시겠습니까?')) {
                      onDeleteCritique();
                    }
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    padding: '2px',
                    display: 'flex',
                    alignItems: 'center',
                    transition: 'color 0.15s ease'
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
                  onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
                  title="비평 삭제"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </>
          ) : (
            <button
              onClick={onRequestCritique}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-focal)',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: 0
              }}
            >
              <RefreshCw size={11} />
              <span>AI 비평 생성</span>
            </button>
          )}
        </div>
      </div>

      {/* Loading Progress State */}
      {loadingCritique && (
        <CritiqueProgressWidget status={status} photoId={photoId || ''} onCancel={onCancelCritique} />
      )}

      {/* Completed Critique Content */}
      {!loadingCritique && critique && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* 1. Score Strip (If score block is present) */}
          {parsedCritique?.scores && (
            <ScoreHudStrip scores={parsedCritique.scores} />
          )}

          {/* 2. Editorial Executive Summary */}
          {parsedCritique?.summary && (
            <div
              style={{
                borderLeft: '2px solid var(--accent-focal)',
                paddingLeft: '10px',
                margin: '2px 0'
              }}
            >
              <p
                style={{
                  margin: 0,
                  fontSize: '12.5px',
                  lineHeight: '1.6',
                  color: 'var(--text-primary)',
                  fontStyle: 'italic',
                  letterSpacing: '-0.01em'
                }}
              >
                "{parsedCritique.summary}"
              </p>
            </div>
          )}

          {/* 3. Primary CTA: Open Document Report */}
          <button
            onClick={() => photoId && openCritiqueDocument(photoId)}
            style={{
              width: '100%',
              background: 'rgba(225, 29, 72, 0.08)',
              border: '1px solid rgba(225, 29, 72, 0.25)',
              borderRadius: '7px',
              padding: '9px 12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              color: 'var(--text-primary)',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(225, 29, 72, 0.14)';
              e.currentTarget.style.borderColor = 'var(--accent-focal)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(225, 29, 72, 0.08)';
              e.currentTarget.style.borderColor = 'rgba(225, 29, 72, 0.25)';
            }}
            title="문서 뷰어로 전체 비평 보기"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={14} color="var(--accent-focal)" />
              <span style={{ fontSize: '12px', fontWeight: 600 }}>전체 비평 읽기</span>
            </div>
            <ArrowUpRight size={14} color="var(--accent-focal-hover)" />
          </button>

          {/* 4. Detailed Sections Collapsible Accordion */}
          {parsedCritique && parsedCritique.sectionCount > 0 ? (
            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
              <button
                onClick={() => setIsExpanded((prev) => !prev)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '11px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '4px 2px',
                  width: '100%',
                  transition: 'color 0.15s ease'
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
                onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  <span>{isExpanded ? '세부 분석 내용 접기' : '세부 분석 내용 펼쳐보기'}</span>
                </span>
                <span style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>
                  {parsedCritique.sectionCount}개 항목
                </span>
              </button>

              {isExpanded && (
                <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <CritiqueContentRenderer
                    content={critique}
                    mode="compact"
                    hideScoreboard
                    hideExecutiveSummary
                  />
                </div>
              )}
            </div>
          ) : !parsedCritique?.scores && !parsedCritique?.summary ? (
            /* Fallback for unformatted generic critique text */
            <div style={{ marginTop: '4px' }}>
              <CritiqueContentRenderer content={critique} mode="compact" />
            </div>
          ) : null}
        </div>
      )}

      {/* Empty State */}
      {!loadingCritique && !critique && (
        <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
          'AI 비평 생성'을 누르면 VLM이 구도, 조명, 색감 및 개선점에 대한 전문가 수준의 피드백을 제공합니다.
        </p>
      )}
    </div>
  );
};
