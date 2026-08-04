import { useState, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store/useAppStore';

export function useFullscreenControls() {
  const { isFullscreenOpen, fullscreenPhotoId, openFullscreen, setSelectedPhotoId, closeFullscreen } = useAppStore();
  const [scale, setScale] = useState(1);
  const [showMetadata, setShowMetadata] = useState(true);
  const [imgError, setImgError] = useState(false);
  const [fitMode, setFitMode] = useState<'fit-height' | 'contain' | 'cover'>('fit-height');
  const [isZenMode, setIsZenMode] = useState(false);
  const [showZenHint, setShowZenHint] = useState(false);
  const zenHintTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  const queryClient = useQueryClient();

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

  useEffect(() => {
    setScale(1);
    setImgError(false);
    setIsZenMode(false);
    setShowZenHint(false);
  }, [fullscreenPhotoId, isFullscreenOpen]);

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

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isFullscreenOpen) return;

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

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreenOpen, isZenMode, fullscreenPhotoId]);

  return {
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
    showZenHint,
    closeFullscreen,
    handlePrevPhoto,
    handleNextPhoto,
    toggleZenMode
  };
}
