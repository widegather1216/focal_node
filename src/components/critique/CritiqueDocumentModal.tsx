import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import { usePhotoDetailQuery } from '../../hooks/usePhotoDetailQuery';
import { useModalZoomPan } from '../../hooks/useModalZoomPan';
import { api } from '../../services/api';
import { extractScoreboard, parseMarkdownToBlocks } from '../../utils/critiqueParser';
import { 
  exportCritiqueToMarkdown, 
  exportCritiqueToPdf, 
  revealSavedFile,
  ExportProgressState,
  CritiqueScores 
} from '../../utils/critiqueExporter';
import { CritiqueDocumentToolbar } from './CritiqueDocumentToolbar';
import { CritiqueDocumentPhotoViewer } from './CritiqueDocumentPhotoViewer';
import { CritiqueDocumentArticle } from './CritiqueDocumentArticle';
import { CritiqueExportProgressOverlay } from './CritiqueExportProgressOverlay';

interface CritiqueDocumentModalProps {
  isStandalone?: boolean;
}

export const CritiqueDocumentModal: React.FC<CritiqueDocumentModalProps> = ({ isStandalone = false }) => {
  const { critiqueDocumentPhotoId, closeCritiqueDocument } = useAppStore();
  const { data: photo, isLoading } = usePhotoDetailQuery(critiqueDocumentPhotoId);

  const [copied, setCopied] = useState(false);
  const [exported, setExported] = useState(false);
  const [isExportingMd, setIsExportingMd] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [pdfExported, setPdfExported] = useState(false);
  const [lastSavedPath, setLastSavedPath] = useState<string | null>(null);
  const [exportProgress, setExportProgress] = useState<ExportProgressState>({
    active: false,
    type: 'pdf',
    title: 'A4 비평 리포트 PDF 생성 중',
    step: '사진 및 그래픽 에셋 준비 중...',
    detail: '고해상도 인쇄를 위해 사진 이미지를 인라인으로 준비하고 있습니다.',
    percent: 0,
    savedPath: null
  });

  const [isMaximized, setIsMaximized] = useState(false);
  const [imgError, setImgError] = useState(false);
  const {
    scale,
    position,
    isDragging,
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleResetZoom,
    zoomIn,
    zoomOut,
  } = useModalZoomPan();

  // Check whether we are running in a dedicated popout desktop window
  const isPopout = useMemo(() => {
    if (isStandalone) return true;
    if (typeof window !== 'undefined') {
      const searchParams = new URLSearchParams(window.location.search);
      return searchParams.get('popout') === 'critique';
    }
    return false;
  }, [isStandalone]);

  const handleClose = useCallback(async () => {
    if (isPopout) {
      try {
        const { getCurrentWindow } = await import('@tauri-apps/api/window');
        await getCurrentWindow().close();
      } catch {
        window.close();
      }
    } else {
      closeCritiqueDocument();
    }
  }, [isPopout, closeCritiqueDocument]);

  // Keyboard shortcut listener (ESC / Cmd+W) — active only when modal is open or in popout window
  useEffect(() => {
    if (!critiqueDocumentPhotoId && !isPopout) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        handleClose();
      } else if ((e.metaKey || e.ctrlKey) && e.key === 'w') {
        e.preventDefault();
        handleClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [critiqueDocumentPhotoId, isPopout, handleClose]);

  // Reset transient viewer & export states when switching photos
  useEffect(() => {
    setImgError(false);
    setCopied(false);
    setExported(false);
    setPdfExported(false);
    setLastSavedPath(null);
    setExportProgress((prev) => (prev.active ? { ...prev, active: false } : prev));
    handleResetZoom();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [critiqueDocumentPhotoId]);

  // Window title update for standalone/popout mode
  useEffect(() => {
    if (isPopout && photo?.file_name) {
      document.title = `${photo.file_name} - AI 사진 비평 리포트 | Focal Node`;
    }
  }, [isPopout, photo?.file_name]);

  const critiqueText = photo?.ai_analysis?.critique || '';

  // Extract editorial masthead scores & summary (must run before conditional return to obey Rules of Hooks)
  const mastheadData = useMemo(() => {
    if (!critiqueText) return { scores: null, summary: null };
    const { scores: extractedScores, remainingText } = extractScoreboard(critiqueText);

    const normOverall = photo?.ai_analysis?.overall_score;
    const normIaa = photo?.ai_analysis?.iaa_score;
    const normIqa = photo?.ai_analysis?.iqa_score;
    const normIsta = photo?.ai_analysis?.ista_score;

    const hasNormalized =
      normOverall != null || normIaa != null || normIqa != null || normIsta != null;

    let scores: CritiqueScores | null = null;
    if (hasNormalized) {
      scores = {
        overall: normOverall != null ? Math.round(normOverall) : null,
        iaa: normIaa != null ? Math.round(normIaa) : null,
        iqa: normIqa != null ? Math.round(normIqa) : null,
        ista: normIsta != null ? Math.round(normIsta) : null,
      };
    } else {
      scores = extractedScores;
    }

    const blocks = parseMarkdownToBlocks(remainingText);
    const summaryBlock = blocks.find(b => b.type === 'executive_summary');
    const summary = summaryBlock && summaryBlock.type === 'executive_summary' ? summaryBlock.summary : null;

    return { scores, summary };
  }, [critiqueText, photo?.ai_analysis]);

  if (!critiqueDocumentPhotoId) return null;

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

  // Text copy handler
  const handleCopyText = async () => {
    if (!critiqueText) return;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(critiqueText);
      } else {
        const textArea = document.createElement('textarea');
        textArea.value = critiqueText;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.warn('Clipboard copy failed:', err);
    }
  };

  // Markdown export handler
  const handleExportMarkdown = async () => {
    if (!critiqueText || isExportingMd) return;
    setIsExportingMd(true);

    try {
      const result = await exportCritiqueToMarkdown(
        photo,
        critiqueText,
        formattedDate,
        mastheadData.scores
      );

      if (result.cancelled) {
        setIsExportingMd(false);
        return;
      }

      if (result.savedPath) {
        setLastSavedPath(result.savedPath);
      }

      setExported(true);
      setExportProgress({
        active: true,
        type: 'md',
        title: '마크다운 리포트 저장 완료',
        step: '마크다운 파일(.md) 저장 성공',
        detail: result.savedPath ? `저장 위치: ${result.savedPath}` : '다운로드 폴더에 마크다운 파일이 저장되었습니다.',
        percent: 100,
        savedPath: result.savedPath
      });

      setTimeout(() => {
        setExportProgress((prev) => ({ ...prev, active: false }));
      }, 2500);
      setTimeout(() => setExported(false), 3000);
    } catch (err) {
      console.error('Failed to export markdown:', err);
      alert('마크다운 파일 저장 중 오류가 발생했습니다.');
    } finally {
      setIsExportingMd(false);
    }
  };

  // PDF export handler
  const handleExportPdf = async () => {
    if (!critiqueText || isExportingPdf) return;
    setIsExportingPdf(true);
    setPdfExported(false);

    try {
      const result = await exportCritiqueToPdf(
        photo,
        critiqueText,
        imageUrl,
        thumbUrl,
        formattedDate,
        mastheadData.scores,
        (progress) => setExportProgress(progress)
      );

      if (result.cancelled) {
        setExportProgress((prev) => ({ ...prev, active: false }));
        setIsExportingPdf(false);
        return;
      }

      if (result.savedPath) {
        setLastSavedPath(result.savedPath);
      }

      setExportProgress({
        active: true,
        type: 'pdf',
        title: 'PDF 리포트 저장 완료',
        step: 'PDF 리포트 저장 완료!',
        detail: result.savedPath ? '파일이 성공적으로 저장되었습니다.' : '다운로드 폴더에 저장되었습니다.',
        percent: 100,
        savedPath: result.savedPath
      });
      setPdfExported(true);

      setTimeout(() => {
        setExportProgress((prev) => ({ ...prev, active: false }));
      }, 2500);
      setTimeout(() => setPdfExported(false), 4000);
    } catch (error) {
      console.error('Failed to generate PDF:', error);
      setExportProgress((prev) => ({ ...prev, active: false }));
      alert('PDF 생성 및 저장 중 오류가 발생했습니다.');
    } finally {
      setIsExportingPdf(false);
    }
  };

  // Popout handler
  const handlePopout = async () => {
    if (isPopout) return;
    try {
      const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow');
      const windowLabel = `critique-doc-${critiqueDocumentPhotoId || Date.now()}`;
      const webview = new WebviewWindow(windowLabel, {
        url: `/?popout=critique&photoId=${critiqueDocumentPhotoId}`,
        title: `${photo?.file_name || '사진'} - AI 비평 리포트 | Focal Node`,
        width: 1320,
        height: 880,
        minWidth: 960,
        minHeight: 640,
        center: true,
        resizable: true,
        decorations: true
      });

      webview.once('tauri://created', () => {
        closeCritiqueDocument();
      });
      webview.once('tauri://error', (e) => {
        console.warn('WebviewWindow creation failed, falling back to window.open:', e);
        window.open(
          `/?popout=critique&photoId=${critiqueDocumentPhotoId}`,
          '_blank',
          'width=1280,height=860,resizable=yes,scrollbars=yes'
        );
        closeCritiqueDocument();
      });
    } catch {
      window.open(
        `/?popout=critique&photoId=${critiqueDocumentPhotoId}`,
        '_blank',
        'width=1280,height=860,resizable=yes,scrollbars=yes'
      );
      closeCritiqueDocument();
    }
  };

  return (
    <AnimatePresence>
      <div
        id="critique-document-modal"
        style={{
          position: isPopout ? 'relative' : 'fixed',
          inset: 0,
          zIndex: 999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: isPopout ? '#0e0e11' : 'rgba(4, 4, 6, 0.85)',
          backdropFilter: isPopout ? 'none' : 'blur(16px)',
          padding: isPopout || isMaximized ? 0 : '24px',
          width: '100vw',
          height: '100vh',
          boxSizing: 'border-box'
        }}
        onClick={(e) => {
          if (!isPopout && e.target === e.currentTarget) handleClose();
        }}
      >
        {/* Print Stylesheet for Direct Print Fallback */}
        <style>{`
          @media print {
            body {
              background: #fff !important;
              color: #111 !important;
            }
            .no-print {
              display: none !important;
            }
            #critique-document-modal {
              position: static !important;
              padding: 0 !important;
              background: #fff !important;
            }
            .print-paper {
              background: #fff !important;
              color: #111 !important;
              box-shadow: none !important;
              border: none !important;
            }
            .print-paper h1,
            .print-paper h2,
            .print-paper h3,
            .print-paper h4,
            .print-paper strong,
            .print-paper th {
              color: #111827 !important;
            }
            .print-paper p,
            .print-paper li,
            .print-paper td,
            .print-paper em,
            .print-paper blockquote,
            .print-paper span:not(.font-mono) {
              color: #374151 !important;
            }
            .print-paper button {
              display: none !important;
            }
          }
        `}</style>

        {/* Modal Window Container */}
        <motion.div
          initial={{ opacity: 0, scale: isPopout ? 1 : 0.96, y: isPopout ? 0 : 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: isPopout ? 1 : 0.96, y: isPopout ? 0 : 15 }}
          transition={{ duration: 0.22, ease: 'easeOut' }}
          style={{
            width: '100%',
            maxWidth: isPopout || isMaximized ? '100%' : '1600px',
            height: isPopout || isMaximized ? '100%' : '92vh',
            maxHeight: isPopout || isMaximized ? '100vh' : '1000px',
            backgroundColor: '#0e0e11',
            borderRadius: isPopout || isMaximized ? 0 : '20px',
            border: isPopout || isMaximized ? 'none' : '1px solid rgba(255, 255, 255, 0.1)',
            boxShadow: isPopout || isMaximized ? 'none' : '0 25px 60px -15px rgba(0, 0, 0, 0.7), 0 0 40px rgba(225, 29, 72, 0.12)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            position: 'relative'
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Top Window Header Toolbar */}
          <CritiqueDocumentToolbar
            photo={photo}
            isPopout={isPopout}
            formattedDate={formattedDate}
            critiqueText={critiqueText}
            copied={copied}
            exported={exported}
            isExportingMd={isExportingMd}
            isExportingPdf={isExportingPdf}
            pdfExported={pdfExported}
            lastSavedPath={lastSavedPath}
            isMaximized={isMaximized}
            onCopyText={handleCopyText}
            onExportMarkdown={handleExportMarkdown}
            onExportPdf={handleExportPdf}
            onRevealFile={revealSavedFile}
            onPopout={handlePopout}
            onToggleMaximize={() => setIsMaximized((prev) => !prev)}
            onClose={handleClose}
          />

          {/* Body Split Area (Left: Photo / Right: Document) */}
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
            <CritiqueDocumentPhotoViewer
              photo={photo}
              imageUrl={imageUrl}
              scale={scale}
              position={position}
              isDragging={isDragging}
              onWheel={handleWheel}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onResetZoom={handleResetZoom}
              onZoomIn={zoomIn}
              onZoomOut={zoomOut}
              onImageError={() => setImgError(true)}
            />

            <CritiqueDocumentArticle
              photo={photo}
              isLoading={isLoading}
              critiqueText={critiqueText}
              mastheadData={mastheadData}
            />
          </div>

          {/* Export Generation Progress & Completion Modal Overlay */}
          <CritiqueExportProgressOverlay
            exportProgress={exportProgress}
            photoName={photo?.file_name}
            lastSavedPath={lastSavedPath}
            onRevealFile={revealSavedFile}
            onClose={() => setExportProgress((prev) => ({ ...prev, active: false }))}
          />
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
