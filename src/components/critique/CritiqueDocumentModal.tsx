import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Copy, 
  Check, 
  Printer, 
  ExternalLink, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  Camera, 
  FileText, 
  Calendar, 
  Sparkles,
  Info,
  Loader2
} from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { usePhotoDetailQuery } from '../../hooks/usePhotoDetailQuery';
import { api } from '../../services/api';
import { CritiqueContentRenderer } from './CritiqueContentRenderer';

export const CritiqueDocumentModal: React.FC = () => {
  const { critiqueDocumentPhotoId, closeCritiqueDocument } = useAppStore();
  const { data: photo, isLoading } = usePhotoDetailQuery(critiqueDocumentPhotoId);

  const [copied, setCopied] = useState(false);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imgError, setImgError] = useState(false);

  // Reset zoom & pan when photo changes
  useEffect(() => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
    setImgError(false);
  }, [critiqueDocumentPhotoId]);

  // Keyboard shortcut: ESC to close
  useEffect(() => {
    if (!critiqueDocumentPhotoId) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeCritiqueDocument();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [critiqueDocumentPhotoId, closeCritiqueDocument]);

  if (!critiqueDocumentPhotoId) return null;

  const critiqueText = photo?.ai_analysis?.critique || '';
  const thumbUrl = api.getPhotoThumbnailUrl(critiqueDocumentPhotoId);
  const originalUrl = `${api.getPhotoOriginalUrl(critiqueDocumentPhotoId)}?raw=true`;
  const imageUrl = imgError ? thumbUrl : originalUrl;

  const meta = photo?.metadata;
  const formattedDate = photo?.ai_analysis?.critique_updated_at
    ? new Date(photo.ai_analysis.critique_updated_at).toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    : meta?.capture_date
    ? new Date(meta.capture_date).toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    : null;

  // Zoom / Pan handlers
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      setScale((prev) => Math.min(prev + 0.2, 3.5));
    } else {
      setScale((prev) => {
        const next = Math.max(prev - 0.2, 0.6);
        if (next === 1) setPosition({ x: 0, y: 0 });
        return next;
      });
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (scale <= 1 && e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleResetZoom = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  const handleCopyText = () => {
    if (!critiqueText) return;
    navigator.clipboard.writeText(critiqueText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  const handlePopout = async () => {
    try {
      // Attempt Tauri v2 WebviewWindow pop-out
      const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow');
      const winLabel = `critique-doc-${critiqueDocumentPhotoId.slice(0, 8)}`;
      const existing = await WebviewWindow.getByLabel(winLabel);
      if (existing) {
        await existing.setFocus();
        return;
      }

      new WebviewWindow(winLabel, {
        url: `/?popout=critique&photoId=${critiqueDocumentPhotoId}`,
        title: `AI 사진 비평 - ${photo?.file_name || '문서 뷰'}`,
        width: 1200,
        height: 840,
        resizable: true,
        decorations: true
      });
    } catch {
      // Fallback: browser popup window
      window.open(
        `/?popout=critique&photoId=${critiqueDocumentPhotoId}`,
        '_blank',
        'width=1200,height=840,resizable=yes,scrollbars=yes'
      );
    }
  };

  return (
    <AnimatePresence>
      <div
        id="critique-document-modal"
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(4, 4, 6, 0.85)',
          backdropFilter: 'blur(16px)',
          padding: '24px',
          boxSizing: 'border-box'
        }}
        onClick={(e) => {
          if (e.target === e.currentTarget) closeCritiqueDocument();
        }}
      >
        {/* Print Stylesheet */}
        <style>{`
          @media print {
            body * {
              visibility: hidden;
            }
            #critique-document-modal,
            #critique-document-modal * {
              visibility: visible;
            }
            #critique-document-modal {
              position: absolute !important;
              inset: 0 !important;
              background: #fff !important;
              padding: 0 !important;
            }
            .no-print {
              display: none !important;
            }
            .print-paper {
              background: #fff !important;
              color: #111 !important;
              box-shadow: none !important;
              border: none !important;
            }
            .print-paper * {
              color: #111 !important;
              background: transparent !important;
              border-color: #ddd !important;
            }
          }
        `}</style>

        {/* Modal Window Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 15 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          style={{
            width: '100%',
            maxWidth: '1600px',
            height: '92vh',
            maxHeight: '1000px',
            backgroundColor: '#0e0e11',
            borderRadius: '20px',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.7), 0 0 40px rgba(168, 85, 247, 0.12)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Top Window Header Toolbar */}
          <header
            className="no-print"
            style={{
              padding: '14px 24px',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              backgroundColor: 'rgba(20, 20, 24, 0.95)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px'
            }}
          >
            {/* Left Title & Status */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}>
                <FileText size={17} color="#fff" />
              </div>
              <div style={{ overflow: 'hidden' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h2 style={{
                    margin: 0,
                    fontSize: '15px',
                    fontWeight: 700,
                    color: '#f4f4f5',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {photo?.file_name || '사진 비평 문서'}
                  </h2>
                  <span style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '2px 7px',
                    borderRadius: '6px',
                    background: 'rgba(168, 85, 247, 0.15)',
                    color: '#c084fc',
                    border: '1px solid rgba(168, 85, 247, 0.3)',
                    flexShrink: 0
                  }}>
                    리포트 뷰
                  </span>
                </div>
                {formattedDate && (
                  <span style={{ fontSize: '11px', color: '#71717a', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                    <Calendar size={11} /> {formattedDate}
                  </span>
                )}
              </div>
            </div>

            {/* Right Action Tools */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={handleCopyText}
                disabled={!critiqueText}
                style={{
                  background: copied ? 'rgba(74, 222, 128, 0.15)' : 'rgba(255, 255, 255, 0.06)',
                  border: `1px solid ${copied ? '#4ade80' : 'rgba(255, 255, 255, 0.12)'}`,
                  color: copied ? '#4ade80' : '#d4d4d8',
                  padding: '7px 12px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: critiqueText ? 'pointer' : 'not-allowed',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.2s ease'
                }}
                title="비평 전문 클립보드 복사"
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                <span>{copied ? '복사 완료!' : '텍스트 복사'}</span>
              </button>

              <button
                onClick={handlePrint}
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  color: '#d4d4d8',
                  padding: '7px 12px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
                title="인쇄 또는 PDF 저장"
              >
                <Printer size={14} />
                <span>인쇄 / PDF</span>
              </button>

              <button
                onClick={handlePopout}
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  color: '#d4d4d8',
                  padding: '7px 12px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
                title="별도 독립 윈도우로 분리"
              >
                <ExternalLink size={14} />
                <span>새 창으로 분리</span>
              </button>

              <div style={{ width: '1px', height: '20px', backgroundColor: 'rgba(255, 255, 255, 0.1)', margin: '0 4px' }} />

              <button
                onClick={closeCritiqueDocument}
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  color: '#a1a1aa',
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  transition: 'background 0.2s ease, color 0.2s ease'
                }}
                title="닫기 (ESC)"
              >
                <X size={16} />
              </button>
            </div>
          </header>

          {/* Body Split Area (Left: Photo / Right: Document) */}
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
            {/* Left Photo Inspector (45%) */}
            <div
              className="no-print"
              style={{
                flex: '0 0 46%',
                backgroundColor: '#060608',
                borderRight: '1px solid rgba(255, 255, 255, 0.08)',
                position: 'relative',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                userSelect: 'none'
              }}
            >
              {/* Photo Canvas Container */}
              <div
                style={{
                  flex: 1,
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden',
                  cursor: scale > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default'
                }}
                onWheel={handleWheel}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onDoubleClick={handleResetZoom}
              >
                <img
                  src={imageUrl}
                  alt={photo?.file_name}
                  onError={() => setImgError(true)}
                  draggable={false}
                  style={{
                    maxWidth: '92%',
                    maxHeight: '92%',
                    objectFit: 'contain',
                    transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
                    transformOrigin: 'center center',
                    transition: isDragging ? 'none' : 'transform 0.15s ease-out',
                    boxShadow: '0 10px 40px rgba(0, 0, 0, 0.6)'
                  }}
                />

                {/* Floating Zoom Control Bar */}
                <div
                  style={{
                    position: 'absolute',
                    top: '16px',
                    left: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    background: 'rgba(18, 18, 22, 0.85)',
                    backdropFilter: 'blur(8px)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '10px',
                    padding: '4px 8px',
                    zIndex: 10
                  }}
                >
                  <button
                    onClick={() => setScale((prev) => Math.max(prev - 0.2, 0.6))}
                    style={{ background: 'none', border: 'none', color: '#a1a1aa', cursor: 'pointer', padding: '4px' }}
                    title="축소"
                  >
                    <ZoomOut size={15} />
                  </button>
                  <span style={{ fontSize: '11px', color: '#fff', fontWeight: 600, minWidth: '38px', textAlign: 'center' }}>
                    {Math.round(scale * 100)}%
                  </span>
                  <button
                    onClick={() => setScale((prev) => Math.min(prev + 0.2, 3.5))}
                    style={{ background: 'none', border: 'none', color: '#a1a1aa', cursor: 'pointer', padding: '4px' }}
                    title="확대"
                  >
                    <ZoomIn size={15} />
                  </button>
                  {scale !== 1 && (
                    <button
                      onClick={handleResetZoom}
                      style={{ background: 'none', border: 'none', color: '#c084fc', cursor: 'pointer', padding: '4px' }}
                      title="줌 리셋"
                    >
                      <RotateCcw size={13} />
                    </button>
                  )}
                </div>
              </div>

              {/* Bottom EXIF Chips Overlay */}
              <div
                style={{
                  padding: '12px 18px',
                  backgroundColor: 'rgba(14, 14, 18, 0.95)',
                  borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '11.5px',
                  color: '#a1a1aa'
                }}
              >
                {meta?.camera_model && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#e4e4e7', fontWeight: 500 }}>
                    <Camera size={13} color="#c084fc" />
                    <span>{meta.camera_model}</span>
                  </div>
                )}
                {meta?.lens_model && (
                  <span style={{ color: '#71717a' }}>• {meta.lens_model}</span>
                )}
                <div style={{ display: 'flex', gap: '6px', marginLeft: 'auto' }}>
                  {meta?.focal_length && (
                    <span style={{ background: 'rgba(255, 255, 255, 0.06)', padding: '2px 7px', borderRadius: '4px', color: '#fff' }}>
                      {meta.focal_length}mm
                    </span>
                  )}
                  {meta?.f_number && (
                    <span style={{ background: 'rgba(255, 255, 255, 0.06)', padding: '2px 7px', borderRadius: '4px', color: '#fff' }}>
                      f/{meta.f_number}
                    </span>
                  )}
                  {meta?.shutter_speed && (
                    <span style={{ background: 'rgba(255, 255, 255, 0.06)', padding: '2px 7px', borderRadius: '4px', color: '#fff' }}>
                      {meta.shutter_speed}s
                    </span>
                  )}
                  {meta?.iso && (
                    <span style={{ background: 'rgba(255, 255, 255, 0.06)', padding: '2px 7px', borderRadius: '4px', color: '#fff' }}>
                      ISO {meta.iso}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Right Critique Document Paper (54%) */}
            <div
              className="print-paper"
              style={{
                flex: '1 1 54%',
                backgroundColor: '#111115',
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column'
              }}
            >
              <div
                style={{
                  maxWidth: '820px',
                  width: '100%',
                  margin: '0 auto',
                  padding: '36px 40px 60px 40px',
                  boxSizing: 'border-box'
                }}
              >
                {/* Document Title Header */}
                <div style={{ marginBottom: '28px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '22px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <Sparkles size={16} color="#c084fc" />
                    <span style={{ fontSize: '12px', fontWeight: 700, color: '#c084fc', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                      Focal Node · AI Photo Critique Report
                    </span>
                  </div>

                  <h1 style={{
                    margin: '0 0 10px 0',
                    fontSize: '24px',
                    fontWeight: 800,
                    color: '#fff',
                    letterSpacing: '-0.02em',
                    lineHeight: '1.3'
                  }}>
                    {photo?.file_name} 심층 미학 평론
                  </h1>

                  {photo?.ai_analysis?.caption && (
                    <p style={{
                      margin: '12px 0 0 0',
                      fontSize: '13.5px',
                      color: '#a1a1aa',
                      lineHeight: '1.65',
                      fontStyle: 'italic',
                      borderLeft: '3px solid #a855f7',
                      paddingLeft: '12px'
                    }}>
                      "{photo.ai_analysis.caption}"
                    </p>
                  )}
                </div>

                {/* Content Renderer or Empty State */}
                {isLoading ? (
                  <div style={{ padding: '60px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#a1a1aa' }}>
                    <Loader2 size={24} className="spin" color="#c084fc" style={{ marginBottom: '12px' }} />
                    <p style={{ margin: 0, fontSize: '14px' }}>비평 데이터를 불러오는 중입니다...</p>
                  </div>
                ) : critiqueText ? (
                  <CritiqueContentRenderer content={critiqueText} mode="document" />
                ) : (
                  <div style={{
                    padding: '60px 20px',
                    textAlign: 'center',
                    background: 'rgba(255, 255, 255, 0.03)',
                    borderRadius: '16px',
                    border: '1px dashed rgba(255, 255, 255, 0.1)'
                  }}>
                    <Info size={32} color="#71717a" style={{ marginBottom: '12px' }} />
                    <h4 style={{ margin: '0 0 8px 0', color: '#f4f4f5', fontSize: '16px' }}>
                      아직 생성된 비평이 없습니다
                    </h4>
                    <p style={{ margin: 0, color: '#71717a', fontSize: '13px' }}>
                      우측 패널에서 'AI 비평 생성'을 요청하시면 전문가 평론이 이곳에 기록됩니다.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
