import { useState, useEffect, useCallback, useMemo } from 'react';
import { useAppStore } from '../store/useAppStore';
import { usePhotoDetailQuery } from './usePhotoDetailQuery';
import { PhotoDetail } from '../types/photo';
import { useModalZoomPan } from './useModalZoomPan';
import { api } from '../services/api';
import { extractScoreboard, parseMarkdownToBlocks } from '../utils/critiqueParser';
import {
  exportCritiqueToMarkdown,
  exportCritiqueToPdf,
  ExportProgressState,
  CritiqueScores,
} from '../utils/critiqueExporter';

const INITIAL_EXPORT_PROGRESS: ExportProgressState = {
  active: false,
  type: 'pdf',
  title: 'A4 비평 리포트 PDF 생성 중',
  step: '사진 및 그래픽 에셋 준비 중...',
  detail: '고해상도 인쇄를 위해 사진 이미지를 인라인으로 준비하고 있습니다.',
  percent: 0,
  savedPath: null,
};

function buildMastheadSummary(photo: PhotoDetail | null | undefined, critiqueText: string): {
  scores: CritiqueScores | null;
  summary: string | null;
} {
  if (!critiqueText) return { scores: null, summary: null };
  const { scores: extractedScores, remainingText } = extractScoreboard(critiqueText);
  const analysis = photo?.ai_analysis;
  const hasNormalized =
    analysis?.overall_score != null ||
    analysis?.iaa_score != null ||
    analysis?.iqa_score != null ||
    analysis?.ista_score != null;

  const scores: CritiqueScores | null = hasNormalized
    ? {
        overall: analysis?.overall_score != null ? Math.round(analysis.overall_score) : null,
        iaa: analysis?.iaa_score != null ? Math.round(analysis.iaa_score) : null,
        iqa: analysis?.iqa_score != null ? Math.round(analysis.iqa_score) : null,
        ista: analysis?.ista_score != null ? Math.round(analysis.ista_score) : null,
      }
    : extractedScores;

  const blocks = parseMarkdownToBlocks(remainingText);
  const summaryBlock = blocks.find((block) => block.type === 'executive_summary');
  const summary = summaryBlock && summaryBlock.type === 'executive_summary' ? summaryBlock.summary : null;
  return { scores, summary };
}

function formatCritiqueDate(photo: PhotoDetail | null | undefined): string | null {
  if (photo?.ai_analysis?.critique_updated_at) {
    return new Date(photo.ai_analysis.critique_updated_at).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
  if (photo?.metadata?.capture_date) {
    return new Date(photo.metadata.capture_date).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }
  return null;
}

export function useCritiqueDocumentModal(isStandalone: boolean) {
  const { critiqueDocumentPhotoId, closeCritiqueDocument } = useAppStore();
  const { data: photo, isLoading } = usePhotoDetailQuery(critiqueDocumentPhotoId);

  const [copied, setCopied] = useState(false);
  const [exported, setExported] = useState(false);
  const [isExportingMd, setIsExportingMd] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [pdfExported, setPdfExported] = useState(false);
  const [lastSavedPath, setLastSavedPath] = useState<string | null>(null);
  const [exportProgress, setExportProgress] = useState<ExportProgressState>(INITIAL_EXPORT_PROGRESS);
  const [isMaximized, setIsMaximized] = useState(false);
  const [imgError, setImgError] = useState(false);

  const zoomPan = useModalZoomPan();

  const isPopout = useMemo(() => {
    if (isStandalone) return true;
    if (typeof window !== 'undefined') {
      return new URLSearchParams(window.location.search).get('popout') === 'critique';
    }
    return false;
  }, [isStandalone]);

  const handleClose = useCallback(async () => {
    if (!isPopout) {
      closeCritiqueDocument();
      return;
    }
    try {
      const { getCurrentWindow } = await import('@tauri-apps/api/window');
      await getCurrentWindow().close();
    } catch (closeErr) {
      console.warn('Tauri window close unavailable, using browser close:', closeErr);
      window.close();
    }
  }, [isPopout, closeCritiqueDocument]);

  useEffect(() => {
    if (!critiqueDocumentPhotoId && !isPopout) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' || ((event.metaKey || event.ctrlKey) && event.key === 'w')) {
        event.preventDefault();
        handleClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [critiqueDocumentPhotoId, isPopout, handleClose]);

  useEffect(() => {
    setImgError(false);
    setCopied(false);
    setExported(false);
    setPdfExported(false);
    setLastSavedPath(null);
    setExportProgress((prev) => (prev.active ? { ...prev, active: false } : prev));
    zoomPan.handleResetZoom();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [critiqueDocumentPhotoId]);

  useEffect(() => {
    if (isPopout && photo?.file_name) {
      document.title = `${photo.file_name} - AI 사진 비평 리포트 | Focal Node`;
    }
  }, [isPopout, photo?.file_name]);

  const critiqueText = photo?.ai_analysis?.critique || '';
  const mastheadSummary = useMemo(() => buildMastheadSummary(photo, critiqueText), [photo, critiqueText]);
  const formattedDate = useMemo(() => formatCritiqueDate(photo), [photo]);

  const thumbUrl = critiqueDocumentPhotoId ? api.getPhotoThumbnailUrl(critiqueDocumentPhotoId) : '';
  const originalUrl = critiqueDocumentPhotoId ? `${api.getPhotoOriginalUrl(critiqueDocumentPhotoId)}?raw=true` : '';
  const imageUrl = imgError ? thumbUrl : originalUrl;

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

  const handleExportMarkdown = async () => {
    if (!critiqueText || isExportingMd) return;
    setIsExportingMd(true);
    try {
      const exportResult = await exportCritiqueToMarkdown(photo, critiqueText, formattedDate, mastheadSummary.scores);
      if (exportResult.cancelled) return;
      if (exportResult.savedPath) setLastSavedPath(exportResult.savedPath);
      setExported(true);
      setExportProgress({
        active: true,
        type: 'md',
        title: '마크다운 리포트 저장 완료',
        step: '마크다운 파일(.md) 저장 성공',
        detail: exportResult.savedPath
          ? `저장 위치: ${exportResult.savedPath}`
          : '다운로드 폴더에 마크다운 파일이 저장되었습니다.',
        percent: 100,
        savedPath: exportResult.savedPath,
      });
      setTimeout(() => setExportProgress((prev) => ({ ...prev, active: false })), 2500);
      setTimeout(() => setExported(false), 3000);
    } catch (err) {
      console.error('Failed to export markdown:', err);
      alert('마크다운 파일 저장 중 오류가 발생했습니다.');
    } finally {
      setIsExportingMd(false);
    }
  };

  const handleExportPdf = async () => {
    if (!critiqueText || isExportingPdf) return;
    setIsExportingPdf(true);
    setPdfExported(false);
    try {
      const exportResult = await exportCritiqueToPdf(
        photo,
        critiqueText,
        imageUrl,
        thumbUrl,
        formattedDate,
        mastheadSummary.scores,
        setExportProgress
      );
      if (exportResult.cancelled) {
        setExportProgress((prev) => ({ ...prev, active: false }));
        return;
      }
      if (exportResult.savedPath) setLastSavedPath(exportResult.savedPath);
      setExportProgress({
        active: true,
        type: 'pdf',
        title: 'PDF 리포트 저장 완료',
        step: 'PDF 리포트 저장 완료!',
        detail: exportResult.savedPath ? '파일이 성공적으로 저장되었습니다.' : '다운로드 폴더에 저장되었습니다.',
        percent: 100,
        savedPath: exportResult.savedPath,
      });
      setPdfExported(true);
      setTimeout(() => setExportProgress((prev) => ({ ...prev, active: false })), 2500);
      setTimeout(() => setPdfExported(false), 4000);
    } catch (error) {
      console.error('Failed to generate PDF:', error);
      setExportProgress((prev) => ({ ...prev, active: false }));
      alert('PDF 생성 및 저장 중 오류가 발생했습니다.');
    } finally {
      setIsExportingPdf(false);
    }
  };

  const handlePopout = async () => {
    if (isPopout) return;
    const popoutUrl = `/?popout=critique&photoId=${critiqueDocumentPhotoId}`;
    const openFallbackWindow = () => {
      window.open(popoutUrl, '_blank', 'width=1280,height=860,resizable=yes,scrollbars=yes');
      closeCritiqueDocument();
    };
    try {
      const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow');
      const windowLabel = `critique-doc-${critiqueDocumentPhotoId || Date.now()}`;
      const webview = new WebviewWindow(windowLabel, {
        url: popoutUrl,
        title: `${photo?.file_name || '사진'} - AI 비평 리포트 | Focal Node`,
        width: 1320,
        height: 880,
        minWidth: 960,
        minHeight: 640,
        center: true,
        resizable: true,
        decorations: true,
      });
      webview.once('tauri://created', () => closeCritiqueDocument());
      webview.once('tauri://error', (err) => {
        console.warn('WebviewWindow creation failed, falling back to window.open:', err);
        openFallbackWindow();
      });
    } catch (popoutErr) {
      console.warn('Tauri WebviewWindow unavailable, using window.open:', popoutErr);
      openFallbackWindow();
    }
  };

  return {
    critiqueDocumentPhotoId,
    photo,
    isLoading,
    isPopout,
    formattedDate,
    critiqueText,
    mastheadSummary,
    imageUrl,
    copied,
    exported,
    isExportingMd,
    isExportingPdf,
    pdfExported,
    lastSavedPath,
    exportProgress,
    setExportProgress,
    isMaximized,
    setIsMaximized,
    setImgError,
    zoomPan,
    handleClose,
    handleCopyText,
    handleExportMarkdown,
    handleExportPdf,
    handlePopout,
  };
}
