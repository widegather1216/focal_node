import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Save, Camera, Aperture, Clock, Sun, Focus, FolderOpen, Wand2, RefreshCw, Heart } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { invoke } from '@tauri-apps/api/core';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';

interface PhotoDetail {
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

const PhotoExif = ({ metadata }: { metadata: PhotoDetail['metadata'] }) => (
  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
    {metadata?.camera_model && (
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
        <Camera size={14} />
        {metadata.camera_model}
      </div>
    )}
    {metadata?.lens_model && (
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
        <Focus size={14} />
        {metadata.lens_model}
      </div>
    )}
    {metadata?.f_number && (
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
        <Aperture size={14} />
        f/{metadata.f_number}
      </div>
    )}
    {metadata?.shutter_speed && (
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
        <Clock size={14} />
        {metadata.shutter_speed}s
      </div>
    )}
    {metadata?.iso && (
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#333', padding: '6px 12px', borderRadius: '4px', fontSize: '12px' }}>
        <Sun size={14} />
        ISO {metadata.iso}
      </div>
    )}
  </div>
);

export function DetailPanel() {
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
      console.error(err);
    }
  };

  const handleTagClick = (tag: string) => {
    setSearchQuery(tag);
    setSelectedPhotoId(null);
  };

  return (
    <AnimatePresence>
      {selectedPhotoId && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: '#000',
              zIndex: 10,
            }}
            onClick={() => setSelectedPhotoId(null)}
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            style={{
              position: 'fixed',
              top: 0,
              right: 0,
              width: '500px',
              height: '100vh',
              backgroundColor: '#1a1a1a',
              zIndex: 20,
              boxShadow: '-4px 0 24px rgba(0,0,0,0.5)',
              display: 'flex',
              flexDirection: 'column',
              color: '#fff',
              overflowY: 'auto'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px', borderBottom: '1px solid #333' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 600, margin: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {photo?.file_name || 'Loading...'}
              </h2>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  onClick={handleToggleFavorite}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
                  title="즐겨찾기"
                >
                  <Heart size={20} fill={photo?.is_favorite ? '#ef4444' : 'none'} color={photo?.is_favorite ? '#ef4444' : '#fff'} />
                </button>
                <button 
                  onClick={() => setSelectedPhotoId(null)}
                  style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            {loading ? (
              <div style={{ padding: '20px', textAlign: 'center', color: '#aaa' }}>Loading details...</div>
            ) : photo ? (
              <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                <div style={{ width: '100%', height: '300px', backgroundColor: '#000', position: 'relative', flexShrink: 0 }}>
                  {apiPort && (
                    <img 
                      src={api.getPhotoOriginalUrl(photo.id)}
                      alt={photo.file_name}
                      style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                    />
                  )}
                </div>

                <div style={{ padding: '24px', flex: 1, display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  
                  {/* EXIF Section */}
                  <PhotoExif metadata={photo.metadata} />

                  {/* Date and Dimensions */}
                  <div style={{ fontSize: '13px', color: '#888', display: 'flex', justifyContent: 'space-between' }}>
                    <span>{photo.metadata?.capture_date ? new Date(photo.metadata.capture_date).toLocaleString() : 'Unknown Date'}</span>
                    <span>{photo.metadata?.width && photo.metadata?.height ? `${photo.metadata.width} x ${photo.metadata.height}` : ''}</span>
                  </div>

                  {/* AI Analysis Section */}
                  <div style={{ borderTop: '1px solid #333', paddingTop: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <h3 style={{ fontSize: '16px', margin: 0, fontWeight: 500, display: 'flex', alignItems: 'center', gap: '8px' }}>
                        AI Analysis
                        {photo.ai_analysis?.is_user_edited && (
                          <span style={{ fontSize: '10px', background: '#4CAF50', color: '#fff', padding: '2px 6px', borderRadius: '10px' }}>Edited</span>
                        )}
                      </h3>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={handleReindex}
                          disabled={reindexing}
                          style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'none', border: '1px solid #4CAF50', color: '#4CAF50', padding: '4px 12px', borderRadius: '4px', cursor: reindexing ? 'default' : 'pointer', fontSize: '12px', opacity: reindexing ? 0.7 : 1 }}
                          title="AI 분석 재시도"
                        >
                          <motion.div
                            animate={reindexing ? { rotate: 360 } : {}}
                            transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                          >
                            <RefreshCw size={14} />
                          </motion.div>
                          {reindexing ? '재분석 중...' : '재분석'}
                        </button>
                        <button
                          onClick={() => {
                            setSearchQuery(`similar:${photo.id}`);
                            setSelectedPhotoId(null);
                          }}
                          style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(255, 215, 0, 0.1)', border: '1px solid rgba(255, 215, 0, 0.4)', color: '#ffd700', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                          title="비슷한 무드 찾기 (Similar Mood Search)"
                        >
                          <Wand2 size={14} />
                          Similar
                        </button>
                        <button
                          onClick={handleReveal}
                          style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'none', border: '1px solid #444', color: '#fff', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                          title="Reveal in OS"
                        >
                          <FolderOpen size={14} />
                          Reveal
                        </button>
                        {!editing ? (
                          <button 
                            onClick={() => setEditing(true)}
                            style={{ background: 'none', border: '1px solid #444', color: '#fff', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                          >
                            Edit
                          </button>
                        ) : (
                          <button 
                            onClick={handleSave}
                            disabled={saving}
                            style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#4CAF50', border: 'none', color: '#fff', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                          >
                            <Save size={14} />
                            {saving ? 'Saving...' : 'Save'}
                          </button>
                        )}
                      </div>
                    </div>

                    {editing ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <div>
                          <label style={{ display: 'block', fontSize: '12px', color: '#aaa', marginBottom: '8px' }}>Caption</label>
                          <textarea
                            value={captionEdit}
                            onChange={e => setCaptionEdit(e.target.value)}
                            style={{ width: '100%', minHeight: '80px', background: '#222', border: '1px solid #444', color: '#fff', padding: '8px', borderRadius: '4px', boxSizing: 'border-box', resize: 'vertical' }}
                          />
                        </div>
                        <div>
                          <label style={{ display: 'block', fontSize: '12px', color: '#aaa', marginBottom: '8px' }}>Tags</label>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '8px' }}>
                            {tagsEdit.map((tag, idx) => (
                              <span key={idx} style={{ background: '#2a2a2a', border: '1px solid #444', padding: '4px 8px', borderRadius: '16px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                {tag}
                                <button
                                  onClick={() => setTagsEdit(prev => prev.filter((_, i) => i !== idx))}
                                  style={{ background: 'none', border: 'none', color: '#aaa', cursor: 'pointer', padding: 0, display: 'flex' }}
                                >
                                  <X size={12} />
                                </button>
                              </span>
                            ))}
                          </div>
                          <input
                            type="text"
                            placeholder="태그를 입력하고 Enter를 누르세요..."
                            onKeyDown={e => {
                              if (e.key === 'Enter') {
                                e.preventDefault();
                                const val = e.currentTarget.value.trim();
                                if (val && !tagsEdit.includes(val)) {
                                  setTagsEdit(prev => [...prev, val]);
                                  e.currentTarget.value = '';
                                }
                              }
                            }}
                            style={{ width: '100%', background: '#222', border: '1px solid #444', color: '#fff', padding: '8px', borderRadius: '4px', boxSizing: 'border-box' }}
                          />
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <div>
                          <label style={{ display: 'block', fontSize: '12px', color: '#aaa', marginBottom: '8px' }}>Caption</label>
                          <p style={{ margin: 0, fontSize: '14px', lineHeight: 1.5 }}>
                            {photo.ai_analysis?.caption || <span style={{ color: '#666', fontStyle: 'italic' }}>No caption generated</span>}
                          </p>
                        </div>
                        <div>
                          <label style={{ display: 'block', fontSize: '12px', color: '#aaa', marginBottom: '8px' }}>Tags</label>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                            {photo.ai_analysis?.aesthetic_tags && photo.ai_analysis.aesthetic_tags.length > 0 && (
                                photo.ai_analysis.aesthetic_tags.map((tag, idx) => (
                                  <span 
                                    key={`aes-${idx}`} 
                                    onClick={() => handleTagClick(tag)}
                                    style={{ background: 'rgba(255, 215, 0, 0.1)', border: '1px solid rgba(255, 215, 0, 0.4)', color: '#ffd700', padding: '4px 10px', borderRadius: '16px', fontSize: '12px', fontWeight: 500, cursor: 'pointer' }}
                                    onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255, 215, 0, 0.2)'; }}
                                    onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255, 215, 0, 0.1)'; }}
                                  >
                                    ✨ {tag}
                                  </span>
                                ))
                            )}
                            {photo.ai_analysis?.tags && photo.ai_analysis.tags.length > 0 ? (
                              photo.ai_analysis.tags.map((tag, idx) => (
                                <span 
                                  key={`tag-${idx}`} 
                                  onClick={() => handleTagClick(tag)}
                                  style={{ background: '#2a2a2a', border: '1px solid #444', padding: '4px 10px', borderRadius: '16px', fontSize: '12px', cursor: 'pointer' }}
                                  onMouseEnter={(e) => { e.currentTarget.style.background = '#3a3a3a'; }}
                                  onMouseLeave={(e) => { e.currentTarget.style.background = '#2a2a2a'; }}
                                >
                                  {tag}
                                </span>
                              ))
                            ) : (
                              (!photo.ai_analysis?.aesthetic_tags || photo.ai_analysis.aesthetic_tags.length === 0) && (
                                <span style={{ color: '#666', fontStyle: 'italic', fontSize: '14px' }}>No tags available</span>
                              )
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Expert Critique Section */}
                  <div style={{ borderTop: '1px solid #333', paddingTop: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <h3 style={{ fontSize: '16px', margin: 0, fontWeight: 500, display: 'flex', alignItems: 'center', gap: '8px' }}>
                        ✨ 전문가 AI 비평
                      </h3>
                      {!critique && !loadingCritique && (
                        <button
                          onClick={handleRequestCritique}
                          style={{ background: 'rgba(255, 215, 0, 0.1)', border: '1px solid rgba(255, 215, 0, 0.4)', color: '#ffd700', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <Wand2 size={14} />
                          비평 받기
                        </button>
                      )}
                    </div>
                    
                    {loadingCritique ? (
                      <div style={{ padding: '20px', textAlign: 'center', color: '#aaa', background: '#222', borderRadius: '8px' }}>
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                          style={{ display: 'inline-block', marginBottom: '8px', color: '#ffd700' }}
                        >
                          <Wand2 size={24} />
                        </motion.div>
                        <div style={{ fontSize: '13px', marginTop: '8px' }}>AI 전문가가 사진을 정밀 분석하고 있습니다...</div>
                      </div>
                    ) : critique ? (
                      <div style={{ background: '#222', padding: '16px', borderRadius: '8px', border: '1px solid #333' }}>
                        <p style={{ margin: 0, fontSize: '14px', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                          {critique}
                        </p>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
