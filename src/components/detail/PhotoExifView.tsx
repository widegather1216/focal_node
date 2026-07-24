import React from 'react';
import { Camera, Aperture, Clock, Sun, Focus } from 'lucide-react';
import { PhotoDetail } from '../../hooks/usePhotoDetail';

export const PhotoExifView: React.FC<{ metadata: PhotoDetail['metadata'] }> = ({ metadata }) => {
  if (!metadata) return null;

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
      {metadata.camera_model && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
          <Camera size={14} />
          {metadata.camera_model}
        </div>
      )}
      {metadata.lens_model && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
          <Focus size={14} />
          {metadata.lens_model}
        </div>
      )}
      {metadata.f_number && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
          <Aperture size={14} />
          f/{metadata.f_number}
        </div>
      )}
      {metadata.focal_length && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
          {metadata.focal_length}mm
        </div>
      )}
      {metadata.shutter_speed && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
          <Clock size={14} />
          {metadata.shutter_speed}s
        </div>
      )}
      {metadata.iso && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
          <Sun size={14} />
          ISO {metadata.iso}
        </div>
      )}
    </div>
  );
};
