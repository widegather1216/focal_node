import React from 'react';
import { Camera, Aperture, Clock, Sun, Focus } from 'lucide-react';
import { PhotoDetail } from '../../hooks/usePhotoDetail';
import { formatAperture, formatShutterSpeed, formatIso, formatFocalLength } from '../../utils/exif';

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
          {formatAperture(metadata.f_number)}
        </div>
      )}
      {metadata.focal_length && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
          <Focus size={14} />
          {formatFocalLength(metadata.focal_length, metadata.focal_length_35mm)}
        </div>
      )}
      {metadata.shutter_speed && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
          <Clock size={14} />
          {formatShutterSpeed(metadata.shutter_speed)}
        </div>
      )}
      {metadata.iso && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
          <Sun size={14} />
          {formatIso(metadata.iso)}
        </div>
      )}
    </div>
  );
};
