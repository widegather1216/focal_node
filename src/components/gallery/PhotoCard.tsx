import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, Heart } from 'lucide-react';
import { api } from '../../services/api';
import { Photo } from '../../types/photo';

interface PhotoCardProps {
  photo: Photo;
  isSelected: boolean;
  onSelectPhoto: (id: string) => void;
  onToggleSelection: (id: string) => void;
  onToggleFavorite: (id: string, e: React.MouseEvent) => void;
}

const FALLBACK_SVG = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"><rect width="100%" height="100%" fill="%232a2a2a"/><text x="50%" y="50%" font-family="sans-serif" font-size="8" fill="%23666" text-anchor="middle" dy=".3em">File Missing</text></svg>';

export const PhotoCard = memo<PhotoCardProps>(({
  photo,
  isSelected,
  onSelectPhoto,
  onToggleSelection,
  onToggleFavorite
}) => {
  return (
    <motion.div 
      onClick={() => onSelectPhoto(photo.id)}
      whileHover={{ scale: 1.02, transition: { duration: 0.2 } }}
      style={{
        flex: 1,
        minWidth: 0,
        backgroundColor: '#222',
        borderRadius: '8px',
        overflow: 'hidden',
        cursor: 'pointer',
        position: 'relative',
        border: isSelected ? '2px solid #4CAF50' : '2px solid transparent',
        boxSizing: 'border-box'
      }}
    >
      <motion.div 
        onClick={(e) => {
          e.stopPropagation();
          onToggleSelection(photo.id);
        }}
        whileHover={{ scale: 1.1, opacity: 1 }}
        whileTap={{ scale: 0.9 }}
        transition={{ type: "spring", stiffness: 400, damping: 15 }}
        style={{
          position: 'absolute',
          top: '8px',
          left: '8px',
          zIndex: 2,
          color: isSelected ? '#4CAF50' : '#fff',
          opacity: isSelected ? 1 : 0.6,
          cursor: 'pointer',
          background: isSelected ? '#fff' : 'rgba(0,0,0,0.5)',
          borderRadius: '50%',
          display: 'flex',
          padding: '2px',
        }}
      >
        <CheckCircle2 size={20} fill={isSelected ? '#4CAF50' : 'none'} color={isSelected ? '#fff' : '#fff'} />
      </motion.div>

      <motion.div 
        onClick={(e) => onToggleFavorite(photo.id, e)}
        whileHover={{ scale: 1.15, opacity: 1 }}
        whileTap={{ scale: 0.9 }}
        transition={{ type: "spring", stiffness: 400, damping: 12 }}
        style={{
          position: 'absolute',
          top: '8px',
          right: '8px',
          zIndex: 2,
          color: photo.is_favorite ? '#ef4444' : '#fff',
          opacity: photo.is_favorite ? 1 : 0.6,
          cursor: 'pointer',
          display: 'flex',
          padding: '4px',
          filter: 'drop-shadow(0px 2px 4px rgba(0,0,0,0.5))'
        }}
      >
        <Heart size={20} fill={photo.is_favorite ? '#ef4444' : 'rgba(0,0,0,0.3)'} color={photo.is_favorite ? '#ef4444' : '#fff'} />
      </motion.div>

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
          backgroundColor: '#2a2a2a'
        }}
        onError={(e) => {
          if (e.currentTarget.getAttribute('data-has-failed')) return;
          e.currentTarget.setAttribute('data-has-failed', 'true');
          e.currentTarget.src = FALLBACK_SVG;
        }}
      />

      <div 
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          padding: '24px 12px 12px',
          background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0) 100%)',
          color: '#fff',
          fontSize: '12px',
          opacity: 0,
          transition: 'opacity 0.2s'
        }}
        onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
        onMouseLeave={(e) => e.currentTarget.style.opacity = '0'}
      >
        <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {photo.file_name}
        </div>
        {photo.metadata?.capture_date && (
          <div style={{ color: '#aaa', marginTop: '2px' }}>
            {new Date(photo.metadata.capture_date).toLocaleDateString()}
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
