import React, { memo, useState } from 'react';
import { motion } from 'framer-motion';
import { Check, Heart } from 'lucide-react';
import { api } from '../../services/api';
import { Photo } from '../../types/photo';

interface PhotoCardProps {
  photo: Photo;
  isSelected: boolean;
  onSelectPhoto: (id: string) => void;
  onToggleSelection: (id: string) => void;
  onToggleFavorite: (id: string, e: React.MouseEvent) => void;
}

const FALLBACK_SVG = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><rect width="100%" height="100%" fill="%2318181b"/><text x="50%" y="50%" font-family="sans-serif" font-size="8" fill="%2371717a" text-anchor="middle" dy=".3em">File Missing</text></svg>';

const RAW_EXTENSIONS = new Set(['arw', 'cr2', 'cr3', 'nef', 'dng', 'raf', 'orf', 'rw2', 'pef']);

export const PhotoCard = memo<PhotoCardProps>(({
  photo,
  isSelected,
  onSelectPhoto,
  onToggleSelection,
  onToggleFavorite
}) => {
  const [isHovered, setIsHovered] = useState(false);

  const fileExt = photo.file_name.split('.').pop()?.toLowerCase() || '';
  const isRaw = RAW_EXTENSIONS.has(fileExt);

  // Format EXIF summary line
  const meta = photo.metadata;
  const exifBadges: string[] = [];
  if (meta?.f_number) exifBadges.push(`ƒ/${meta.f_number}`);
  if (meta?.exposure_time) exifBadges.push(meta.exposure_time);
  if (meta?.iso) exifBadges.push(`ISO ${meta.iso}`);
  if (meta?.focal_length_in_35mm || meta?.focal_length) {
    const fl = meta.focal_length_in_35mm || meta.focal_length;
    exifBadges.push(`${Math.round(fl!)}mm`);
  }

  return (
    <motion.div 
      onClick={() => onSelectPhoto(photo.id)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      whileHover={{ scale: 1.015, transition: { duration: 0.15 } }}
      style={{
        flex: 1,
        minWidth: 0,
        backgroundColor: 'var(--bg-card)',
        borderRadius: '6px',
        overflow: 'hidden',
        cursor: 'pointer',
        position: 'relative',
        border: isSelected 
          ? '2px solid var(--accent-focal)' 
          : '1px solid var(--border-subtle)',
        boxSizing: 'border-box',
        boxShadow: isSelected ? '0 0 16px rgba(225, 29, 72, 0.4)' : 'none',
        transition: 'border-color 0.15s ease, box-shadow 0.15s ease'
      }}
    >
      {/* Selection Checkbox Trigger */}
      <motion.div 
        onClick={(e) => {
          e.stopPropagation();
          onToggleSelection(photo.id);
        }}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        transition={{ type: "spring", stiffness: 400, damping: 15 }}
        style={{
          position: 'absolute',
          top: '6px',
          left: '6px',
          zIndex: 3,
          color: '#fff',
          opacity: isSelected ? 1 : isHovered ? 0.75 : 0,
          cursor: 'pointer',
          background: isSelected ? 'var(--accent-focal)' : 'rgba(0, 0, 0, 0.55)',
          borderRadius: '4px',
          border: isSelected ? '1px solid var(--accent-focal)' : '1px solid rgba(255, 255, 255, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '20px',
          height: '20px',
          transition: 'opacity 0.15s ease, background 0.15s ease'
        }}
        title={isSelected ? "선택 해제" : "선택"}
      >
        {isSelected && <Check size={13} strokeWidth={3} />}
      </motion.div>

      {/* Favorite Heart Trigger */}
      <motion.div 
        onClick={(e) => onToggleFavorite(photo.id, e)}
        whileHover={{ scale: 1.15 }}
        whileTap={{ scale: 0.9 }}
        transition={{ type: "spring", stiffness: 400, damping: 12 }}
        style={{
          position: 'absolute',
          top: '6px',
          right: '6px',
          zIndex: 3,
          color: photo.is_favorite ? 'var(--accent-focal)' : '#fff',
          opacity: photo.is_favorite ? 1 : isHovered ? 0.8 : 0,
          cursor: 'pointer',
          display: 'flex',
          padding: '4px',
          filter: 'drop-shadow(0px 2px 4px rgba(0,0,0,0.7))',
          transition: 'opacity 0.15s ease'
        }}
        title="즐겨찾기 토글"
      >
        <Heart 
          size={16} 
          fill={photo.is_favorite ? 'var(--accent-focal)' : 'none'} 
          color={photo.is_favorite ? 'var(--accent-focal)' : '#fff'} 
        />
      </motion.div>

      {/* Image Element */}
      <img 
        src={api.getPhotoThumbnailUrl(photo.id)}
        alt={photo.file_name}
        decoding="async"
        loading="lazy"
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          display: 'block',
          backgroundColor: 'var(--bg-canvas)'
        }}
        onError={(e) => {
          if (e.currentTarget.getAttribute('data-has-failed')) return;
          e.currentTarget.setAttribute('data-has-failed', 'true');
          e.currentTarget.src = FALLBACK_SVG;
        }}
      />

      {/* Progressive Disclosure Overlay (Gradient + Monospace EXIF HUD) */}
      <div 
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          padding: '24px 10px 8px 10px',
          background: 'linear-gradient(to top, rgba(9, 9, 11, 0.92) 0%, rgba(9, 9, 11, 0.6) 60%, transparent 100%)',
          color: 'var(--text-primary)',
          opacity: isHovered || isSelected ? 1 : 0,
          pointerEvents: isHovered ? 'auto' : 'none',
          transition: 'opacity 0.18s ease-out',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}
      >
        {/* Filename and RAW Tag */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          {isRaw && (
            <span className="badge-raw">RAW</span>
          )}
          <span style={{
            fontSize: '11px',
            fontWeight: 500,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            color: 'var(--text-primary)'
          }}>
            {photo.file_name}
          </span>
        </div>

        {/* Monospace EXIF Mini-HUD */}
        {exifBadges.length > 0 && (
          <div className="font-mono" style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '10px',
            color: 'var(--text-secondary)',
            letterSpacing: '-0.02em',
            overflow: 'hidden',
            whiteSpace: 'nowrap'
          }}>
            {exifBadges.map((badge, idx) => (
              <React.Fragment key={idx}>
                {idx > 0 && <span style={{ color: 'var(--text-muted)' }}>·</span>}
                <span>{badge}</span>
              </React.Fragment>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}, (prev, next) => (
  prev.photo.id === next.photo.id &&
  prev.photo.is_favorite === next.photo.is_favorite &&
  prev.isSelected === next.isSelected
));
