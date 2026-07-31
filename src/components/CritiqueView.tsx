import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sparkles, 
  Search, 
  Trash2, 
  Copy, 
  Check, 
  Camera, 
  Calendar, 
  Eye, 
  ExternalLink, 
  Loader2, 
  FileText,
  Maximize2
} from 'lucide-react';
import { api, CritiqueItem } from '../services/api';
import { useAppStore } from '../store/useAppStore';

export const CritiqueView: React.FC = () => {
  const queryClient = useQueryClient();
  const { apiPort, setSelectedPhotoId, setActiveTab, openFullscreen } = useAppStore();
  const [filterQuery, setFilterQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const { data: critiques = [], isLoading } = useQuery<CritiqueItem[]>({
    queryKey: ['critiques'],
    queryFn: () => api.getCritiques(),
    enabled: !!apiPort,
  });

  const deleteMutation = useMutation({
    mutationFn: (photoId: string) => api.deleteCritique(photoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['critiques'] });
    },
  });

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredCritiques = critiques.filter((item) => {
    if (!filterQuery.trim()) return true;
    const q = filterQuery.toLowerCase();
    return (
      item.file_name.toLowerCase().includes(q) ||
      item.critique.toLowerCase().includes(q) ||
      (item.camera_model && item.camera_model.toLowerCase().includes(q)) ||
      (item.lens_model && item.lens_model.toLowerCase().includes(q))
    );
  });

  if (isLoading) {
    return (
      <div style={{
        flex: 1,
        height: '100vh',
        backgroundColor: '#0c0c0e',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#a1a1aa'
      }}>
        <Loader2 size={36} className="spin" style={{ color: '#c084fc', marginBottom: '16px' }} />
        <p style={{ fontSize: '15px', fontWeight: 500 }}>AI 비평 목록을 불러오는 중...</p>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          .spin { animation: spin 1s linear infinite; }
        `}</style>
      </div>
    );
  }

  return (
    <div style={{
      flex: 1,
      height: '100vh',
      backgroundColor: '#0c0c0e',
      color: '#f4f4f5',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      boxSizing: 'border-box'
    }}>
      {/* Header */}
      <header style={{
        padding: '24px 32px 18px 32px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        background: 'linear-gradient(180deg, rgba(24, 24, 27, 0.8) 0%, rgba(12, 12, 14, 0.95) 100%)',
        backdropFilter: 'blur(12px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '20px',
        zIndex: 10
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 20px rgba(168, 85, 247, 0.35)'
          }}>
            <Sparkles size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 style={{ fontSize: '20px', fontWeight: 700, margin: 0, color: '#fff', letterSpacing: '-0.02em' }}>
                AI 사진 비평 모아보기
              </h1>
              <span style={{
                background: 'rgba(168, 85, 247, 0.15)',
                color: '#c084fc',
                border: '1px solid rgba(168, 85, 247, 0.3)',
                padding: '2px 9px',
                borderRadius: '12px',
                fontSize: '12px',
                fontWeight: 600
              }}>
                {critiques.length}개의 비평
              </span>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#a1a1aa' }}>
              Gemma VLM이 분석한 사진의 구도, 조명, 색감 피드백 보관함
            </p>
          </div>
        </div>

        {/* Filter Input */}
        {critiques.length > 0 && (
          <div style={{ position: 'relative', width: '280px' }}>
            <Search size={16} color="#71717a" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="비평 내용 또는 파일명 검색..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              style={{
                width: '100%',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '10px',
                padding: '8px 12px 8px 36px',
                color: '#fff',
                fontSize: '13px',
                outline: 'none',
                boxSizing: 'border-box',
                transition: 'all 0.2s ease'
              }}
            />
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '28px 32px',
        boxSizing: 'border-box'
      }}>
        {critiques.length === 0 ? (
          /* Empty State */
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            style={{
              height: '100%',
              minHeight: '400px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              padding: '40px'
            }}
          >
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{ repeat: Infinity, duration: 3, ease: 'easeInOut' }}
              style={{
                width: '72px',
                height: '72px',
                borderRadius: '24px',
                background: 'rgba(168, 85, 247, 0.1)',
                border: '1px solid rgba(168, 85, 247, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '20px',
                boxShadow: '0 0 30px rgba(168, 85, 247, 0.15)'
              }}
            >
              <Sparkles size={34} color="#c084fc" />
            </motion.div>
            <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#f4f4f5', margin: '0 0 8px 0' }}>
              아직 작성된 AI 비평이 없습니다
            </h3>
            <p style={{ fontSize: '14px', color: '#a1a1aa', maxWidth: '440px', lineHeight: 1.6, margin: '0 0 24px 0' }}>
              갤러리에서 마음에 드는 사진을 선택하고 우측 상세 패널에서 <strong style={{ color: '#c084fc' }}>'AI 비평 생성'</strong>을 누르면,
              Gemma VLM 비전 모델이 구도와 색감에 대해 남겨준 전문 비평이 이곳에 모아집니다.
            </p>
            <motion.button
              onClick={() => setActiveTab('gallery')}
              whileHover={{ scale: 1.04, boxShadow: '0 4px 20px rgba(168, 85, 247, 0.4)' }}
              whileTap={{ scale: 0.97 }}
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #7c3aed 100%)',
                color: '#fff',
                border: 'none',
                padding: '10px 22px',
                borderRadius: '10px',
                fontSize: '14px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <FileText size={16} /> 갤러리로 이동하여 비평 받기
            </motion.button>
          </motion.div>
        ) : filteredCritiques.length === 0 ? (
          /* Filter No Results */
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#71717a' }}>
            <Search size={32} style={{ marginBottom: '12px', opacity: 0.5 }} />
            <p style={{ fontSize: '15px', margin: 0 }}>'{filterQuery}' 검색 결과와 일치하는 비평이 없습니다.</p>
          </div>
        ) : (
          /* Critiques Grid */
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))',
            gap: '24px',
            maxWidth: '1600px',
            margin: '0 auto'
          }}>
            <AnimatePresence>
              {filteredCritiques.map((item, index) => {
                const thumbUrl = `http://127.0.0.1:${apiPort}/api/photos/${item.photo_id}/thumbnail`;
                const formattedDate = item.critique_updated_at 
                  ? new Date(item.critique_updated_at).toLocaleDateString('ko-KR', {
                      year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
                    })
                  : null;

                return (
                  <motion.div
                    key={item.photo_id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.3, delay: Math.min(index * 0.05, 0.3) }}
                    style={{
                      backgroundColor: 'rgba(24, 24, 27, 0.7)',
                      borderRadius: '16px',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      overflow: 'hidden',
                      display: 'flex',
                      flexDirection: 'column',
                      boxShadow: '0 8px 30px rgba(0, 0, 0, 0.3)',
                      transition: 'border-color 0.2s ease, box-shadow 0.2s ease'
                    }}
                    whileHover={{
                      borderColor: 'rgba(168, 85, 247, 0.3)',
                      boxShadow: '0 12px 36px rgba(168, 85, 247, 0.12)'
                    }}
                  >
                    {/* Top Thumbnail & Photo Info Bar */}
                    <div style={{
                      display: 'flex',
                      height: '140px',
                      background: '#121215',
                      borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                      position: 'relative'
                    }}>
                      <div 
                        onClick={() => setSelectedPhotoId(item.photo_id)}
                        style={{
                          width: '140px',
                          height: '140px',
                          flexShrink: 0,
                          cursor: 'pointer',
                          position: 'relative',
                          overflow: 'hidden',
                          backgroundColor: '#18181b'
                        }}
                      >
                        <img
                          src={thumbUrl}
                          alt={item.file_name}
                          style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover',
                            transition: 'transform 0.3s ease'
                          }}
                        />
                        <div style={{
                          position: 'absolute',
                          inset: 0,
                          background: 'rgba(0,0,0,0.3)',
                          opacity: 0,
                          transition: 'opacity 0.2s ease',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '8px'
                        }}
                        className="thumb-overlay"
                        >
                          <Eye size={20} color="#fff" />
                        </div>
                      </div>

                      <div style={{
                        flex: 1,
                        padding: '14px 16px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        overflow: 'hidden'
                      }}>
                        <div>
                          <h4 
                            onClick={() => setSelectedPhotoId(item.photo_id)}
                            style={{
                              margin: '0 0 6px 0',
                              fontSize: '14px',
                              fontWeight: 600,
                              color: '#f4f4f5',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              cursor: 'pointer'
                            }}
                            title={item.file_name}
                          >
                            {item.file_name}
                          </h4>

                          {/* Metadata Tags */}
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '11px', color: '#a1a1aa' }}>
                            {item.camera_model && (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                                <Camera size={12} color="#c084fc" />
                                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                  {item.camera_model} {item.lens_model ? `• ${item.lens_model}` : ''}
                                </span>
                              </div>
                            )}

                            {(item.f_number || item.shutter_speed || item.iso) && (
                              <div style={{ display: 'flex', gap: '8px', color: '#71717a' }}>
                                {item.f_number && <span>f/{item.f_number}</span>}
                                {item.shutter_speed && <span>{item.shutter_speed}s</span>}
                                {item.iso && <span>ISO {item.iso}</span>}
                              </div>
                            )}
                          </div>
                        </div>

                        {formattedDate && (
                          <div style={{ fontSize: '11px', color: '#71717a', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Calendar size={11} />
                            <span>{formattedDate} 생성</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Critique Text Box */}
                    <div style={{
                      padding: '18px 20px',
                      flex: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '16px'
                    }}>
                      <div style={{
                        fontSize: '13px',
                        lineHeight: '1.65',
                        color: '#e4e4e7',
                        whiteSpace: 'pre-line',
                        maxHeight: '180px',
                        overflowY: 'auto',
                        paddingRight: '6px'
                      }}>
                        {item.critique}
                      </div>

                      {/* Card Action Footer */}
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        paddingTop: '12px',
                        borderTop: '1px solid rgba(255, 255, 255, 0.06)'
                      }}>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            onClick={() => setSelectedPhotoId(item.photo_id)}
                            style={{
                              background: 'rgba(255, 255, 255, 0.06)',
                              border: '1px solid rgba(255, 255, 255, 0.1)',
                              color: '#f4f4f5',
                              padding: '5px 11px',
                              borderRadius: '6px',
                              fontSize: '12px',
                              fontWeight: 500,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '5px'
                            }}
                          >
                            <ExternalLink size={12} /> 상세 패널
                          </button>
                          <button
                            onClick={() => openFullscreen(item.photo_id)}
                            style={{
                              background: 'rgba(255, 255, 255, 0.06)',
                              border: '1px solid rgba(255, 255, 255, 0.1)',
                              color: '#f4f4f5',
                              padding: '5px 11px',
                              borderRadius: '6px',
                              fontSize: '12px',
                              fontWeight: 500,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '5px'
                            }}
                          >
                            <Maximize2 size={12} /> 원본 보기
                          </button>
                        </div>

                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button
                            onClick={() => handleCopy(item.photo_id, item.critique)}
                            style={{
                              background: copiedId === item.photo_id ? 'rgba(74, 222, 128, 0.15)' : 'transparent',
                              border: 'none',
                              color: copiedId === item.photo_id ? '#4ade80' : '#a1a1aa',
                              padding: '6px',
                              borderRadius: '6px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center'
                            }}
                            title="비평 텍스트 복사"
                          >
                            {copiedId === item.photo_id ? <Check size={14} /> : <Copy size={14} />}
                          </button>
                          <button
                            onClick={() => {
                              if (confirm(`'${item.file_name}'의 저장된 비평을 삭제하시겠습니까?`)) {
                                deleteMutation.mutate(item.photo_id);
                              }
                            }}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: '#ef4444',
                              padding: '6px',
                              borderRadius: '6px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center'
                            }}
                            title="비평 삭제"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>

      <style>{`
        .thumb-overlay:hover {
          opacity: 1 !important;
        }
      `}</style>
    </div>
  );
};
