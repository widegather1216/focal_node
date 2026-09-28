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
      backgroundColor: 'var(--bg-canvas)',
      color: 'var(--text-primary)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      boxSizing: 'border-box'
    }}>
      {/* Header */}
      <header style={{
        padding: '16px 28px',
        borderBottom: '1px solid var(--border-subtle)',
        backgroundColor: 'var(--bg-surface)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '20px',
        zIndex: 10
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Sparkles size={18} color="var(--accent-focal)" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '16px', fontWeight: 600, margin: 0, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
                AI 사진 비평 & 큐레이션
              </h1>
              <span className="font-mono" style={{
                background: 'var(--bg-card)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border-subtle)',
                padding: '2px 8px',
                borderRadius: '10px',
                fontSize: '11px',
                fontWeight: 500
              }}>
                {critiques.length} 컷
              </span>
            </div>
            <p style={{ margin: '2px 0 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>
              AI가 분석한 사진의 미학적 구도와 광학적 디테일 평론 보관함
            </p>
          </div>
        </div>

        {/* Right Header Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {critiques.length > 0 && (
            <>
              <div style={{ position: 'relative', width: '220px' }}>
                <Search size={13} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="text"
                  placeholder="비평 / 태그 검색..."
                  value={filterQuery}
                  onChange={(e) => setFilterQuery(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '6px 10px 6px 28px',
                    color: 'var(--text-primary)',
                    fontSize: '12px',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <motion.button
                onClick={handleGenerateSummary}
                disabled={isGeneratingSummary}
                whileHover={!isGeneratingSummary ? { scale: 1.02, backgroundColor: 'var(--bg-elevated)', borderColor: 'var(--border-active)' } : {}}
                whileTap={!isGeneratingSummary ? { scale: 0.98 } : {}}
                style={{
                  backgroundColor: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-subtle)',
                  padding: '7px 14px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: isGeneratingSummary ? 'not-allowed' : 'pointer',
                  opacity: isGeneratingSummary ? 0.6 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                  transition: 'all 0.15s ease'
                }}
              >
                {isGeneratingSummary ? (
                  <>
                    <Loader2 size={13} className="spin" color="var(--accent-focal)" style={{ flexShrink: 0 }} />
                    <span style={{ whiteSpace: 'nowrap' }}>요약 분석 중...</span>
                  </>
                ) : (
                  <>
                    <Wand2 size={13} color="var(--accent-focal)" style={{ flexShrink: 0 }} />
                    <span style={{ whiteSpace: 'nowrap' }}>종합 포트폴리오 요약</span>
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
        padding: '24px 28px',
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
            transition={{ duration: 0.3 }}
            style={{
              height: '100%',
              minHeight: '380px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              padding: '30px',
              userSelect: 'none'
            }}
          >
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '16px'
            }}>
              <Sparkles size={24} color="var(--accent-focal)" />
            </div>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 6px 0' }}>
              아직 작성된 AI 비평이 없습니다
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', maxWidth: '400px', margin: '0 0 20px 0', lineHeight: 1.5 }}>
              갤러리에서 원하는 사진을 선택한 후 우측 상세 패널에서 AI 사진 비평을 요청해 보세요.
            </p>
            <motion.button
              whileHover={{ scale: 1.02, backgroundColor: 'var(--bg-elevated)', borderColor: 'var(--border-active)' }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setActiveTab('gallery')}
              style={{
                backgroundColor: 'var(--bg-card)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-subtle)',
                padding: '8px 16px',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <FileText size={14} color="var(--text-secondary)" /> 갤러리로 이동하기
            </motion.button>
          </motion.div>
        ) : filteredCritiques.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
            <Search size={28} style={{ marginBottom: '10px', opacity: 0.5 }} />
            <p style={{ fontSize: '14px', margin: 0 }}>'{filterQuery}' 검색 결과와 일치하는 비평이 없습니다.</p>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
            gap: '16px',
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
