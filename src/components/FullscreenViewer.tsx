import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ZoomIn, ZoomOut, RotateCcw, Info, Camera, Focus, Aperture, Clock, Zap, Maximize, Expand, Eye, ChevronLeft, ChevronRight } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';
import { usePhotoDetailQuery } from '../hooks/usePhotoDetailQuery';

export function FullscreenViewer() {
  const { isFullscreenOpen, fullscreenPhotoId, openFullscreen, setSelectedPhotoId, closeFullscreen } = useAppStore();
  const [scale, setScale] = useState(1);
  const [showMetadata, setShowMetadata] = useState(true);
  const [imgError, setImgError] = useState(false);
  const [fitMode, setFitMode] = useState<'fit-height' | 'contain' | 'cover'>('fit-height');
  const [isZenMode, setIsZenMode] = useState(false);
  const [showZenHint, setShowZenHint] = useState(false);
  const zenHintTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const queryClient = useQueryClient();

  // Fetch full details of the active photo
  const { data: photo } = usePhotoDetailQuery(fullscreenPhotoId);

  // Helper to retrieve loaded photo list from react-query cache
  const getActivePhotoList = (): any[] => {
    const queryCache = queryClient.getQueriesData<any>({ queryKey: ['photos'] });
    for (const [, data] of queryCache) {
      if (data && data.pages) {
        return data.pages.flatMap((page: any) => page);
      }
    }
    return [];
  };

  const handlePrevPhoto = () => {
    const photos = getActivePhotoList();
    if (!photos.length || !fullscreenPhotoId) return;
    const currentIndex = photos.findIndex((p: any) => p.id === fullscreenPhotoId);
    if (currentIndex > 0) {
      const prevPhoto = photos[currentIndex - 1];
      openFullscreen(prevPhoto.id);
      setSelectedPhotoId(prevPhoto.id);
    }
  };

  const handleNextPhoto = () => {
    const photos = getActivePhotoList();
    if (!photos.length || !fullscreenPhotoId) return;
    const currentIndex = photos.findIndex((p: any) => p.id === fullscreenPhotoId);
    if (currentIndex !== -1 && currentIndex < photos.length - 1) {
      const nextPhoto = photos[currentIndex + 1];
      openFullscreen(nextPhoto.id);
      setSelectedPhotoId(nextPhoto.id);
    }
  };

  // Reset zoom & Zen mode on photo change or view open
  useEffect(() => {
    setScale(1);
    setImgError(false);
    setIsZenMode(false);
    setShowZenHint(false);
  }, [fullscreenPhotoId, isFullscreenOpen]);

  // Toggle Zen Mode helper
  const toggleZenMode = () => {
    setIsZenMode(prev => {
      const nextState = !prev;
      if (nextState) {
        setShowZenHint(true);
        if (zenHintTimerRef.current) clearTimeout(zenHintTimerRef.current);
        zenHintTimerRef.current = setTimeout(() => {
          setShowZenHint(false);
        }, 2500);
      } else {
        setShowZenHint(false);
      }
      return nextState;
    });
  };

  // Keyboard shortcut handlers
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isFullscreenOpen) return;

      // Ignore shortcut keys if typing in input or textarea elements
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
        return;
      }

      const key = e.key;
      const code = e.code;

      if (key === 'Escape') {
        if (isZenMode) {
          setIsZenMode(false);
        } else {
          closeFullscreen();
        }
      } else if (key === 'ArrowLeft') {
        handlePrevPhoto();
      } else if (key === 'ArrowRight') {
        handleNextPhoto();
      } else if (key === '+' || key === '=' || code === 'Equal' || code === 'NumpadAdd') {
        setScale(prev => Math.min(prev + 0.5, 4));
      } else if (key === '-' || code === 'Minus' || code === 'NumpadSubtract') {
        setScale(prev => Math.max(prev - 0.5, 0.5));
      } else if (key === '0' || code === 'Digit0' || code === 'Numpad0') {
        setScale(1);
      } else if (code === 'KeyI' || key === 'i' || key === 'I' || key === 'ㅑ') {
        setShowMetadata(prev => !prev);
      } else if (code === 'KeyF' || code === 'KeyH' || key === 'f' || key === 'F' || key === 'h' || key === 'H' || key === 'ㅁ' || key === 'ㅗ') {
        e.preventDefault();
        e.stopPropagation();
        toggleZenMode();
      }
    };

    window.addEventListener('keydown', handleKeyDown, true);
    return () => window.removeEventListener('keydown', handleKeyDown, true);
  }, [isFullscreenOpen, closeFullscreen, isZenMode, fullscreenPhotoId]);

  // Trackpad pinch-to-zoom & wheel zoom handler
  useEffect(() => {
    if (!isFullscreenOpen) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      // Trackpad pinch gesture emits wheel event with e.ctrlKey === true
      if (e.ctrlKey) {
        const delta = -e.deltaY * 0.015;
        setScale(prev => Math.min(Math.max(prev + delta, 0.8), 4));
      } else {
        // Standard wheel scroll zoom
        const delta = -e.deltaY * 0.002;
        setScale(prev => Math.min(Math.max(prev + delta, 0.8), 4));
      }
    };

    // WebKit Safari gesture events for macOS Trackpad pinch
    let initialScale = 1;
    const handleGestureStart = (e: any) => {
      e.preventDefault();
      initialScale = scale;
    };
    const handleGestureChange = (e: any) => {
      e.preventDefault();
      if (e.scale) {
        const nextScale = Math.min(Math.max(initialScale * e.scale, 0.8), 4);
        setScale(nextScale);
      }
    };

    window.addEventListener('wheel', handleWheel, { passive: false });
    window.addEventListener('gesturestart', handleGestureStart as any, { passive: false });
    window.addEventListener('gesturechange', handleGestureChange as any, { passive: false });

    return () => {
      window.removeEventListener('wheel', handleWheel);
      window.removeEventListener('gesturestart', handleGestureStart as any);
      window.removeEventListener('gesturechange', handleGestureChange as any);
    };
  }, [isFullscreenOpen, scale]);

  const handleZoomIn = () => setScale(prev => Math.min(prev + 0.5, 4));
  const handleZoomOut = () => setScale(prev => Math.max(prev - 0.5, 0.5));
  const handleResetZoom = () => setScale(1);

  const imageUrl = fullscreenPhotoId
    ? (imgError ? api.getPhotoThumbnailUrl(fullscreenPhotoId) : api.getPhotoOriginalUrl(fullscreenPhotoId))
    : '';

  return (
    <AnimatePresence>
      {isFullscreenOpen && fullscreenPhotoId && (
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
            zIndex: 100,
            backgroundColor: 'rgba(5, 5, 7, 0.95)',
            backdropFilter: 'blur(12px)',
            display: 'flex',
            flexDirection: 'column',
            userSelect: 'none',
            WebkitUserSelect: 'none',
            touchAction: 'none',
            overscrollBehavior: 'none',
            overflow: 'hidden'
          }}
        >
        {/* Zen Mode Notification Hint Snackbar */}
        <AnimatePresence>
          {showZenHint && (
            <motion.div
              initial={{ y: -30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: -30, opacity: 0 }}
              transition={{ duration: 0.25 }}
              style={{
                position: 'absolute',
                top: '20px',
                left: '50%',
                transform: 'translateX(-50%)',
                background: 'rgba(24, 24, 27, 0.9)',
                backdropFilter: 'blur(12px)',
                border: '1px solid rgba(56, 189, 248, 0.4)',
                color: '#38bdf8',
                borderRadius: '20px',
                padding: '8px 18px',
                fontSize: '12px',
                fontWeight: 600,
                boxShadow: '0 8px 25px rgba(0,0,0,0.6)',
                zIndex: 150,
                pointerEvents: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <Eye size={15} /> ✨ 몰입 감상 모드 (클릭 또는 F키로 UI 복원)
            </motion.div>
          )}
        </AnimatePresence>

        {/* Top Floating Control Bar */}
        <AnimatePresence>
          {!isZenMode && (
            <motion.div
              initial={{ y: -64, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: -64, opacity: 0 }}
              transition={{ duration: 0.2 }}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: '64px',
                padding: '0 24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: 'linear-gradient(to bottom, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%)',
                zIndex: 120,
                pointerEvents: 'auto'
              }}
            >
              {/* File Name & Info */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#f4f4f5', maxWidth: '400px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {photo?.file_name || '사진 전체화면 보기'}
                </h3>
                {photo?.metadata && (
                  <span style={{ fontSize: '12px', color: '#71717a', background: '#18181b', padding: '3px 8px', borderRadius: '4px', border: '1px solid #27272a' }}>
                    {photo.metadata.width} x {photo.metadata.height}
                  </span>
                )}
              </div>

              {/* Action Toolbar */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {/* Zen Mode Button */}
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={toggleZenMode}
                  style={{
                    background: '#18181b',
                    border: '1px solid #27272a',
                    color: '#38bdf8',
                    borderRadius: '6px', padding: '6px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                    fontSize: '12px', fontWeight: 600, transition: 'all 0.2s'
                  }}
                  title="몰입 감상 모드 (F / H)"
                >
                  <Eye size={15} /> 몰입 감상
                </motion.button>

                <div style={{ width: '1px', height: '20px', backgroundColor: '#27272a', margin: '0 2px' }} />

                {/* Fit Mode Toggle Button */}
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setFitMode(prev => prev === 'fit-height' ? 'contain' : prev === 'contain' ? 'cover' : 'fit-height')}
                  style={{
                    background: fitMode === 'fit-height' ? 'rgba(56, 189, 248, 0.2)' : '#18181b',
                    border: '1px solid',
                    borderColor: fitMode === 'fit-height' ? '#38bdf8' : '#3f3f46',
                    color: fitMode === 'fit-height' ? '#38bdf8' : '#e4e4e7',
                    borderRadius: '6px', padding: '6px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                    fontSize: '12px', fontWeight: 600, transition: 'background-color 0.2s, border-color 0.2s'
                  }}
                  title="화면 맞춤 토글 (세로 꽉 채우기 / 뷰포트 핏 / 커버)"
                >
                  {fitMode === 'fit-height' ? (
                    <>
                      <Maximize size={15} /> 세로 핏 (패딩 0)
                    </>
                  ) : fitMode === 'cover' ? (
                    <>
                      <Expand size={15} /> 화면 꽉 채우기
                    </>
                  ) : (
                    <>
                      <Maximize size={15} /> 여백 맞춤
                    </>
                  )}
                </motion.button>

                <div style={{ width: '1px', height: '20px', backgroundColor: '#27272a', margin: '0 2px' }} />

                {/* Zoom Out Button */}
                <motion.button
                  whileHover={scale > 0.5 ? { scale: 1.08, backgroundColor: '#27272a', borderColor: '#52525b' } : {}}
                  whileTap={scale > 0.5 ? { scale: 0.92 } : {}}
                  onClick={handleZoomOut}
                  disabled={scale <= 0.5}
                  style={{
                    background: '#18181b', border: '1px solid #27272a', color: scale <= 0.5 ? '#52525b' : '#e4e4e7',
                    borderRadius: '6px', padding: '8px', cursor: scale <= 0.5 ? 'not-allowed' : 'pointer', display: 'flex',
                    transition: 'all 0.15s ease'
                  }}
                  title="축소 (-)"
                >
                  <ZoomOut size={18} />
                </motion.button>
                
                {/* Reset Zoom Ratio Pill */}
                <motion.button
                  whileHover={{ scale: 1.08, backgroundColor: '#27272a', borderColor: '#38bdf8' }}
                  whileTap={{ scale: 0.92 }}
                  onClick={handleResetZoom}
                  style={{
                    background: '#18181b', border: '1px solid #27272a', color: '#e4e4e7',
                    borderRadius: '6px', padding: '6px 10px', cursor: 'pointer', fontSize: '12px', fontWeight: 600,
                    transition: 'all 0.15s ease'
                  }}
                  title="100% 원본 배율 (0)"
                >
                  {Math.round(scale * 100)}%
                </motion.button>

                {/* Zoom In Button */}
                <motion.button
                  whileHover={scale < 4 ? { scale: 1.08, backgroundColor: '#27272a', borderColor: '#52525b' } : {}}
                  whileTap={scale < 4 ? { scale: 0.92 } : {}}
                  onClick={handleZoomIn}
                  disabled={scale >= 4}
                  style={{
                    background: '#18181b', border: '1px solid #27272a', color: scale >= 4 ? '#52525b' : '#e4e4e7',
                    borderRadius: '6px', padding: '8px', cursor: scale >= 4 ? 'not-allowed' : 'pointer', display: 'flex',
                    transition: 'all 0.15s ease'
                  }}
                  title="확대 (+)"
                >
                  <ZoomIn size={18} />
                </motion.button>

                {/* Reset Ratio */}
                <motion.button
                  whileHover={{ scale: 1.08, backgroundColor: '#27272a', borderColor: '#52525b' }}
                  whileTap={{ scale: 0.92 }}
                  onClick={handleResetZoom}
                  style={{
                    background: '#18181b', border: '1px solid #27272a', color: '#e4e4e7',
                    borderRadius: '6px', padding: '8px', cursor: 'pointer', display: 'flex',
                    transition: 'all 0.15s ease'
                  }}
                  title="비율 초기화"
                >
                  <RotateCcw size={18} />
                </motion.button>

                <div style={{ width: '1px', height: '20px', backgroundColor: '#27272a', margin: '0 4px' }} />

                {/* EXIF Overlay Toggle */}
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setShowMetadata(prev => !prev)}
                  style={{
                    background: showMetadata ? '#38bdf8' : '#18181b',
                    border: '1px solid',
                    borderColor: showMetadata ? '#38bdf8' : '#27272a',
                    color: showMetadata ? '#000' : '#e4e4e7',
                    borderRadius: '6px', padding: '8px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                    fontSize: '12px', fontWeight: 600, transition: 'all 0.2s'
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

        {/* Left/Right Floating Navigation Arrows */}
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
            style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '100%', height: '100%', touchAction: 'none' }}
          >
            <img
              src={imageUrl}
              alt={photo?.file_name || '원본 사진'}
              draggable={false}
              onDragStart={(e) => e.preventDefault()}
              onError={() => setImgError(true)}
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
                boxShadow: '0 20px 50px rgba(0,0,0,0.8)'
              }}
            />
          </motion.div>
        </div>

        {/* Bottom Floating Metadata Overlay */}
        <AnimatePresence>
          {!isZenMode && showMetadata && photo && (
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
          )}
        </AnimatePresence>
      </motion.div>
      )}
    </AnimatePresence>
  );
}
