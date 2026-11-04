import React from 'react';
import { Camera, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import { PhotoDetail } from '../../hooks/usePhotoDetail';

interface CritiqueDocumentPhotoViewerProps {
  photo: PhotoDetail | null | undefined;
  imageUrl: string;
  scale: number;
  position: { x: number; y: number };
  isDragging: boolean;
  onWheel: (e: React.WheelEvent) => void;
  onMouseDown: (e: React.MouseEvent) => void;
  onMouseMove: (e: React.MouseEvent) => void;
  onMouseUp: () => void;
  onResetZoom: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onImageError: () => void;
}

export const CritiqueDocumentPhotoViewer: React.FC<CritiqueDocumentPhotoViewerProps> = ({
  photo,
  imageUrl,
  scale,
  position,
  isDragging,
  onWheel,
  onMouseDown,
  onMouseMove,
  onMouseUp,
  onResetZoom,
  onZoomIn,
  onZoomOut,
  onImageError,
}) => {
  const meta = photo?.metadata;

  return (
    <div
      className="no-print"
      style={{
        flex: '0 0 46%',
        backgroundColor: '#060608',
        borderRight: '1px solid rgba(255, 255, 255, 0.08)',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        userSelect: 'none'
      }}
    >
      {/* Photo Canvas Container */}
      <div
        style={{
          flex: 1,
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          cursor: scale > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default'
        }}
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onDoubleClick={onResetZoom}
      >
        <img
          src={imageUrl}
          alt={photo?.file_name}
          onError={onImageError}
          draggable={false}
          style={{
            maxWidth: '92%',
            maxHeight: '92%',
            objectFit: 'contain',
            transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
            transformOrigin: 'center center',
            transition: isDragging ? 'none' : 'transform 0.15s ease-out',
            boxShadow: '0 10px 40px rgba(0, 0, 0, 0.6)'
          }}
        />

        {/* Floating Zoom Control Bar (Minimal Pill) */}
        <div
          style={{
            position: 'absolute',
            top: '16px',
            left: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: 'rgba(18, 18, 22, 0.65)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '20px',
            padding: '3px 8px',
            zIndex: 10
          }}
        >
          <button
            onClick={onZoomOut}
            style={{ background: 'none', border: 'none', color: '#a1a1aa', cursor: 'pointer', padding: '2px', display: 'flex' }}
            title="축소"
          >
            <ZoomOut size={13} />
          </button>
          <span className="font-mono" style={{ fontSize: '11px', color: '#f4f4f5', fontWeight: 600, minWidth: '36px', textAlign: 'center' }}>
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={onZoomIn}
            style={{ background: 'none', border: 'none', color: '#a1a1aa', cursor: 'pointer', padding: '2px', display: 'flex' }}
            title="확대"
          >
            <ZoomIn size={13} />
          </button>
          {scale !== 1 && (
            <button
              onClick={onResetZoom}
              style={{ background: 'none', border: 'none', color: 'var(--accent-focal-hover)', cursor: 'pointer', padding: '2px', display: 'flex', marginLeft: '2px' }}
              title="줌 리셋"
            >
              <RotateCcw size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Bottom EXIF HUD Overlay (Leica Monospace HUD) */}
      <div
        style={{
          padding: '10px 18px',
          backgroundColor: 'rgba(12, 12, 15, 0.95)',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          fontSize: '11.5px',
          color: '#a1a1aa'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0, overflow: 'hidden' }}>
          <Camera size={13} color="var(--accent-focal)" style={{ flexShrink: 0 }} />
          <span style={{ color: '#e4e4e7', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {meta?.camera_model || '카메라'}
          </span>
          {meta?.lens_model && (
            <span style={{ color: '#71717a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              · {meta.lens_model}
            </span>
          )}
        </div>

        <div
          className="font-mono"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            color: '#f4f4f5',
            fontSize: '11px',
            whiteSpace: 'nowrap',
            flexShrink: 0
          }}
        >
          {meta?.focal_length && <span>{meta.focal_length}mm</span>}
          {meta?.focal_length && (meta?.f_number || meta?.shutter_speed || meta?.iso) && (
            <span style={{ color: 'rgba(255, 255, 255, 0.2)' }}>·</span>
          )}
          {meta?.f_number && <span>f/{meta.f_number}</span>}
          {meta?.f_number && (meta?.shutter_speed || meta?.iso) && (
            <span style={{ color: 'rgba(255, 255, 255, 0.2)' }}>·</span>
          )}
          {meta?.shutter_speed && <span>{meta.shutter_speed}s</span>}
          {meta?.shutter_speed && meta?.iso && (
            <span style={{ color: 'rgba(255, 255, 255, 0.2)' }}>·</span>
          )}
          {meta?.iso && <span>ISO {meta.iso}</span>}
        </div>
      </div>
    </div>
  );
};
