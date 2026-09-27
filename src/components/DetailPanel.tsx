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
    handleCancelCritique,
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
              backgroundColor: 'rgba(0, 0, 0, 0.7)', backdropFilter: 'blur(6px)', zIndex: 40
            }}
          />

          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 220 }}
            style={{
              position: 'fixed', top: 0, right: 0, bottom: 0, width: '420px',
              backgroundColor: 'var(--bg-surface)', borderLeft: '1px solid var(--border-subtle)',
              color: 'var(--text-primary)', zIndex: 50, display: 'flex', flexDirection: 'column',
              boxShadow: '-16px 0 36px rgba(0,0,0,0.75)'
            }}
          >
            {/* Panel Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px', borderBottom: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--accent-focal)' }} />
                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, letterSpacing: '-0.01em' }}>사진 상세 정보</h3>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {photo && (
                  <button
                    onClick={handleToggleFavorite}
                    style={{ background: 'none', border: 'none', color: photo.is_favorite ? 'var(--accent-focal)' : 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}
                    title={photo.is_favorite ? "즐겨찾기 해제" : "즐겨찾기 추가"}
                  >
                    <Heart size={18} fill={photo.is_favorite ? 'var(--accent-focal)' : 'none'} />
                  </button>
                )}
                <button
                  onClick={() => setSelectedPhotoId(null)}
                  style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Panel Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '18px' }}>
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
                      borderRadius: '6px',
                      overflow: 'hidden',
                      backgroundColor: 'var(--bg-canvas)',
                      marginBottom: '16px',
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      maxHeight: '260px',
                      position: 'relative',
                      cursor: 'zoom-in',
                      border: '1px solid var(--border-subtle)'
                    }}
                    title="전체화면 뷰어 (Space / Enter)"
                  >
                    <img
                      src={api.getPhotoThumbnailUrl(photo.id)}
                      alt={photo.file_name}
                      style={{ maxWidth: '100%', maxHeight: '260px', objectFit: 'contain', display: 'block' }}
                    />
                    <motion.div
                      variants={{
                        rest: { opacity: 0 },
                        hover: { opacity: 1 }
                      }}
                      transition={{ duration: 0.15 }}
                      style={{
                        position: 'absolute',
                        top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: 'rgba(9, 9, 11, 0.65)',
                        backdropFilter: 'blur(3px)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#fff',
                        gap: '6px',
                        pointerEvents: 'none'
                      }}
                    >
                      <Maximize2 size={22} color="var(--accent-focal)" />
                      <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>전체화면으로 보기</span>
                    </motion.div>
                  </motion.div>

                  {/* File Info */}
                  <div style={{ marginBottom: '18px' }}>
                    <h4 style={{ margin: '0 0 6px 0', fontSize: '14px', fontWeight: 600, wordBreak: 'break-all' }}>{photo.file_name}</h4>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                      {[
                        { label: '해상도:', value: `${photo.metadata.width} × ${photo.metadata.height}` },
                        { label: '색상 공간:', value: photo.metadata.color_space },
                      ].map((item, idx) => (
                        <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ flexShrink: 0, whiteSpace: 'nowrap' }}>{item.label}</span>
                          <span className="font-mono" style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>{item.value}</span>
                        </div>
                      ))}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                        <span style={{ flexShrink: 0, whiteSpace: 'nowrap' }}>파일 위치:</span>
                        <button
                          onClick={handleReveal}
                          style={{
                            background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer',
                            padding: 0, fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px',
                            textDecoration: 'underline', whiteSpace: 'nowrap'
                          }}
                        >
                          <FolderOpen size={11} style={{ flexShrink: 0 }} /> Finder에서 보기
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* EXIF Metadata */}
                  <div style={{ marginBottom: '18px' }}>
                    <h4 style={{ margin: '0 0 8px 0', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      EXIF 메타데이터
                    </h4>
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
                    onCancelCritique={handleCancelCritique}
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
