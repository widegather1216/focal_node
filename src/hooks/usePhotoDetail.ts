import { useState, useEffect } from 'react';
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
    const queryCache = queryClient.getQueriesData<any>({ queryKey: ['photos'] });
    for (const [, data] of queryCache) {
      if (data && data.pages) {
        return data.pages.flatMap((page: any) => page);
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

  const handleRequestCritique = async () => {
    const currentId = selectedPhotoId;
    if (!currentId || generatingCritiquePhotoIds.has(currentId)) return;
    addGeneratingCritiquePhotoId(currentId);
    useAppStore.getState().setActiveCritiqueJob({ photoId: currentId, fileName: photo?.file_name });
    try {
      const result = await api.getPhotoCritique(currentId);
      if (useAppStore.getState().selectedPhotoId === currentId) {
        setCritique(result.critique);
      }
      queryClient.invalidateQueries({ queryKey: ['critiques'] });
      queryClient.invalidateQueries({ queryKey: ['photoDetail', currentId] });
    } catch (err) {
      if (useAppStore.getState().selectedPhotoId === currentId) {
        console.error("Failed to generate critique:", err);
        setCritique("비평을 생성하는 도중 오류가 발생했습니다.");
      }
    } finally {
      removeGeneratingCritiquePhotoId(currentId);
      setTimeout(() => {
        if (useAppStore.getState().activeCritiqueJob?.photoId === currentId) {
          useAppStore.getState().setActiveCritiqueJob(null);
        }
      }, 3500);
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
    handleDeleteCritique,
    handleReindex,
    handleToggleFavorite,
    handleTagClick
  };
}
