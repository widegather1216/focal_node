import React from 'react';
import { Wand2, RefreshCw } from 'lucide-react';

interface PhotoCritiqueViewProps {
  critique: string | null;
  loadingCritique: boolean;
  onRequestCritique: () => void;
}

export const PhotoCritiqueView: React.FC<PhotoCritiqueViewProps> = ({
  critique,
  loadingCritique,
  onRequestCritique
}) => {
  return (
    <div style={{ marginTop: '24px', background: '#1a1a1a', padding: '16px', borderRadius: '8px', border: '1px solid #333' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ margin: 0, fontSize: '14px', color: '#888', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Wand2 size={16} color="#a855f7" /> AI 사진 비평 (Gemma VLM)
        </h4>
        <button
          onClick={onRequestCritique}
          disabled={loadingCritique}
          style={{
            background: 'none', border: 'none', color: '#a855f7', cursor: 'pointer',
            fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px'
          }}
        >
          <RefreshCw size={12} className={loadingCritique ? 'spin' : ''} />
          {critique ? '다시 비평받기' : 'AI 비평 생성'}
        </button>
      </div>

      {loadingCritique && (
        <div style={{ color: '#aaa', fontSize: '13px', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <RefreshCw size={14} className="spin" />
          사진 구도, 조명, 색감을 AI 전문가 관점에서 분석 중입니다...
        </div>
      )}

      {!loadingCritique && critique && (
        <div style={{ fontSize: '13px', lineHeight: '1.6', color: '#ddd', whiteSpace: 'pre-line' }}>
          {critique}
        </div>
      )}

      {!loadingCritique && !critique && (
        <p style={{ margin: 0, fontSize: '12px', color: '#666' }}>
          'AI 비평 생성'을 누르면 VLM이 구도, 조명, 색감 및 개선점에 대한 전문가 수준의 피드백을 제공합니다.
        </p>
      )}
    </div>
  );
};
