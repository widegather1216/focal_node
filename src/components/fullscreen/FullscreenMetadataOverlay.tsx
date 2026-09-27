import React from 'react';
import { motion } from 'framer-motion';
import { Camera, Focus, Aperture, Clock, Zap } from 'lucide-react';

interface FullscreenMetadataOverlayProps {
  photo: any;
  isVisible: boolean;
}

export const FullscreenMetadataOverlay: React.FC<FullscreenMetadataOverlayProps> = ({ photo, isVisible }) => {
  if (!isVisible || !photo || !photo.metadata) return null;

  return (
    <motion.div
      initial={{ y: 50, opacity: 0, x: '-50%' }}
      animate={{ y: 0, opacity: 1, x: '-50%' }}
      exit={{ y: 50, opacity: 0, x: '-50%' }}
      transition={{ duration: 0.18 }}
      style={{
        position: 'absolute',
        bottom: '24px',
        left: '50%',
        backgroundColor: 'rgba(18, 18, 21, 0.88)',
        backdropFilter: 'blur(16px)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '8px',
        padding: '10px 18px',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        boxShadow: '0 16px 36px rgba(0,0,0,0.7)',
        maxWidth: '92%',
        zIndex: 110,
        userSelect: 'none'
      }}
    >
      {/* Camera */}
      {photo.metadata.camera_model && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-primary)' }}>
          <Camera size={13} color="var(--text-muted)" />
          <span style={{ fontWeight: 600 }}>{photo.metadata.camera_model}</span>
        </div>
      )}

      {/* Lens */}
      {photo.metadata.lens_model && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-primary)' }}>
          <Focus size={13} color="var(--text-muted)" />
          <span style={{ fontWeight: 500 }}>{photo.metadata.lens_model}</span>
        </div>
      )}

      {/* Divider */}
      <div style={{ width: '1px', height: '14px', backgroundColor: 'var(--border-subtle)' }} />

      {/* Hardware EXIF HUD (Monospace Numbers) */}
      <div className="font-mono" style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '12px', color: 'var(--text-secondary)' }}>
        {/* Focal length */}
        {photo.metadata.focal_length && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span>{Math.round(photo.metadata.focal_length)}mm</span>
            {photo.metadata.focal_length_35mm && photo.metadata.focal_length_35mm !== photo.metadata.focal_length && (
              <span style={{ color: 'var(--text-muted)', fontSize: '10px' }}>
                ({Math.round(photo.metadata.focal_length_35mm)}mm eq)
              </span>
            )}
          </div>
        )}

        {/* Aperture */}
        {photo.metadata.f_number && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Aperture size={12} color="var(--text-muted)" />
            <span>ƒ/{photo.metadata.f_number}</span>
          </div>
        )}

        {/* Shutter */}
        {photo.metadata.shutter_speed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={12} color="var(--text-muted)" />
            <span>{photo.metadata.shutter_speed}</span>
          </div>
        )}

        {/* ISO */}
        {photo.metadata.iso && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Zap size={12} color="var(--text-muted)" />
            <span>ISO {photo.metadata.iso}</span>
          </div>
        )}
      </div>
    </motion.div>
  );
};
