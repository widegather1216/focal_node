import React, { useEffect, useState } from 'react';
import { Wand2, RefreshCw, Trash2 } from 'lucide-react';
import { api } from '../../services/api';
import { CritiqueStatus } from '../../types/critique';
import { CritiqueProgressWidget } from '../critique/CritiqueProgressWidget';

interface PhotoCritiqueViewProps {
  photoId?: string;
  critique: string | null;
  loadingCritique: boolean;
  onRequestCritique: () => void;
  onDeleteCritique?: () => void;
}

export const PhotoCritiqueView: React.FC<PhotoCritiqueViewProps> = ({
  photoId,
  critique,
  loadingCritique,
  onRequestCritique,
  onDeleteCritique
}) => {
  const [status, setStatus] = useState<CritiqueStatus | null>(null);

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
          if (res.status === 'completed' || res.status === 'error' || res.progress === 100) {
            return;
          }
        }
      } catch {
        // Silently ignore transient errors
      }

      if (isMounted) {
        timerId = setTimeout(pollStatus, 1200);
      }
    };

    pollStatus();

    return () => {
      isMounted = false;
      if (timerId) clearTimeout(timerId);
    };
  }, [loadingCritique, photoId]);

  return (
    <div style={{ marginTop: '24px', background: '#1a1a1a', padding: '16px', borderRadius: '8px', border: '1px solid #333' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ margin: 0, fontSize: '14px', color: '#888', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Wand2 size={16} color="#a855f7" /> AI 사진 비평 (Gemma VLM)
        </h4>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
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
          {!loadingCritique && critique && onDeleteCritique && (
            <button
              onClick={onDeleteCritique}
              style={{
                background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer',
                fontSize: '12px', display: 'flex', alignItems: 'center', padding: '2px'
              }}
              title="비평 삭제"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      {loadingCritique && (
        <CritiqueProgressWidget status={status} photoId={photoId || ''} />
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
