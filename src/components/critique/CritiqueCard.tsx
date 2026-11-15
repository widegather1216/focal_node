import React from 'react';
import { motion } from 'framer-motion';
import { Maximize2, Copy, Check, Trash2, FileText } from 'lucide-react';
import { CritiqueItem } from '../../types/critique';
import { api } from '../../services/api';
import { useAppStore } from '../../store/useAppStore';
import { CritiqueContentRenderer } from './CritiqueContentRenderer';
import { CritiqueCardHeader } from './CritiqueCardHeader';

interface CritiqueCardProps {
  item: CritiqueItem;
  index: number;
  copiedId: string | null;
  onSelectPhoto: (id: string) => void;
  onOpenFullscreen: (id: string) => void;
  onCopy: (id: string, text: string) => void;
  onDelete: (id: string) => void;
}

const cardBtnStyle: React.CSSProperties = {
  background: 'rgba(255, 255, 255, 0.06)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  color: '#f4f4f5',
  padding: '5px 10px',
  borderRadius: '6px',
  fontSize: '12px',
  fontWeight: 500,
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  gap: '5px',
  whiteSpace: 'nowrap',
  flexShrink: 0,
};

export const CritiqueCard: React.FC<CritiqueCardProps> = ({
  item,
  index,
  copiedId,
  onSelectPhoto,
  onOpenFullscreen,
  onCopy,
  onDelete,
}) => {
  const { openCritiqueDocument } = useAppStore();
  const thumbUrl = api.getPhotoThumbnailUrl(item.photo_id);
  const formattedDate = item.critique_updated_at
    ? new Date(item.critique_updated_at).toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : null;

  return (
    <motion.div
      key={item.photo_id}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.05, 0.3) }}
      style={{
        backgroundColor: 'rgba(24, 24, 27, 0.7)',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.3)',
        transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
      }}
      whileHover={{
        borderColor: 'var(--accent-focal-glow)',
        boxShadow: '0 12px 36px rgba(225, 29, 72, 0.12)',
      }}
    >
      <CritiqueCardHeader
        item={item}
        thumbUrl={thumbUrl}
        formattedDate={formattedDate}
        onSelectPhoto={onSelectPhoto}
      />

      <div
        style={{
          padding: '18px 20px',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          gap: '16px',
        }}
      >
        <div
          style={{
            fontSize: '13px',
            lineHeight: '1.65',
            color: '#e4e4e7',
            maxHeight: '200px',
            overflowY: 'auto',
            paddingRight: '6px',
          }}
        >
          <CritiqueContentRenderer
            content={item.critique}
            mode="compact"
            overallScore={item.overall_score}
            iaaScore={item.iaa_score}
            iqaScore={item.iqa_score}
            istaScore={item.ista_score}
            critiqueEn={item.critique_en}
          />
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingTop: '12px',
            borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          }}
        >
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => openCritiqueDocument(item.photo_id)}
              style={{
                ...cardBtnStyle,
                background: 'var(--accent-focal-subtle)',
                border: '1px solid rgba(225, 29, 72, 0.3)',
                color: 'var(--accent-focal-hover)',
              }}
              title="리포트 문서 뷰어로 크게 보기"
            >
              <FileText size={12} /> 문서로 보기
            </button>
            <button onClick={() => onOpenFullscreen(item.photo_id)} style={cardBtnStyle}>
              <Maximize2 size={12} /> 원본 보기
            </button>
          </div>

          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              onClick={() => onCopy(item.photo_id, item.critique)}
              style={{
                background: copiedId === item.photo_id ? 'var(--accent-focal-subtle)' : 'transparent',
                border: 'none',
                color: copiedId === item.photo_id ? 'var(--accent-focal-hover)' : '#a1a1aa',
                padding: '6px',
                borderRadius: '6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              title="비평 텍스트 복사"
            >
              {copiedId === item.photo_id ? <Check size={14} /> : <Copy size={14} />}
            </button>
            <button
              onClick={() => {
                if (confirm(`'${item.file_name}'의 저장된 비평을 삭제하시겠습니까?`)) {
                  onDelete(item.photo_id);
                }
              }}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#ef4444',
                padding: '6px',
                borderRadius: '6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              title="비평 삭제"
            >
              <Trash2 size={14} />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
