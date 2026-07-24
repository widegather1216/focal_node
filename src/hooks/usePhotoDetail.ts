import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';

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
    shutter_speed: string | null;
    iso: number | null;
    capture_date: string | null;
  };
  ai_analysis: {
    caption: string | null;
    tags: string[];
    aesthetic_tags?: string[];
    is_user_edited: boolean;
  };
}

export function usePhotoDetail() {
  const { apiPort, selectedPhotoId, setSelectedPhotoId, setSearchQuery } = useAppStore();
  const queryClient = useQueryClient();

  const [photo, setPhoto] = useState<PhotoDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  
  const [captionEdit, setCaptionEdit] = useState('');
  const [tagsEdit, setTagsEdit] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const [critique, setCritique] = useState<string | null>(null);
  const [loadingCritique, setLoadingCritique] = useState(false);
  const [reindexing, setReindexing] = useState(false);

  useEffect(() => {
    if (!selectedPhotoId || !apiPort) {
      setPhoto(null);
      setEditing(false);
      setCritique(null);
      return;
    }

    const fetchDetail = async () => {
      setLoading(true);
      try {
        const data: PhotoDetail = await api.getPhotoDetail(selectedPhotoId);
        setPhoto(data);
        setCaptionEdit(data.ai_analysis?.caption || '');
        setTagsEdit(data.ai_analysis?.tags ? [...data.ai_analysis.tags] : []);
        setCritique(null);
      } catch (err) {
        console.error("Failed to fetch photo detail:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [selectedPhotoId, apiPort]);

  const handleSave = async () => {
    if (!selectedPhotoId || !apiPort) return;
    setSaving(true);
    try {
      const updated = await api.updatePhotoMetadata(selectedPhotoId, captionEdit, tagsEdit);
      setPhoto(prev => prev ? {
        ...prev,
        ai_analysis: updated.ai_analysis
      } : null);
      setEditing(false);
    } catch (err) {
      console.error("Failed to save metadata:", err);
    } finally {
      setSaving(false);
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
    if (!currentId) return;
    setLoadingCritique(true);
    try {
      const result = await api.getPhotoCritique(currentId);
      if (useAppStore.getState().selectedPhotoId === currentId) {
        setCritique(result.critique);
      }
    } catch (err) {
      if (useAppStore.getState().selectedPhotoId === currentId) {
        console.error("Failed to generate critique:", err);
        setCritique("비평을 생성하는 도중 오류가 발생했습니다.");
      }
    } finally {
      if (useAppStore.getState().selectedPhotoId === currentId) {
        setLoadingCritique(false);
      }
    }
  };

  const handleReindex = async () => {
    if (!selectedPhotoId) return;
    setReindexing(true);
    try {
      const updatedData = await api.reindexPhoto(selectedPhotoId);
      setPhoto(updatedData);
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
      const res = await api.toggleFavorite(photo.id);
      setPhoto(prev => prev ? { ...prev, is_favorite: res.is_favorite } : null);
      queryClient.invalidateQueries({ queryKey: ['photos'] });
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
    photo,
    loading,
    editing,
    setEditing,
    captionEdit,
    setCaptionEdit,
    tagsEdit,
    setTagsEdit,
    saving,
    critique,
    loadingCritique,
    reindexing,
    handleSave,
    handleReveal,
    handleRequestCritique,
    handleReindex,
    handleToggleFavorite,
    handleTagClick
  };
}
