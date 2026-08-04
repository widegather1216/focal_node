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
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: 50, opacity: 0 }}
      transition={{ duration: 0.2 }}
      style={{
        position: 'absolute',
        bottom: '24px',
        left: '50%',
        transform: 'translateX(-50%)',
        background: 'rgba(24, 24, 27, 0.85)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(63, 63, 70, 0.5)',
        borderRadius: '12px',
        padding: '14px 20px',
        display: 'flex',
        alignItems: 'center',
        gap: '20px',
        boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
        maxWidth: '90%',
        zIndex: 110
      }}
    >
      {/* Camera */}
      {photo.metadata.camera_model && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#f4f4f5' }}>
          <Camera size={15} color="#38bdf8" />
          <span style={{ fontWeight: 600 }}>{photo.metadata.camera_model}</span>
        </div>
      )}

      {/* Lens */}
      {photo.metadata.lens_model && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#f4f4f5' }}>
          <Focus size={15} color="#c084fc" />
          <span style={{ fontWeight: 600 }}>{photo.metadata.lens_model}</span>
        </div>
      )}

      {/* Focal length */}
      {photo.metadata.focal_length && (
        <div style={{ fontSize: '13px', color: '#a1a1aa', fontWeight: 500 }}>
          <span>{photo.metadata.focal_length}mm</span>
          {photo.metadata.focal_length_35mm && photo.metadata.focal_length_35mm !== photo.metadata.focal_length && (
            <span style={{ color: '#71717a', marginLeft: '4px', fontSize: '11px' }}>
              ({photo.metadata.focal_length_35mm}mm 환산)
            </span>
          )}
        </div>
      )}

      {/* Aperture */}
      {photo.metadata.f_number && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#4ade80', fontWeight: 600 }}>
          <Aperture size={15} />
          <span>f/{photo.metadata.f_number}</span>
        </div>
      )}

      {/* Shutter */}
      {photo.metadata.shutter_speed && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#facc15', fontWeight: 600 }}>
          <Clock size={15} />
          <span>{photo.metadata.shutter_speed}s</span>
        </div>
      )}

      {/* ISO */}
      {photo.metadata.iso && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#fb923c', fontWeight: 600 }}>
          <Zap size={15} />
          <span>ISO {photo.metadata.iso}</span>
        </div>
      )}
    </motion.div>
  );
};
