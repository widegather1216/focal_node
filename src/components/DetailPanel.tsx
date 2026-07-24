import { motion, AnimatePresence } from 'framer-motion';
import { X, Save, FolderOpen, RefreshCw, Heart } from 'lucide-react';
import { api } from '../services/api';
import { usePhotoDetail } from '../hooks/usePhotoDetail';
import { PhotoExifView } from './detail/PhotoExifView';
import { PhotoCritiqueView } from './detail/PhotoCritiqueView';

export function DetailPanel() {
  const {
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
  } = usePhotoDetail();

  return (
    <AnimatePresence>
      {selectedPhotoId && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelectedPhotoId(null)}
            style={{
              position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(4px)', zIndex: 40
            }}
          />

          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            style={{
              position: 'fixed', top: 0, right: 0, bottom: 0, width: '420px',
              backgroundColor: '#18181b', borderLeft: '1px solid #27272a',
              color: '#f4f4f5', zIndex: 50, display: 'flex', flexDirection: 'column',
              boxShadow: '-10px 0 25px rgba(0,0,0,0.5)'
            }}
          >
            {/* Panel Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid #27272a' }}>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>사진 상세 정보</h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {photo && (
                  <button
                    onClick={handleToggleFavorite}
                    style={{ background: 'none', border: 'none', color: photo.is_favorite ? '#ef4444' : '#71717a', cursor: 'pointer', padding: '4px' }}
                    title={photo.is_favorite ? "즐겨찾기 해제" : "즐겨찾기 추가"}
                  >
                    <Heart size={20} fill={photo.is_favorite ? '#ef4444' : 'none'} />
                  </button>
                )}
                <button
                  onClick={() => setSelectedPhotoId(null)}
                  style={{ background: 'none', border: 'none', color: '#a1a1aa', cursor: 'pointer', padding: '4px' }}
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            {/* Panel Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
              {loading && (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px', color: '#71717a' }}>
                  로딩 중...
                </div>
              )}

              {!loading && photo && (
                <>
                  {/* Image Preview */}
                  <div style={{ borderRadius: '8px', overflow: 'hidden', backgroundColor: '#09090b', marginBottom: '20px', display: 'flex', justifyContent: 'center', maxHeight: '280px' }}>
                    <img
                      src={api.getPhotoThumbnailUrl(photo.id)}
                      alt={photo.file_name}
                      style={{ maxWidth: '100%', maxHeight: '280px', objectFit: 'contain' }}
                    />
                  </div>

                  {/* File Info */}
                  <div style={{ marginBottom: '20px' }}>
                    <h4 style={{ margin: '0 0 8px 0', fontSize: '15px', wordBreak: 'break-all' }}>{photo.file_name}</h4>
                    <div style={{ fontSize: '12px', color: '#71717a', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>해상도:</span>
                        <span style={{ color: '#a1a1aa' }}>{photo.metadata.width} x {photo.metadata.height}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>색상 공간:</span>
                        <span style={{ color: '#a1a1aa' }}>{photo.metadata.color_space}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>파일 위치:</span>
                        <button
                          onClick={handleReveal}
                          style={{
                            background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer',
                            padding: 0, fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px',
                            textDecoration: 'underline'
                          }}
                        >
                          <FolderOpen size={12} /> Finder에서 열기
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* EXIF Metadata */}
                  <div style={{ marginBottom: '20px' }}>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.05em' }}>EXIF 촬영 정보</h4>
                    <PhotoExifView metadata={photo.metadata} />
                  </div>

                  {/* AI Analysis Section */}
                  <div style={{ marginBottom: '20px', backgroundColor: '#18181b', borderRadius: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                      <h4 style={{ margin: 0, fontSize: '13px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.05em' }}>AI 메타데이터 묘사</h4>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={handleReindex}
                          disabled={reindexing}
                          style={{ background: 'none', border: 'none', color: '#a1a1aa', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                          title="AI 분석 다시 실행"
                        >
                          <RefreshCw size={12} className={reindexing ? 'spin' : ''} /> Re-index
                        </button>
                        {!editing ? (
                          <button
                            onClick={() => setEditing(true)}
                            style={{ background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer', fontSize: '12px' }}
                          >
                            편집
                          </button>
                        ) : (
                          <button
                            onClick={handleSave}
                            disabled={saving}
                            style={{ background: '#38bdf8', border: 'none', color: '#000', cursor: 'pointer', fontSize: '12px', padding: '2px 8px', borderRadius: '4px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}
                          >
                            <Save size={12} /> {saving ? '저장 중...' : '저장'}
                          </button>
                        )}
                      </div>
                    </div>

                    {!editing ? (
                      <div>
                        <p style={{ fontSize: '13px', color: '#d4d4d8', lineHeight: 1.5, margin: '0 0 12px 0', background: '#09090b', padding: '10px 12px', borderRadius: '6px' }}>
                          {photo.ai_analysis.caption || "생성된 캡션이 없습니다."}
                        </p>
                        
                        {/* Keyword Tags */}
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
                          {photo.ai_analysis.tags.map((tag, idx) => (
                            <span
                              key={idx}
                              onClick={() => handleTagClick(tag)}
                              style={{ background: '#27272a', color: '#e4e4e7', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
                            >
                              #{tag}
                            </span>
                          ))}
                        </div>

                        {/* Aesthetic Tags */}
                        {photo.ai_analysis.aesthetic_tags && photo.ai_analysis.aesthetic_tags.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
                            {photo.ai_analysis.aesthetic_tags.map((tag, idx) => (
                              <span
                                key={idx}
                                style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.3)', padding: '3px 8px', borderRadius: '4px', fontSize: '11px' }}
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <textarea
                          value={captionEdit}
                          onChange={(e) => setCaptionEdit(e.target.value)}
                          style={{ background: '#09090b', border: '1px solid #3f3f46', color: '#fff', padding: '8px', borderRadius: '4px', fontSize: '13px', minHeight: '80px', width: '100%', boxSizing: 'border-box' }}
                        />
                        <input
                          type="text"
                          value={tagsEdit.join(', ')}
                          onChange={(e) => setTagsEdit(e.target.value.split(',').map(t => t.trim()).filter(Boolean))}
                          placeholder="태그 (쉼표로 구분)"
                          style={{ background: '#09090b', border: '1px solid #3f3f46', color: '#fff', padding: '8px', borderRadius: '4px', fontSize: '12px', width: '100%', boxSizing: 'border-box' }}
                        />
                      </div>
                    )}
                  </div>

                  {/* AI Critique Component */}
                  <PhotoCritiqueView
                    critique={critique}
                    loadingCritique={loadingCritique}
                    onRequestCritique={handleRequestCritique}
                  />
                </>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
