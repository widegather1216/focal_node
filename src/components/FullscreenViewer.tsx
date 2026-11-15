import React, { useRef, useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { usePhotoDetailQuery } from '../hooks/usePhotoDetailQuery';
import { useFullscreenControls } from '../hooks/useFullscreenControls';
import { FullscreenMetadataOverlay } from './fullscreen/FullscreenMetadataOverlay';
import { FullscreenToolbar } from './fullscreen/FullscreenToolbar';
import { FullscreenNavigation } from './fullscreen/FullscreenNavigation';
import { api } from '../services/api';

function getFitModeImageStyle(fitMode: 'fit-height' | 'contain' | 'cover'): React.CSSProperties {
  return {
    height: fitMode === 'fit-height' || fitMode === 'cover' ? '100vh' : 'auto',
    width: fitMode === 'cover' ? '100vw' : 'auto',
    maxHeight: fitMode === 'fit-height' ? '100vh' : fitMode === 'contain' ? '92vh' : 'none',
    maxWidth: fitMode === 'contain' ? '92vw' : 'none',
    objectFit: fitMode === 'cover' ? 'cover' : 'contain',
  };
}

export function FullscreenViewer() {
  const {
    isFullscreenOpen,
    fullscreenPhotoId,
    scale,
    setScale,
    showMetadata,
    setShowMetadata,
    imgError,
    setImgError,
    fitMode,
    setFitMode,
    isZenMode,
    closeFullscreen,
    handlePrevPhoto,
    handleNextPhoto,
    toggleZenMode,
  } = useFullscreenControls();

  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullLoaded, setIsFullLoaded] = useState(false);
  const { data: photo } = usePhotoDetailQuery(fullscreenPhotoId);

  useEffect(() => {
    setIsFullLoaded(false);
  }, [fullscreenPhotoId]);

  if (!isFullscreenOpen || !fullscreenPhotoId) return null;

  const thumbUrl = api.getPhotoThumbnailUrl(fullscreenPhotoId);
  const originalUrl = `${api.getPhotoOriginalUrl(fullscreenPhotoId)}?raw=true`;
  const imageUrl = imgError ? thumbUrl : originalUrl;
  const fitImageStyle = getFitModeImageStyle(fitMode);

  const handleWheel = (event: React.WheelEvent) => {
    if (event.ctrlKey || event.metaKey || scale > 1) {
      event.preventDefault();
      if (event.deltaY < 0) {
        setScale((prev) => Math.min(prev + 0.25, 4));
      } else {
        setScale((prev) => Math.max(prev - 0.25, 0.5));
      }
    }
  };

  return (
    <AnimatePresence>
      {isFullscreenOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.95)',
            zIndex: 100,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            userSelect: 'none',
          }}
        >
          <FullscreenToolbar
            fileName={photo?.file_name}
            isVisible={!isZenMode}
            scale={scale}
            fitMode={fitMode}
            showMetadata={showMetadata}
            onZoomOut={() => setScale((prev) => Math.max(prev - 0.5, 0.5))}
            onZoomIn={() => setScale((prev) => Math.min(prev + 0.5, 4))}
            onResetZoom={() => setScale(1)}
            onSelectFitMode={(mode) => setFitMode(mode)}
            onToggleZenMode={toggleZenMode}
            onToggleMetadata={() => setShowMetadata((prev) => !prev)}
            onClose={closeFullscreen}
          />

          <FullscreenNavigation
            isVisible={!isZenMode}
            onPrevPhoto={handlePrevPhoto}
            onNextPhoto={handleNextPhoto}
          />

          {/* Main Image Container */}
          <div
            ref={containerRef}
            onWheel={handleWheel}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
              cursor: isZenMode ? 'pointer' : scale > 1 ? 'grab' : 'default',
            }}
            onClick={toggleZenMode}
          >
            <motion.div
              key={fullscreenPhotoId}
              drag={scale > 1}
              dragConstraints={{
                left: -window.innerWidth * (scale - 0.8),
                right: window.innerWidth * (scale - 0.8),
                top: -window.innerHeight * (scale - 0.8),
                bottom: window.innerHeight * (scale - 0.8),
              }}
              dragMomentum={false}
              dragElastic={0}
              onPointerDown={(event) => {
                if (scale > 1) {
                  event.stopPropagation();
                }
              }}
              animate={{
                scale,
                x: scale === 1 ? 0 : undefined,
                y: scale === 1 ? 0 : undefined,
              }}
              transition={scale === 1 ? { type: 'spring', stiffness: 300, damping: 30 } : { duration: 0 }}
              style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                width: '100%',
                height: '100%',
                touchAction: 'none',
                position: 'relative',
              }}
            >
              {/* Thumbnail Placeholder while Full Res is loading */}
              {!isFullLoaded && !imgError && (
                <img
                  src={thumbUrl}
                  alt="미리보기"
                  style={{
                    ...fitImageStyle,
                    position: 'absolute',
                    filter: 'blur(8px)',
                    opacity: 0.8,
                    pointerEvents: 'none',
                  }}
                />
              )}

              {/* Full-resolution Image */}
              <img
                src={imageUrl}
                alt={photo?.file_name || '원본 사진'}
                draggable={false}
                onDragStart={(event) => event.preventDefault()}
                onLoad={() => setIsFullLoaded(true)}
                onError={() => {
                  setImgError(true);
                  setIsFullLoaded(true);
                }}
                onDoubleClick={() => setScale((prev) => (prev === 1 ? 2 : 1))}
                style={{
                  ...fitImageStyle,
                  display: 'block',
                  userSelect: 'none',
                  WebkitUserSelect: 'none',
                  boxShadow: '0 20px 50px rgba(0,0,0,0.8)',
                  position: 'relative',
                  zIndex: 2,
                }}
              />

              {/* Decoding RAW spinner badge */}
              {!isFullLoaded && !imgError && (
                <div
                  style={{
                    position: 'absolute',
                    bottom: '24px',
                    right: '24px',
                    background: 'rgba(0, 0, 0, 0.7)',
                    backdropFilter: 'blur(8px)',
                    padding: '6px 12px',
                    borderRadius: '20px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    color: '#e4e4e7',
                    fontSize: '12px',
                    zIndex: 10,
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                  }}
                >
                  <Loader2 size={13} className="spin" color="var(--accent-focal)" style={{ flexShrink: 0 }} />
                  <span style={{ whiteSpace: 'nowrap' }}>고해상도 디코딩 중...</span>
                </div>
              )}
            </motion.div>
          </div>

          {/* Bottom Floating Metadata Overlay */}
          <AnimatePresence>
            <FullscreenMetadataOverlay photo={photo} isVisible={!isZenMode && showMetadata} />
          </AnimatePresence>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
