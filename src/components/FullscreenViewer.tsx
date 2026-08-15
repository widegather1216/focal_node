import { useRef, useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ZoomOut, ZoomIn, RotateCcw, Eye, Info, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { usePhotoDetailQuery } from '../hooks/usePhotoDetailQuery';
import { useFullscreenControls } from '../hooks/useFullscreenControls';
import { FullscreenMetadataOverlay } from './fullscreen/FullscreenMetadataOverlay';
import { api } from '../services/api';

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
    toggleZenMode
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

  const handleWheel = (e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey || scale > 1) {
      e.preventDefault();
      if (e.deltaY < 0) {
        setScale(prev => Math.min(prev + 0.25, 4));
      } else {
        setScale(prev => Math.max(prev - 0.25, 0.5));
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
            userSelect: 'none'
          }}
        >
          {/* Top Floating Control Bar */}
          <AnimatePresence>
            {!isZenMode && (
              <motion.div
                initial={{ y: -50, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -50, opacity: 0 }}
                transition={{ duration: 0.2 }}
                style={{
                  position: 'absolute',
                  top: '20px',
                  left: '20px',
                  right: '20px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  zIndex: 120,
                  pointerEvents: 'none'
                }}
              >
                {/* File Title */}
                <div className="glass-panel" style={{
                  padding: '8px 16px',
                  borderRadius: '10px',
                  color: '#fff',
                  fontSize: '14px',
                  fontWeight: 500,
                  maxWidth: '300px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  pointerEvents: 'auto'
                }}>
                  {photo?.file_name || '사진 뷰어'}
                </div>

                {/* Toolbar Buttons */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', pointerEvents: 'auto' }}>
                  {/* Zoom Controls */}
                  <div className="glass-panel" style={{
                    display: 'flex',
                    alignItems: 'center',
                    borderRadius: '10px',
                    padding: '4px'
                  }}>
                    <button
                      onClick={() => setScale(prev => Math.max(prev - 0.5, 0.5))}
                      style={{ background: 'none', border: 'none', color: '#a1a1aa', padding: '6px', cursor: 'pointer', display: 'flex' }}
                      title="축소 (-)"
                    >
                      <ZoomOut size={16} />
                    </button>
                    <span style={{ color: '#fff', fontSize: '12px', minWidth: '45px', textAlign: 'center', fontWeight: 600 }}>
                      {Math.round(scale * 100)}%
                    </span>
                    <button
                      onClick={() => setScale(prev => Math.min(prev + 0.5, 4))}
                      style={{ background: 'none', border: 'none', color: '#a1a1aa', padding: '6px', cursor: 'pointer', display: 'flex' }}
                      title="확대 (+)"
                    >
                      <ZoomIn size={16} />
                    </button>
                    <button
                      onClick={() => setScale(1)}
                      style={{ background: 'none', border: 'none', color: scale !== 1 ? '#38bdf8' : '#71717a', padding: '6px', cursor: 'pointer', display: 'flex' }}
                      title="100% 원본 비율 (0)"
                    >
                      <RotateCcw size={15} />
                    </button>
                  </div>

                  {/* Fit Mode Switcher */}
                  <div className="glass-panel" style={{
                    display: 'flex',
                    alignItems: 'center',
                    borderRadius: '10px',
                    padding: '4px'
                  }}>
                    <button
                      onClick={() => setFitMode('fit-height')}
                      style={{
                        background: fitMode === 'fit-height' ? '#3f3f46' : 'none',
                        border: 'none', color: fitMode === 'fit-height' ? '#fff' : '#a1a1aa',
                        padding: '6px 10px', borderRadius: '6px', fontSize: '12px', cursor: 'pointer', fontWeight: 500
                      }}
                      title="높이 맞춤"
                    >
                      높이 맞춤
                    </button>
                    <button
                      onClick={() => setFitMode('contain')}
                      style={{
                        background: fitMode === 'contain' ? '#3f3f46' : 'none',
                        border: 'none', color: fitMode === 'contain' ? '#fff' : '#a1a1aa',
                        padding: '6px 10px', borderRadius: '6px', fontSize: '12px', cursor: 'pointer', fontWeight: 500
                      }}
                      title="전체 맞춤"
                    >
                      전체 맞춤
                    </button>
                  </div>

                  {/* Zen Mode Button */}
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={toggleZenMode}
                    className="glass-button"
                    style={{
                      padding: '8px 12px',
                      fontSize: '13px',
                      fontWeight: 500
                    }}
                    title="몰입 모드 (F)"
                  >
                    <Eye size={16} /> Zen Mode
                  </motion.button>

                  {/* EXIF Info Toggle */}
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setShowMetadata(prev => !prev)}
                    className="glass-button"
                    style={{
                      borderColor: showMetadata ? '#38bdf8' : undefined,
                      color: showMetadata ? '#38bdf8' : undefined,
                      padding: '8px 12px',
                      fontSize: '13px',
                      fontWeight: 500
                    }}
                    title="메타데이터 오버레이 토글 (I)"
                  >
                    <Info size={16} /> EXIF 오버레이
                  </motion.button>

                  {/* Close Button */}
                  <motion.button
                    whileHover={{ scale: 1.1, backgroundColor: '#ef4444', color: '#fff' }}
                    whileTap={{ scale: 0.9 }}
                    onClick={closeFullscreen}
                    style={{
                      background: '#27272a', border: 'none', color: '#f4f4f5',
                      borderRadius: '50%', padding: '8px', cursor: 'pointer', display: 'flex', marginLeft: '8px',
                      transition: 'all 0.15s ease'
                    }}
                    title="닫기 (Esc)"
                  >
                    <X size={20} />
                  </motion.button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Floating Navigation Arrows */}
          <AnimatePresence>
            {!isZenMode && (
              <>
                <motion.button
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 0.8, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  whileHover={{ scale: 1.15, opacity: 1, backgroundColor: 'rgba(24, 24, 27, 0.95)' }}
                  whileTap={{ scale: 0.9 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    handlePrevPhoto();
                  }}
                  style={{
                    position: 'absolute',
                    left: '24px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'rgba(24, 24, 27, 0.6)',
                    backdropFilter: 'blur(8px)',
                    border: '1px solid rgba(63, 63, 70, 0.6)',
                    color: '#fff',
                    borderRadius: '50%',
                    padding: '14px',
                    cursor: 'pointer',
                    zIndex: 130,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 8px 25px rgba(0,0,0,0.5)',
                    transition: 'opacity 0.2s, background-color 0.2s'
                  }}
                  title="이전 사진 (←)"
                >
                  <ChevronLeft size={24} />
                </motion.button>

                <motion.button
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 0.8, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  whileHover={{ scale: 1.15, opacity: 1, backgroundColor: 'rgba(24, 24, 27, 0.95)' }}
                  whileTap={{ scale: 0.9 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleNextPhoto();
                  }}
                  style={{
                    position: 'absolute',
                    right: '24px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'rgba(24, 24, 27, 0.6)',
                    backdropFilter: 'blur(8px)',
                    border: '1px solid rgba(63, 63, 70, 0.6)',
                    color: '#fff',
                    borderRadius: '50%',
                    padding: '14px',
                    cursor: 'pointer',
                    zIndex: 130,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 8px 25px rgba(0,0,0,0.5)',
                    transition: 'opacity 0.2s, background-color 0.2s'
                  }}
                  title="다음 사진 (→)"
                >
                  <ChevronRight size={24} />
                </motion.button>
              </>
            )}
          </AnimatePresence>

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
              cursor: isZenMode ? 'pointer' : (scale > 1 ? 'grab' : 'default')
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
                bottom: window.innerHeight * (scale - 0.8)
              }}
              dragMomentum={false}
              dragElastic={0}
              onPointerDown={(e) => {
                if (scale > 1) {
                  e.stopPropagation();
                }
              }}
              animate={{
                scale,
                x: scale === 1 ? 0 : undefined,
                y: scale === 1 ? 0 : undefined
              }}
              transition={scale === 1 ? { type: 'spring', stiffness: 300, damping: 30 } : { duration: 0 }}
              style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '100%', height: '100%', touchAction: 'none', position: 'relative' }}
            >
              {/* Thumbnail Placeholder while Full Res is loading */}
              {!isFullLoaded && !imgError && (
                <img
                  src={thumbUrl}
                  alt="미리보기"
                  style={{
                    position: 'absolute',
                    height: fitMode === 'fit-height' ? '100vh' : fitMode === 'cover' ? '100vh' : 'auto',
                    width: fitMode === 'cover' ? '100vw' : 'auto',
                    maxHeight: fitMode === 'fit-height' ? '100vh' : fitMode === 'contain' ? '92vh' : 'none',
                    maxWidth: fitMode === 'contain' ? '92vw' : 'none',
                    objectFit: fitMode === 'cover' ? 'cover' : 'contain',
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
                onDragStart={(e) => e.preventDefault()}
                onLoad={() => setIsFullLoaded(true)}
                onError={() => {
                  setImgError(true);
                  setIsFullLoaded(true);
                }}
                onDoubleClick={() => setScale(prev => (prev === 1 ? 2 : 1))}
                style={{
                  height: fitMode === 'fit-height' ? '100vh' : fitMode === 'cover' ? '100vh' : 'auto',
                  width: fitMode === 'cover' ? '100vw' : 'auto',
                  maxHeight: fitMode === 'fit-height' ? '100vh' : fitMode === 'contain' ? '92vh' : 'none',
                  maxWidth: fitMode === 'contain' ? '92vw' : 'none',
                  objectFit: fitMode === 'cover' ? 'cover' : 'contain',
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
                <div style={{
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
                }}>
                  <Loader2 size={13} className="spin" color="#38bdf8" />
                  <span>원본 고해상도 디코딩 중...</span>
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
