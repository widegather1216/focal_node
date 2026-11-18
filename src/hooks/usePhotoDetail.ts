import { useState, useEffect, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';
import { PhotoDetail } from '../types/photo';
import { getActivePhotoList } from '../utils/activePhotoList';
import { pollAndRecoverCritique } from './useCritiqueStatusPolling';
import { usePhotoDetailQuery, useUpdatePhotoMetadataMutation } from './usePhotoDetailQuery';
import { useToggleFavoriteMutation } from './usePhotosQuery';
import {
  addReindexingPhotoId,
  clearPhotoReindexError,
  executePhotoReindex,
  removeReindexingPhotoId,
  setPhotoReindexError,
  shouldSyncPhotoEditFields,
} from '../utils/photoReindex';

export type { PhotoDetail };

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
  const [reindexingPhotoIds, setReindexingPhotoIds] = useState<Set<string>>(() => new Set());
  const [reindexingErrors, setReindexingErrors] = useState<Record<string, string>>({});
  const reindexing = Boolean(selectedPhotoId && reindexingPhotoIds.has(selectedPhotoId));
  const reindexingError = selectedPhotoId ? (reindexingErrors[selectedPhotoId] ?? null) : null;

  const isMountedRef = useRef(true);
  const inFlightReindexIdsRef = useRef<Set<string>>(new Set());
  const reindexRequestSeqRef = useRef<Map<string, number>>(new Map());
  const lastSyncedPhotoIdRef = useRef<string | null>(null);
  const editingRef = useRef(editing);
  editingRef.current = editing;
  const critiqueAbortControllerRef = useRef<AbortController | null>(null);
  const clearJobTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearJobCleanupTimer = () => {
    if (clearJobTimerRef.current !== null) {
      clearTimeout(clearJobTimerRef.current);
      clearJobTimerRef.current = null;
    }
  };

  useEffect(() => {
    // Re-arm on mount because React.StrictMode invokes cleanup once between initial checks.
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      clearJobCleanupTimer();
    };
  }, []);

  useEffect(() => {
    editingRef.current = false;
    setEditing(false);
  }, [selectedPhotoId]);

  useEffect(() => {
    if (!photo) {
      lastSyncedPhotoIdRef.current = null;
      editingRef.current = false;
      setEditing(false);
      setCritique(null);
      return;
    }

    const shouldSyncEdits = shouldSyncPhotoEditFields(
      photo.id,
      lastSyncedPhotoIdRef.current,
      editingRef.current,
    );
    if (lastSyncedPhotoIdRef.current !== photo.id) {
      editingRef.current = false;
      setEditing(false);
    }
    lastSyncedPhotoIdRef.current = photo.id;
    setCritique(photo.ai_analysis?.critique || null);
    if (shouldSyncEdits) {
      setCaptionEdit(photo.ai_analysis?.caption || '');
      setTagsEdit(photo.ai_analysis?.tags ? [...photo.ai_analysis.tags] : []);
    }
  }, [photo]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const { isFullscreenOpen } = useAppStore.getState();
      if (!selectedPhotoId || isFullscreenOpen) return;

      const target = event.target as HTMLElement | null;
      const isTextInput = target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);
      if (editing || isTextInput) return;

      if (event.key === 'Escape') {
        setSelectedPhotoId(null);
        return;
      }

      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      const activePhotos = getActivePhotoList(queryClient);
      if (activePhotos.length === 0) return;

      const currentIndex = activePhotos.findIndex((item) => item.id === selectedPhotoId);
      if (event.key === 'ArrowLeft' && currentIndex > 0) {
        setSelectedPhotoId(activePhotos[currentIndex - 1].id);
      } else if (event.key === 'ArrowRight' && currentIndex !== -1 && currentIndex < activePhotos.length - 1) {
        setSelectedPhotoId(activePhotos[currentIndex + 1].id);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedPhotoId, setSelectedPhotoId, editing, queryClient]);

  // Re-sync on sleep wake-up (visibility change, window focus, network online)
  useEffect(() => {
    const handleWakeOrFocus = async () => {
      if (document.visibilityState === 'hidden') return;
      const { activeCritiqueJob, selectedPhotoId: currentSelectedId } = useAppStore.getState();
      const targetId = activeCritiqueJob?.photoId || currentSelectedId;
      if (!targetId) return;

      try {
        const critiqueStatus = await api.getCritiqueStatus(targetId);
        if (critiqueStatus.status === 'completed' && critiqueStatus.critique) {
          if (useAppStore.getState().selectedPhotoId === targetId) {
            setCritique(critiqueStatus.critique);
          }
          queryClient.invalidateQueries({ queryKey: ['critiques'] });
          queryClient.invalidateQueries({ queryKey: ['photoDetail', targetId] });
        }
      } catch (error: unknown) {
        console.debug("[usePhotoDetail] Wake-up critique status sync skipped:", error);
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

  const handleSave = async () => {
    if (!selectedPhotoId) return;
    try {
      await updateMetadataMutation.mutateAsync({
        photoId: selectedPhotoId,
        caption: captionEdit,
        tags: tagsEdit,
      });
      setEditing(false);
    } catch (error: unknown) {
      console.error("Failed to save metadata:", error);
    }
  };

  const handleReveal = async () => {
    if (!photo) return;
    try {
      await invoke('reveal_in_finder', { path: photo.file_path });
    } catch (error: unknown) {
      console.error("Failed to reveal in finder", error);
    }
  };

  const handleRequestCritique = async () => {
    const currentId = selectedPhotoId;
    if (!currentId || generatingCritiquePhotoIds.has(currentId)) return;

    clearJobCleanupTimer();
    if (critiqueAbortControllerRef.current) {
      critiqueAbortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    critiqueAbortControllerRef.current = abortController;

    addGeneratingCritiquePhotoId(currentId);
    useAppStore.getState().setActiveCritiqueJob({ photoId: currentId, fileName: photo?.file_name });
    try {
      const critiqueResult = await api.getPhotoCritique(currentId, abortController.signal);
      if (critiqueResult.status === 'cancelled') return;
      if (useAppStore.getState().selectedPhotoId === currentId) {
        setCritique(critiqueResult.critique);
      }
      queryClient.invalidateQueries({ queryKey: ['critiques'] });
      queryClient.invalidateQueries({ queryKey: ['photoDetail', currentId] });
    } catch (error: unknown) {
      if ((error instanceof Error && error.name === 'AbortError') || abortController.signal.aborted) {
        return;
      }
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
      } catch (recoverError: unknown) {
        console.warn("Critique recovery attempt error:", recoverError);
      }
      if (useAppStore.getState().selectedPhotoId === currentId) {
        console.error("Failed to generate critique:", error);
        setCritique("비평을 생성하는 도중 오류가 발생했습니다.");
      }
    } finally {
      removeGeneratingCritiquePhotoId(currentId);
      if (critiqueAbortControllerRef.current === abortController) {
        critiqueAbortControllerRef.current = null;
      }
      clearJobCleanupTimer();
      clearJobTimerRef.current = setTimeout(() => {
        const latestState = useAppStore.getState();
        if (
          latestState.activeCritiqueJob?.photoId === currentId &&
          !latestState.generatingCritiquePhotoIds.has(currentId)
        ) {
          latestState.setActiveCritiqueJob(null);
        }
      }, 3500);
    }
  };

  const handleCancelCritique = async () => {
    const currentId = selectedPhotoId;
    if (!currentId) return;

    clearJobCleanupTimer();
    if (critiqueAbortControllerRef.current) {
      critiqueAbortControllerRef.current.abort();
      critiqueAbortControllerRef.current = null;
    }

    try {
      await api.cancelCritique(currentId);
    } catch (error: unknown) {
      console.warn("Backend cancel critique error:", error);
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
    } catch (error: unknown) {
      console.error("Failed to delete critique:", error);
    }
  };

  const dismissReindexError = () => {
    const activeId = useAppStore.getState().selectedPhotoId;
    if (!activeId) return;
    setReindexingErrors((prev) => clearPhotoReindexError(prev, activeId));
  };

  const handleReindex = async () => {
    await executePhotoReindex({
      targetId: useAppStore.getState().selectedPhotoId,
      inFlightIds: inFlightReindexIdsRef.current,
      requestSeqByPhoto: reindexRequestSeqRef.current,
      reindexPhoto: (photoId) => api.reindexPhoto(photoId),
      queryClient,
      getSelectedPhotoId: () => useAppStore.getState().selectedPhotoId,
      isMounted: () => isMountedRef.current,
      onStart: (targetId) => {
        setReindexingPhotoIds((prev) => addReindexingPhotoId(prev, targetId));
        setReindexingErrors((prev) => clearPhotoReindexError(prev, targetId));
      },
      onSuccessActive: (updatedPhoto) => {
        editingRef.current = false;
        setEditing(false);
        setCaptionEdit(updatedPhoto.ai_analysis?.caption || '');
        setTagsEdit(updatedPhoto.ai_analysis?.tags ? [...updatedPhoto.ai_analysis.tags] : []);
        setCritique(updatedPhoto.ai_analysis?.critique || null);
      },
      onError: (targetId, errorMessage) => {
        setReindexingErrors((prev) => setPhotoReindexError(prev, targetId, errorMessage));
      },
      onFinish: (targetId) => {
        setReindexingPhotoIds((prev) => removeReindexingPhotoId(prev, targetId));
      },
    });
  };

  const handleToggleFavorite = async () => {
    if (!photo) return;
    try {
      await toggleFavoriteMutation.mutateAsync(photo.id);
    } catch (error: unknown) {
      console.error("Failed to toggle favorite:", error);
    }
  };

  const handleTagClick = (tag: string) => {
    setSearchQuery(tag);
    setSelectedPhotoId(null);
  };

  return {
    selectedPhotoId, setSelectedPhotoId,
    photo: photo || null, loading,
    editing, setEditing,
    captionEdit, setCaptionEdit,
    tagsEdit, setTagsEdit,
    saving: updateMetadataMutation.isPending,
    critique, loadingCritique, reindexing, reindexingError,
    handleSave, handleReveal, handleRequestCritique, handleCancelCritique,
    handleDeleteCritique, handleReindex, dismissReindexError, handleToggleFavorite, handleTagClick
  };
}
