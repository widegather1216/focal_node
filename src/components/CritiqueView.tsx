import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Search, Wand2, FileText, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import { CritiqueItem, CritiqueSummaryResponse } from '../types/critique';
import { useAppStore } from '../store/useAppStore';
import { CritiqueSummaryCard } from './critique/CritiqueSummaryCard';
import { CritiqueCard } from './critique/CritiqueCard';
import { LoadingSpinner } from './common/LoadingSpinner';

export const CritiqueView: React.FC = () => {
  const queryClient = useQueryClient();
  const { apiPort, setSelectedPhotoId, setActiveTab, openFullscreen } = useAppStore();
  
  const [filterQuery, setFilterQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Summary State
  const [summaryData, setSummaryData] = useState<CritiqueSummaryResponse | null>(null);
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [copiedSummary, setCopiedSummary] = useState(false);
  const [isSummaryExpanded, setIsSummaryExpanded] = useState(true);

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

  const handleGenerateSummary = async () => {
    if (critiques.length === 0 || isGeneratingSummary) return;
    setIsGeneratingSummary(true);
    setSummaryError(null);
    setIsSummaryExpanded(true);
    try {
      const res = await api.getCritiqueSummary();
      setSummaryData(res);
    } catch (err: any) {
      console.error("Failed to generate critique summary:", err);
      setSummaryError(err.message || "종합 요약을 생성하는 도중 오류가 발생했습니다.");
    } finally {
      setIsGeneratingSummary(false);
    }
  };

  const handleCopySummary = () => {
    if (!summaryData?.summary) return;
    navigator.clipboard.writeText(summaryData.summary);
    setCopiedSummary(true);
    setTimeout(() => setCopiedSummary(false), 2000);
  };

  const filteredCritiques = useMemo(() => {
    if (!filterQuery.trim()) return critiques;
    const q = filterQuery.toLowerCase();
    return critiques.filter((item) => (
      item.file_name.toLowerCase().includes(q) ||
      item.critique.toLowerCase().includes(q) ||
      (item.camera_model && item.camera_model.toLowerCase().includes(q)) ||
      (item.lens_model && item.lens_model.toLowerCase().includes(q))
    ));
  }, [critiques, filterQuery]);

  if (isLoading) {
    return <LoadingSpinner fullScreen message="AI 비평 목록을 불러오는 중..." />;
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
        padding: '20px 32px',
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

        {/* Right Header Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {critiques.length > 0 && (
            <>
              <div style={{ position: 'relative', width: '240px' }}>
                <Search size={15} color="#71717a" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="text"
                  placeholder="비평 또는 파일명 검색..."
                  value={filterQuery}
                  onChange={(e) => setFilterQuery(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '10px',
                    padding: '8px 12px 8px 34px',
                    color: '#fff',
                    fontSize: '13px',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <motion.button
                onClick={handleGenerateSummary}
                disabled={isGeneratingSummary}
                whileHover={!isGeneratingSummary ? { scale: 1.03 } : {}}
                whileTap={!isGeneratingSummary ? { scale: 0.97 } : {}}
                style={{
                  background: 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
                  color: '#fff',
                  border: 'none',
                  padding: '9px 16px',
                  borderRadius: '10px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: isGeneratingSummary ? 'not-allowed' : 'pointer',
                  opacity: isGeneratingSummary ? 0.7 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: '0 4px 16px rgba(168, 85, 247, 0.3)'
                }}
              >
                {isGeneratingSummary ? (
                  <>
                    <Loader2 size={15} className="spin" />
                    <span>요약 분석 중...</span>
                  </>
                ) : (
                  <>
                    <Wand2 size={15} />
                    <span>종합 요약 생성</span>
                  </>
                )}
              </motion.button>
            </>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '28px 32px',
        boxSizing: 'border-box'
      }}>
        {/* Aggregated Critique Summary Card Section */}
        <AnimatePresence>
          <CritiqueSummaryCard
            isGeneratingSummary={isGeneratingSummary}
            summaryData={summaryData}
            summaryError={summaryError}
            copiedSummary={copiedSummary}
            isSummaryExpanded={isSummaryExpanded}
            totalCritiques={critiques.length}
            onCopySummary={handleCopySummary}
            onGenerateSummary={handleGenerateSummary}
            onToggleExpand={() => setIsSummaryExpanded(!isSummaryExpanded)}
            onCloseSummary={() => {
              setSummaryData(null);
              setSummaryError(null);
            }}
          />
        </AnimatePresence>

        {/* Critiques Grid or Empty States */}
        {critiques.length === 0 ? (
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
            <p style={{ fontSize: '14px', color: '#a1a1aa', maxWidth: '420px', margin: '0 0 24px 0', lineHeight: 1.6 }}>
              갤러리에서 원하는 사진을 클릭하여 우측 상세 정보 패널에서 AI 피드백을 요청해보세요!
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setActiveTab('gallery')}
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
                color: '#fff',
                border: 'none',
                padding: '10px 20px',
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
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#71717a' }}>
            <Search size={32} style={{ marginBottom: '12px', opacity: 0.5 }} />
            <p style={{ fontSize: '15px', margin: 0 }}>'{filterQuery}' 검색 결과와 일치하는 비평이 없습니다.</p>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))',
            gap: '24px',
            maxWidth: '1600px',
            margin: '0 auto'
          }}>
            <AnimatePresence>
              {filteredCritiques.map((item, index) => (
                <CritiqueCard
                  key={item.photo_id}
                  item={item}
                  index={index}
                  copiedId={copiedId}
                  onSelectPhoto={setSelectedPhotoId}
                  onOpenFullscreen={openFullscreen}
                  onCopy={handleCopy}
                  onDelete={(id) => deleteMutation.mutate(id)}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
};
