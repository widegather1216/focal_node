import React from 'react';
import { Camera, Calendar, Eye } from 'lucide-react';
import { CritiqueItem } from '../../types/critique';

interface CritiqueCardHeaderProps {
  item: CritiqueItem;
  thumbUrl: string;
  formattedDate: string | null;
  onSelectPhoto: (id: string) => void;
}

export const CritiqueCardHeader: React.FC<CritiqueCardHeaderProps> = ({
  item,
  thumbUrl,
  formattedDate,
  onSelectPhoto,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        height: '140px',
        background: '#121215',
        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
        position: 'relative',
      }}
    >
      <div
        onClick={() => onSelectPhoto(item.photo_id)}
        style={{
          width: '140px',
          height: '140px',
          flexShrink: 0,
          cursor: 'pointer',
          position: 'relative',
          overflow: 'hidden',
          backgroundColor: '#18181b',
        }}
      >
        <img
          src={thumbUrl}
          alt={item.file_name}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transition: 'transform 0.3s ease',
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
            gap: '8px',
          }}
          className="thumb-overlay"
        >
          <Eye size={20} color="#fff" />
        </div>
      </div>

      <div
        style={{
          flex: 1,
          padding: '14px 16px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          overflow: 'hidden',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
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
                cursor: 'pointer',
                flex: 1,
              }}
              title={item.file_name}
            >
              {item.file_name}
            </h4>

            {item.overall_score !== null && item.overall_score !== undefined && (
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: 'rgba(225, 29, 72, 0.12)',
                  border: '1px solid rgba(225, 29, 72, 0.3)',
                  borderRadius: '6px',
                  padding: '2px 7px',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--accent-focal-hover)',
                  flexShrink: 0,
                }}
                title={`종합 평점: ${item.overall_score}점${item.iaa_score != null ? ` (미학 IAA: ${item.iaa_score}점)` : ''}`}
              >
                <span style={{ fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.04em' }}>SCORE</span>
                <span className="font-mono">{Math.round(item.overall_score)}</span>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '11px', color: '#a1a1aa' }}>
            {item.camera_model && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Camera size={12} color="var(--accent-focal)" />
                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {item.camera_model} {item.lens_model ? `• ${item.lens_model}` : ''}
                </span>
              </div>
            )}

            {(item.f_number || item.shutter_speed || item.iso) && (
              <div className="font-mono" style={{ display: 'flex', gap: '8px', color: '#71717a', whiteSpace: 'nowrap' }}>
                {item.f_number && <span>f/{item.f_number}</span>}
                {item.shutter_speed && <span>{item.shutter_speed}</span>}
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
  );
};
