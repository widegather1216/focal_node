import React from 'react';
import { Camera, Aperture, Clock, Sun, Focus } from 'lucide-react';
import { PhotoDetail } from '../../hooks/usePhotoDetail';
import { formatAperture, formatShutterSpeed, formatIso, formatFocalLength } from '../../utils/exif';

export const PhotoExifView: React.FC<{ metadata: PhotoDetail['metadata'] }> = ({ metadata }) => {
  if (!metadata) return null;

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
      {metadata.camera_model && (
        <div style={chipStyle} title={metadata.camera_model}>
          <Camera size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
          <span style={textTruncateStyle}>{metadata.camera_model}</span>
        </div>
      )}
      {metadata.lens_model && (
        <div style={chipStyle} title={metadata.lens_model}>
          <Focus size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
          <span style={textTruncateStyle}>{metadata.lens_model}</span>
        </div>
      )}
      {metadata.sensor_format && (
        <div style={{ ...chipStyle, borderColor: 'var(--border-active)' }}>
          <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
            {metadata.sensor_format}
          </span>
        </div>
      )}
      {metadata.f_number && (
        <div className="font-mono" style={chipStyle}>
          <Aperture size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
          <span style={{ color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{formatAperture(metadata.f_number)}</span>
        </div>
      )}
      {metadata.focal_length && (
        <div className="font-mono" style={chipStyle}>
          <Focus size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
          <span style={{ color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
            {formatFocalLength(metadata.focal_length, metadata.focal_length_35mm)}
          </span>
        </div>
      )}
      {metadata.shutter_speed && (
        <div className="font-mono" style={chipStyle}>
          <Clock size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
          <span style={{ color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{formatShutterSpeed(metadata.shutter_speed)}</span>
        </div>
      )}
      {metadata.iso && (
        <div className="font-mono" style={chipStyle}>
          <Sun size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
          <span style={{ color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{formatIso(metadata.iso)}</span>
        </div>
      )}
    </div>
  );
};

const chipStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  backgroundColor: 'var(--bg-card)',
  border: '1px solid var(--border-subtle)',
  padding: '5px 10px',
  borderRadius: '4px',
  fontSize: '11px',
  color: 'var(--text-secondary)',
  letterSpacing: '-0.01em',
  whiteSpace: 'nowrap' as const,
  flexShrink: 0
};

const textTruncateStyle = {
  fontWeight: 500,
  color: 'var(--text-primary)',
  whiteSpace: 'nowrap' as const,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  maxWidth: '240px'
};
