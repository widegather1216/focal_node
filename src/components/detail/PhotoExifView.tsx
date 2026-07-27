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
      {metadata.sensor_format && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '6px 12px', borderRadius: '4px', fontSize: '12px', fontWeight: 600 }}>
          <Camera size={14} />
          {metadata.sensor_format}
        </div>
      )}
      {metadata.f_number && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
          <Aperture size={14} />
          f/{typeof metadata.f_number === 'number' ? Math.round(metadata.f_number * 100) / 100 : metadata.f_number}
        </div>
      )}
      {metadata.focal_length && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
          <Focus size={14} />
          {metadata.focal_length}mm
          {metadata.focal_length_35mm && metadata.focal_length_35mm !== metadata.focal_length && (
            <span style={{ color: '#aaa', fontSize: '11px', marginLeft: '2px' }}>
              (35mm 환산 {metadata.focal_length_35mm}mm)
            </span>
          )}
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
