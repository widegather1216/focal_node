import { useState, useEffect, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';
import { usePhotoDetailQuery, useUpdatePhotoMetadataMutation } from './usePhotoDetailQuery';
import { useToggleFavoriteMutation } from './usePhotosQuery';

export interface PhotoDetail {
  id: string;
  file_name: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  is_favorite: boolean;
  metadata: {
    width: number | null;
    height: number | null;
    color_space: string;
    camera_model: string | null;
    lens_model: string | null;
    f_number: number | null;
    focal_length: number | null;
    focal_length_35mm: number | null;
    crop_factor: number | null;
    sensor_format: string | null;
    shutter_speed: string | null;
    iso: number | null;
    capture_date: string | null;
  };
  ai_analysis: {
    caption: string | null;
    tags: string[];
    aesthetic_tags?: string[];
    is_user_edited: boolean;
    critique?: string | null;
    critique_updated_at?: string | null;
  };
}

export function usePhotoDetail() {
  const { 
    selectedPhotoId, 
    setSelectedPhotoId, 
    setSearchQuery, 
    searchQuery, 
    searchFilters,
    generatingCritiquePhotoIds,
    addGeneratingCritiquePhotoId,
    removeGeneratingCritiquePhotoId
  } = useAppStore();
  const queryClient = useQueryClient();

  const { data: photo, isLoading: loading } = usePhotoDetailQuery(selectedPhotoId);
  const updateMetadataMutation = useUpdatePhotoMetadataMutation();
  const toggleFavoriteMutation = useToggleFavoriteMutation(null, searchQuery, searchFilters);

  const [editing, setEditing] = useState(false);
  const [captionEdit, setCaptionEdit] = useState('');
  const [tagsEdit, setTagsEdit] = useState<string[]>([]);

  const [critique, setCritique] = useState<string | null>(null);
  const loadingCritique = Boolean(selectedPhotoId && generatingCritiquePhotoIds.has(selectedPhotoId));
  const [reindexing, setReindexing] = useState(false);

  useEffect(() => {
    if (photo) {
      setCaptionEdit(photo.ai_analysis?.caption || '');
      setTagsEdit(photo.ai_analysis?.tags ? [...photo.ai_analysis.tags] : []);
      setCritique(photo.ai_analysis?.critique || null);
    } else {
      setEditing(false);
      setCritique(null);
    }
  }, [photo]);

  const getActivePhotoList = (): any[] => {
    if (useAppStore.getState().activeTab === 'critique') {
      const critiqueData = queryClient.getQueryData<any[]>(['critiques']);
      if (Array.isArray(critiqueData) && critiqueData.length > 0) {
        return critiqueData.map(c => ({ id: c.photo_id, ...c }));
      }
    }

    const queryCache = queryClient.getQueriesData<any>({ queryKey: ['photos'] });
    for (const [, data] of queryCache) {
      if (data && data.pages && Array.isArray(data.pages)) {
        return data.pages.flatMap((page: any) => page);
      }
      if (Array.isArray(data)) {
        return data;
      }
    }
    return [];
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const { isFullscreenOpen } = useAppStore.getState();
      if (!selectedPhotoId || isFullscreenOpen) return;

      const target = e.target as HTMLElement | null;
      if (editing || (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable))) {
        return;
      }

      if (e.key === 'Escape') {
        setSelectedPhotoId(null);
      } else if (e.key === 'ArrowLeft') {
        const photos = getActivePhotoList();
        if (!photos.length) return;
        const currentIndex = photos.findIndex((p: any) => p.id === selectedPhotoId);
        if (currentIndex > 0) {
          setSelectedPhotoId(photos[currentIndex - 1].id);
        }
      } else if (e.key === 'ArrowRight') {
        const photos = getActivePhotoList();
        if (!photos.length) return;
        const currentIndex = photos.findIndex((p: any) => p.id === selectedPhotoId);
        if (currentIndex !== -1 && currentIndex < photos.length - 1) {
          setSelectedPhotoId(photos[currentIndex + 1].id);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedPhotoId, setSelectedPhotoId, editing]);

  const handleSave = async () => {
    if (!selectedPhotoId) return;
    try {
      await updateMetadataMutation.mutateAsync({
        photoId: selectedPhotoId,
        caption: captionEdit,
        tags: tagsEdit,
      });
      setEditing(false);
    } catch (err) {
      console.error("Failed to save metadata:", err);
    }
  };

  const handleReveal = async () => {
    if (!photo) return;
    try {
      await invoke('reveal_in_finder', { path: photo.file_path });
    } catch (err) {
      console.error("Failed to reveal in finder", err);
    }
  };

  const critiqueAbortControllerRef = useRef<AbortController | null>(null);

  const pollAndRecoverCritique = async (photoId: string, signal: AbortSignal): Promise<string | null> => {
    const maxAttempts = 35; // Poll up to ~50 seconds to allow MLX pipeline completion after sleep
    const intervalMs = 1500;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      if (signal.aborted) {
        return null;
      }
      try {
        const st = await api.getCritiqueStatus(photoId);
        if (st.status === 'completed' && st.critique) {
          return st.critique;
        }
        if (st.status === 'cancelled') {
          return null;
        }
        if (st.status === 'error') {
          throw new Error(st.message || "비평 생성 오류");
        }
      } catch (err: any) {
        if (err.message && err.message.includes("비평 생성 오류")) {
          throw err;
        }
        // Silently tolerate transient network connection drops during OS sleep/wake
      }
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
    return null;
  };

  // Re-sync on sleep wake-up (visibility change, window focus, network online)
  useEffect(() => {
    const handleWakeOrFocus = async () => {
      const { activeCritiqueJob, selectedPhotoId: currentSelectedId } = useAppStore.getState();
      const targetId = activeCritiqueJob?.photoId || currentSelectedId;
      if (!targetId) return;

      try {
        const st = await api.getCritiqueStatus(targetId);
        if (st.status === 'completed' && st.critique) {
          if (useAppStore.getState().selectedPhotoId === targetId) {
            setCritique(st.critique);
          }
          queryClient.invalidateQueries({ queryKey: ['critiques'] });
          queryClient.invalidateQueries({ queryKey: ['photoDetail', targetId] });
        }
      } catch {
        // Silently ignore if backend is still initializing/waking up
      }
    };

    window.addEventListener('focus', handleWakeOrFocus);
    window.addEventListener('online', handleWakeOrFocus);
    document.addEventListener('visibilitychange', handleWakeOrFocus);

    return () => {
      window.removeEventListener('focus', handleWakeOrFocus);
      window.removeEventListener('online', handleWakeOrFocus);
      document.removeEventListener('visibilitychange', handleWakeOrFocus);
    };
  }, [queryClient]);

  const handleRequestCritique = async () => {
    const currentId = selectedPhotoId;
    if (!currentId || generatingCritiquePhotoIds.has(currentId)) return;

    if (critiqueAbortControllerRef.current) {
      critiqueAbortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    critiqueAbortControllerRef.current = abortController;

    addGeneratingCritiquePhotoId(currentId);
    useAppStore.getState().setActiveCritiqueJob({ photoId: currentId, fileName: photo?.file_name });
    try {
      const result = await api.getPhotoCritique(currentId, abortController.signal);
      if (result.status === 'cancelled') {
        return;
      }
      if (useAppStore.getState().selectedPhotoId === currentId) {
        setCritique(result.critique);
      }
      queryClient.invalidateQueries({ queryKey: ['critiques'] });
      queryClient.invalidateQueries({ queryKey: ['photoDetail', currentId] });
    } catch (err: any) {
      if (err.name === 'AbortError' || abortController.signal.aborted) {
        return;
      }

      // Potential socket disconnect caused by system sleep/wake.
      // Attempt recovery by polling backend status before treating as failure.
      try {
        const recoveredCritique = await pollAndRecoverCritique(currentId, abortController.signal);
        if (abortController.signal.aborted) return;

        if (recoveredCritique) {
          if (useAppStore.getState().selectedPhotoId === currentId) {
            setCritique(recoveredCritique);
          }
          queryClient.invalidateQueries({ queryKey: ['critiques'] });
          queryClient.invalidateQueries({ queryKey: ['photoDetail', currentId] });
          return;
        }
      } catch (recoverErr) {
        console.warn("Critique recovery attempt error:", recoverErr);
      }

      if (useAppStore.getState().selectedPhotoId === currentId) {
        console.error("Failed to generate critique:", err);
        setCritique("비평을 생성하는 도중 오류가 발생했습니다.");
      }
    } finally {
      removeGeneratingCritiquePhotoId(currentId);
      if (critiqueAbortControllerRef.current === abortController) {
        critiqueAbortControllerRef.current = null;
      }
      setTimeout(() => {
        if (useAppStore.getState().activeCritiqueJob?.photoId === currentId) {
          useAppStore.getState().setActiveCritiqueJob(null);
        }
      }, 3500);
    }
  };


  const handleCancelCritique = async () => {
    const currentId = selectedPhotoId;
    if (!currentId) return;

    if (critiqueAbortControllerRef.current) {
      critiqueAbortControllerRef.current.abort();
      critiqueAbortControllerRef.current = null;
    }

    try {
      await api.cancelCritique(currentId);
    } catch (err) {
      console.warn("Backend cancel critique error:", err);
    } finally {
      removeGeneratingCritiquePhotoId(currentId);
      if (useAppStore.getState().activeCritiqueJob?.photoId === currentId) {
        useAppStore.getState().setActiveCritiqueJob(null);
      }
      queryClient.invalidateQueries({ queryKey: ['critiques'] });
      queryClient.invalidateQueries({ queryKey: ['photoDetail', currentId] });
    }
  };

  const handleDeleteCritique = async () => {
    const currentId = selectedPhotoId;
    if (!currentId) return;
    try {
      await api.deleteCritique(currentId);
      if (useAppStore.getState().selectedPhotoId === currentId) {
        setCritique(null);
      }
      queryClient.invalidateQueries({ queryKey: ['critiques'] });
      queryClient.invalidateQueries({ queryKey: ['photoDetail', currentId] });
    } catch (err) {
      console.error("Failed to delete critique:", err);
    }
  };

  const handleReindex = async () => {
    if (!selectedPhotoId) return;
    setReindexing(true);
    try {
      const updatedData = await api.reindexPhoto(selectedPhotoId);
      setCaptionEdit(updatedData.ai_analysis?.caption || '');
      setTagsEdit(updatedData.ai_analysis?.tags ? [...updatedData.ai_analysis.tags] : []);
    } catch (err) {
      console.error("Failed to reindex photo:", err);
    } finally {
      setReindexing(false);
    }
  };

  const handleToggleFavorite = async () => {
    if (!photo) return;
    try {
      await toggleFavoriteMutation.mutateAsync(photo.id);
    } catch (err) {
      console.error("Failed to toggle favorite:", err);
    }
  };

  const handleTagClick = (tag: string) => {
    setSearchQuery(tag);
    setSelectedPhotoId(null);
  };

  return {
    selectedPhotoId,
    setSelectedPhotoId,
    photo: photo || null,
    loading,
    editing,
    setEditing,
    captionEdit,
    setCaptionEdit,
    tagsEdit,
    setTagsEdit,
    saving: updateMetadataMutation.isPending,
    critique,
    loadingCritique,
    reindexing,
    handleSave,
    handleReveal,
    handleRequestCritique,
    handleCancelCritique,
    handleDeleteCritique,
    handleReindex,
    handleToggleFavorite,
    handleTagClick
  };
}
