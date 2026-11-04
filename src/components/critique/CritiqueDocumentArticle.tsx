import React from 'react';
import { Loader2, Info } from 'lucide-react';
import { PhotoDetail } from '../../hooks/usePhotoDetail';
import { CritiqueScores } from '../../utils/critiqueExporter';
import { CritiqueContentRenderer } from './CritiqueContentRenderer';

interface MastheadData {
  scores: CritiqueScores | null;
  summary: string | null;
}

interface CritiqueDocumentArticleProps {
  photo: PhotoDetail | null | undefined;
  isLoading: boolean;
  critiqueText: string;
  mastheadData: MastheadData;
}

export const CritiqueDocumentArticle: React.FC<CritiqueDocumentArticleProps> = ({
  photo,
  isLoading,
  critiqueText,
  mastheadData,
}) => {
  return (
    <div
      className="print-paper"
      style={{
        flex: '1 1 54%',
        backgroundColor: '#111115',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      <div
        style={{
          maxWidth: '820px',
          width: '100%',
          margin: '0 auto',
          padding: '36px 40px 60px 40px',
          boxSizing: 'border-box'
        }}
      >
        {/* 1. Unified Editorial Masthead */}
        <div style={{ marginBottom: '20px' }}>
          <h1 style={{
            margin: '0 0 14px 0',
            fontSize: '24px',
            fontWeight: 700,
            color: '#fff',
            letterSpacing: '-0.02em',
            lineHeight: '1.3'
          }}>
            {photo?.file_name}
          </h1>

          {/* Editorial Lead Subtitle (Executive Summary or Caption) */}
          {(mastheadData.summary || photo?.ai_analysis?.caption) && (
            <p style={{
              margin: '0 0 20px 0',
              fontSize: '15px',
              lineHeight: '1.65',
              color: '#e4e4e7',
              fontStyle: 'italic',
              letterSpacing: '-0.01em'
            }}>
              "{mastheadData.summary || photo?.ai_analysis?.caption}"
            </p>
          )}

          {/* 1-Line Minimal Spec Divider */}
          {mastheadData.scores && (
            <div style={{
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '12px 0 0 0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px'
            }}>
              {/* Overall Score */}
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em' }}>
                  TOTAL
                </span>
                <span className="font-mono" style={{ fontSize: '19px', fontWeight: 700, color: 'var(--accent-focal-hover)', letterSpacing: '-0.02em', lineHeight: 1 }}>
                  {mastheadData.scores.overall ?? '-'}
                </span>
                <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  / 100
                </span>
              </div>

              {/* Detail Metrics Chips */}
              <div
                className="font-mono"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  fontSize: '11.5px',
                  color: 'var(--text-secondary)'
                }}
              >
                {mastheadData.scores.iaa !== null && (
                  <span title="미학 & 구도 지수 (IAA)">
                    <span style={{ color: 'var(--text-muted)', marginRight: '3px' }}>IAA</span>
                    <strong style={{ color: '#fff' }}>{mastheadData.scores.iaa}</strong>
                  </span>
                )}
                {mastheadData.scores.iaa !== null && (mastheadData.scores.iqa !== null || mastheadData.scores.ista !== null) && (
                  <span style={{ color: 'rgba(255, 255, 255, 0.2)' }}>·</span>
                )}
                {mastheadData.scores.iqa !== null && (
                  <span title="화질 & 광학 지수 (IQA)">
                    <span style={{ color: 'var(--text-muted)', marginRight: '3px' }}>IQA</span>
                    <strong style={{ color: '#fff' }}>{mastheadData.scores.iqa}</strong>
                  </span>
                )}
                {mastheadData.scores.iqa !== null && mastheadData.scores.ista !== null && (
                  <span style={{ color: 'rgba(255, 255, 255, 0.2)' }}>·</span>
                )}
                {mastheadData.scores.ista !== null && (
                  <span title="구조 & 질감 지수 (ISTA)">
                    <span style={{ color: 'var(--text-muted)', marginRight: '3px' }}>ISTA</span>
                    <strong style={{ color: '#fff' }}>{mastheadData.scores.ista}</strong>
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Content Renderer or Empty State */}
        {isLoading ? (
          <div style={{ padding: '60px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#a1a1aa' }}>
            <Loader2 size={24} className="spin" color="var(--accent-focal)" style={{ marginBottom: '12px' }} />
            <p style={{ margin: 0, fontSize: '14px' }}>비평 데이터를 불러오는 중입니다...</p>
          </div>
        ) : critiqueText ? (
          <div id="critique-rendered-body">
            <CritiqueContentRenderer
              content={critiqueText}
              mode="document"
              hideScoreboard={!!mastheadData.scores}
              hideExecutiveSummary={!!mastheadData.summary}
              overallScore={photo?.ai_analysis?.overall_score}
              iaaScore={photo?.ai_analysis?.iaa_score}
              iqaScore={photo?.ai_analysis?.iqa_score}
              istaScore={photo?.ai_analysis?.ista_score}
              critiqueEn={photo?.ai_analysis?.critique_en}
            />
          </div>
        ) : (
          <div style={{
            padding: '60px 20px',
            textAlign: 'center',
            background: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '16px',
            border: '1px dashed rgba(255, 255, 255, 0.1)'
          }}>
            <Info size={32} color="#71717a" style={{ marginBottom: '12px' }} />
            <h4 style={{ margin: '0 0 8px 0', color: '#f4f4f5', fontSize: '16px' }}>
              아직 생성된 비평이 없습니다
            </h4>
            <p style={{ margin: 0, color: '#71717a', fontSize: '13px' }}>
              우측 패널에서 'AI 비평 생성'을 요청하시면 전문가 평론이 이곳에 기록됩니다.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
