import { motion, AnimatePresence } from 'framer-motion';
import { X, FolderOpen, Heart, Maximize2 } from 'lucide-react';
import { api } from '../services/api';
import { usePhotoDetail } from '../hooks/usePhotoDetail';
import { useAppStore } from '../store/useAppStore';
import { PhotoExifView } from './detail/PhotoExifView';
import { PhotoCritiqueView } from './detail/PhotoCritiqueView';
import { PhotoAiAnalysisView } from './detail/PhotoAiAnalysisView';
import { LoadingSpinner } from './common/LoadingSpinner';

export function DetailPanel() {
  const openFullscreen = useAppStore(state => state.openFullscreen);
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
    handleDeleteCritique,
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
              {loading && <LoadingSpinner message="사진 정보를 불러오는 중입니다..." />}

              {!loading && photo && (
                <>
                  {/* Image Preview */}
                  <motion.div
                    initial="rest"
                    whileHover="hover"
                    animate="rest"
                    onClick={() => openFullscreen(photo.id)}
                    style={{
                      borderRadius: '8px',
                      overflow: 'hidden',
                      backgroundColor: '#09090b',
                      marginBottom: '20px',
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      maxHeight: '280px',
                      position: 'relative',
                      cursor: 'zoom-in',
                      border: '1px solid #27272a'
                    }}
                    title="클릭하여 전체화면 보기"
                  >
                    <img
                      src={api.getPhotoThumbnailUrl(photo.id)}
                      alt={photo.file_name}
                      style={{ maxWidth: '100%', maxHeight: '280px', objectFit: 'contain', display: 'block' }}
                    />
                    <motion.div
                      variants={{
                        rest: { opacity: 0 },
                        hover: { opacity: 1 }
                      }}
                      transition={{ duration: 0.2 }}
                      style={{
                        position: 'absolute',
                        top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: 'rgba(0, 0, 0, 0.5)',
                        backdropFilter: 'blur(3px)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#fff',
                        gap: '8px',
                        pointerEvents: 'none'
                      }}
                    >
                      <Maximize2 size={26} color="#38bdf8" />
                      <span style={{ fontSize: '12px', fontWeight: 600, color: '#f4f4f5' }}>전체화면으로 보기</span>
                    </motion.div>
                  </motion.div>

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

                  {/* AI Analysis Component */}
                  <PhotoAiAnalysisView
                    aiAnalysis={photo.ai_analysis}
                    editing={editing}
                    reindexing={reindexing}
                    saving={saving}
                    captionEdit={captionEdit}
                    tagsEdit={tagsEdit}
                    setEditing={setEditing}
                    setCaptionEdit={setCaptionEdit}
                    setTagsEdit={setTagsEdit}
                    handleSave={handleSave}
                    handleReindex={handleReindex}
                    handleTagClick={handleTagClick}
                  />

                  {/* AI Critique Component */}
                  <PhotoCritiqueView
                    photoId={photo.id}
                    critique={critique}
                    loadingCritique={loadingCritique}
                    onRequestCritique={handleRequestCritique}
                    onDeleteCritique={handleDeleteCritique}
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
