import React from 'react';
import { motion } from 'framer-motion';
import { Camera, Calendar, Eye, ExternalLink, Maximize2, Copy, Check, Trash2 } from 'lucide-react';
import { CritiqueItem } from '../../types/critique';
import { api } from '../../services/api';

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
  padding: '5px 11px',
  borderRadius: '6px',
  fontSize: '12px',
  fontWeight: 500,
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '5px'
};

export const CritiqueCard: React.FC<CritiqueCardProps> = ({
  item,
  index,
  copiedId,
  onSelectPhoto,
  onOpenFullscreen,
  onCopy,
  onDelete
}) => {
  const thumbUrl = api.getPhotoThumbnailUrl(item.photo_id);
  const formattedDate = item.critique_updated_at 
    ? new Date(item.critique_updated_at).toLocaleDateString('ko-KR', {
        year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
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
        transition: 'border-color 0.2s ease, box-shadow 0.2s ease'
      }}
      whileHover={{
        borderColor: 'rgba(168, 85, 247, 0.3)',
        boxShadow: '0 12px 36px rgba(168, 85, 247, 0.12)'
      }}
    >
      {/* Top Thumbnail & Photo Info Bar */}
      <div style={{
        display: 'flex',
        height: '140px',
        background: '#121215',
        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
        position: 'relative'
      }}>
        <div 
          onClick={() => onSelectPhoto(item.photo_id)}
          style={{
            width: '140px',
            height: '140px',
            flexShrink: 0,
            cursor: 'pointer',
            position: 'relative',
            overflow: 'hidden',
            backgroundColor: '#18181b'
          }}
        >
          <img
            src={thumbUrl}
            alt={item.file_name}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transition: 'transform 0.3s ease'
            }}
          />
          <div 
            style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(0,0,0,0.3)',
              opacity: 0,
              transition: 'opacity 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
            className="thumb-overlay"
          >
            <Eye size={20} color="#fff" />
          </div>
        </div>

        <div style={{
          flex: 1,
          padding: '14px 16px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          overflow: 'hidden'
        }}>
          <div>
            <h4 
              onClick={() => onSelectPhoto(item.photo_id)}
              style={{
                margin: '0 0 6px 0',
                fontSize: '14px',
                fontWeight: 600,
                color: '#f4f4f5',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                cursor: 'pointer'
              }}
              title={item.file_name}
            >
              {item.file_name}
            </h4>

            {/* Metadata Tags */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '11px', color: '#a1a1aa' }}>
              {item.camera_model && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Camera size={12} color="#c084fc" />
                  <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.camera_model} {item.lens_model ? `• ${item.lens_model}` : ''}
                  </span>
                </div>
              )}

              {(item.f_number || item.shutter_speed || item.iso) && (
                <div style={{ display: 'flex', gap: '8px', color: '#71717a' }}>
                  {item.f_number && <span>f/{item.f_number}</span>}
                  {item.shutter_speed && <span>{item.shutter_speed}s</span>}
                  {item.iso && <span>ISO {item.iso}</span>}
                </div>
              )}
            </div>
          </div>

          {formattedDate && (
            <div style={{ fontSize: '11px', color: '#71717a', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Calendar size={11} />
              <span>{formattedDate} 생성</span>
            </div>
          )}
        </div>
      </div>

      {/* Critique Text Box */}
      <div style={{
        padding: '18px 20px',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '16px'
      }}>
        <div style={{
          fontSize: '13px',
          lineHeight: '1.65',
          color: '#e4e4e7',
          whiteSpace: 'pre-line',
          maxHeight: '180px',
          overflowY: 'auto',
          paddingRight: '6px'
        }}>
          {item.critique}
        </div>

        {/* Card Action Footer */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingTop: '12px',
          borderTop: '1px solid rgba(255, 255, 255, 0.06)'
        }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={() => onSelectPhoto(item.photo_id)} style={cardBtnStyle}>
              <ExternalLink size={12} /> 상세 패널
            </button>
            <button onClick={() => onOpenFullscreen(item.photo_id)} style={cardBtnStyle}>
              <Maximize2 size={12} /> 원본 보기
            </button>
          </div>

          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              onClick={() => onCopy(item.photo_id, item.critique)}
              style={{
                background: copiedId === item.photo_id ? 'rgba(74, 222, 128, 0.15)' : 'transparent',
                border: 'none',
                color: copiedId === item.photo_id ? '#4ade80' : '#a1a1aa',
                padding: '6px',
                borderRadius: '6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
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
                justifyContent: 'center'
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
