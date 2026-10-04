import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Copy, 
  Check, 
  ExternalLink, 
  Download,
  FileDown,
  Maximize2,
  Minimize2,
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  Camera, 
  FileText, 
  Calendar, 
  Info,
  Loader2
} from 'lucide-react';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import { useAppStore } from '../../store/useAppStore';
import { usePhotoDetailQuery } from '../../hooks/usePhotoDetailQuery';
import { api } from '../../services/api';
import { CritiqueContentRenderer, extractScoreboard, parseMarkdownToBlocks } from './CritiqueContentRenderer';
import { PhotoDetail } from '../../hooks/usePhotoDetail';

interface CritiqueDocumentModalProps {
  isStandalone?: boolean;
}

interface CritiqueScores {
  overall: number | null;
  iaa: number | null;
  iqa: number | null;
  ista: number | null;
}

/**
 * Fetches an image URL and converts it to a Base64 data URL for safe offline canvas rendering.
 */
async function fetchImageAsDataUrl(url: string): Promise<string> {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const blob = await response.blob();
    return await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        if (typeof reader.result === 'string') {
          resolve(reader.result);
        } else {
          reject(new Error('FileReader result is not a string'));
        }
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  } catch (err) {
    console.warn('Failed to fetch image as data URL, fallback to raw url:', err);
    return url;
  }
}

/**
 * Builds a clean, professional A4 print HTML document with photo, EXIF, scores, and critique.
 */
function generatePrintHtml(
  photo: PhotoDetail | null | undefined,
  critiqueContentHtml: string,
  imageUrl: string,
  formattedDate: string | null,
  scores?: CritiqueScores | null
): string {
  const meta = photo?.metadata;
  return `
  <div class="focal-pdf-report-container">
    <style>
      .focal-pdf-report-container {
        box-sizing: border-box;
        width: 794px;
        background-color: #ffffff !important;
        color: #1f2937 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Apple SD Gothic Neo", "Malgun Gothic", "Pretendard", sans-serif;
        padding: 36px 40px;
        line-height: 1.6;
        font-size: 13px;
        --accent-focal: #e11d48;
        --accent-focal-hover: #be123c;
        --accent-focal-deep: #9f1239;
        --text-primary: #111827;
        --text-secondary: #4b5563;
        --text-muted: #6b7280;
        --border-subtle: #e5e7eb;
      }
      .focal-pdf-report-container * {
        box-sizing: border-box;
      }
      .focal-pdf-report-container .report-container {
        max-width: 714px;
        margin: 0 auto;
      }
      .focal-pdf-report-container .report-header {
        border-bottom: 2px solid #e11d48;
        padding-bottom: 12px;
        margin-bottom: 18px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
      }
      .focal-pdf-report-container .brand-title {
        font-size: 11px;
        font-weight: 700;
        color: #e11d48;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 4px;
      }
      .focal-pdf-report-container .report-title {
        font-size: 20px;
        font-weight: 800;
        color: #111827;
        margin: 0;
      }
      .focal-pdf-report-container .report-date {
        font-size: 12px;
        color: #6b7280;
      }
      .focal-pdf-report-container .photo-summary-card {
        display: flex;
        gap: 18px;
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 18px;
      }
      .focal-pdf-report-container .photo-img {
        max-width: 220px;
        max-height: 165px;
        object-fit: contain;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        background: #111;
      }
      .focal-pdf-report-container .meta-details {
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 6px;
      }
      .focal-pdf-report-container .meta-row {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
      }
      .focal-pdf-report-container .meta-label {
        color: #6b7280;
        font-weight: 500;
        min-width: 60px;
      }
      .focal-pdf-report-container .meta-value {
        color: #111827;
        font-weight: 600;
      }
      .focal-pdf-report-container .caption-box {
        margin-top: 6px;
        padding: 8px 12px;
        background: #fff1f2;
        border-left: 3px solid #e11d48;
        border-radius: 4px;
        font-style: italic;
        color: #9f1239;
        font-size: 12px;
        line-height: 1.5;
      }
      .focal-pdf-report-container .score-grid {
        display: flex;
        gap: 10px;
        margin-bottom: 22px;
      }
      .focal-pdf-report-container .score-card {
        flex: 1;
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 10px 12px;
        text-align: center;
      }
      .focal-pdf-report-container .score-card.main-score {
        flex: 1.3;
        background: #fff1f2;
        border-color: #fecdd3;
      }
      .focal-pdf-report-container .score-label {
        font-size: 10.5px;
        font-weight: 600;
        color: #6b7280;
        margin-bottom: 2px;
        letter-spacing: 0.04em;
      }
      .focal-pdf-report-container .score-card.main-score .score-label {
        color: #e11d48;
      }
      .focal-pdf-report-container .score-val {
        font-size: 19px;
        font-weight: 800;
        color: #111827;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      }
      .focal-pdf-report-container .score-card.main-score .score-val {
        color: #e11d48;
      }
      .focal-pdf-report-container .score-max {
        font-size: 11px;
        font-weight: 500;
        color: #9ca3af;
        margin-left: 2px;
      }
      .focal-pdf-report-container .critique-body {
        color: #374151 !important;
        font-size: 13px;
        line-height: 1.7;
      }
      .focal-pdf-report-container .critique-body * {
        color: #374151 !important;
        border-color: #e5e7eb !important;
      }
      .focal-pdf-report-container .critique-body h1,
      .focal-pdf-report-container .critique-body h2,
      .focal-pdf-report-container .critique-body h3,
      .focal-pdf-report-container .critique-body h4,
      .focal-pdf-report-container .critique-body strong,
      .focal-pdf-report-container .critique-body b {
        color: #111827 !important;
      }
      .focal-pdf-report-container .critique-body section {
        border-top-color: #e5e7eb !important;
      }
      .focal-pdf-report-container .critique-body svg {
        stroke: #e11d48 !important;
      }
      .focal-pdf-report-container .report-footer {
        margin-top: 32px;
        padding-top: 12px;
        border-top: 1px solid #e5e7eb;
        display: flex;
        justify-content: space-between;
        color: #9ca3af;
        font-size: 11px;
      }
    </style>
    <div class="report-container">
      <div class="report-header">
        <div>
          <div class="brand-title">Focal Node · AI Photo Critique Report</div>
          <h1 class="report-title">${photo?.file_name || '사진'}</h1>
        </div>
        <div class="report-date">${formattedDate ? `분석일: ${formattedDate}` : ''}</div>
      </div>

      <div class="photo-summary-card">
        <img src="${imageUrl}" class="photo-img" alt="${photo?.file_name || ''}" />
        <div class="meta-details">
          ${meta?.camera_model ? `<div class="meta-row"><span class="meta-label">카메라</span><span class="meta-value">${meta.camera_model}</span></div>` : ''}
          ${meta?.lens_model ? `<div class="meta-row"><span class="meta-label">렌즈</span><span class="meta-value">${meta.lens_model}</span></div>` : ''}
          <div class="meta-row">
            <span class="meta-label">촬영 정보</span>
            <span class="meta-value">
              ${[
                meta?.focal_length ? `${meta.focal_length}mm` : null,
                meta?.f_number ? `f/${meta.f_number}` : null,
                meta?.shutter_speed ? `${meta.shutter_speed}s` : null,
                meta?.iso ? `ISO ${meta.iso}` : null
              ].filter(Boolean).join('  ·  ') || '메타데이터 없음'}
            </span>
          </div>
          ${photo?.ai_analysis?.caption ? `<div class="caption-box">"${photo.ai_analysis.caption}"</div>` : ''}
        </div>
      </div>

      ${scores ? `
      <div class="score-grid">
        <div class="score-card main-score">
          <div class="score-label">종합 평가</div>
          <div class="score-val">${scores.overall ?? '-'}<span class="score-max">/100</span></div>
        </div>
        ${scores.iaa !== null ? `
        <div class="score-card">
          <div class="score-label">IAA (미학 & 구도)</div>
          <div class="score-val">${scores.iaa}</div>
        </div>` : ''}
        ${scores.iqa !== null ? `
        <div class="score-card">
          <div class="score-label">IQA (화질 & 광학)</div>
          <div class="score-val">${scores.iqa}</div>
        </div>` : ''}
        ${scores.ista !== null ? `
        <div class="score-card">
          <div class="score-label">ISTA (구조 & 질감)</div>
          <div class="score-val">${scores.ista}</div>
        </div>` : ''}
      </div>` : ''}

      <div class="critique-body">
        ${critiqueContentHtml}
      </div>

      <div class="report-footer">
        <span>On-device AI Local Photo Search & Aesthetic Curator</span>
        <span>Focal Node</span>
      </div>
    </div>
  </div>`;
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
  const [exportProgress, setExportProgress] = useState<{
    active: boolean;
    type: 'pdf' | 'md';
    title: string;
    step: string;
    detail: string;
    percent: number;
    savedPath?: string | null;
  }>({
    active: false,
    type: 'pdf',
    title: '',
    step: '',
    detail: '',
    percent: 0,
    savedPath: null
  });
  const [isMaximized, setIsMaximized] = useState(false);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imgError, setImgError] = useState(false);

  // Check if current page is opened in dedicated popout window
  const urlParams = new URLSearchParams(window.location.search);
  const isPopout = isStandalone || urlParams.get('popout') === 'critique';

  // Reset zoom, pan & export states when photo changes
  useEffect(() => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
    setImgError(false);
    setLastSavedPath(null);
    setExported(false);
    setIsExportingMd(false);
    setPdfExported(false);
    setIsExportingPdf(false);
    setExportProgress({ active: false, type: 'pdf', title: '', step: '', detail: '', percent: 0, savedPath: null });
  }, [critiqueDocumentPhotoId]);

  // Window or Modal close handler
  const handleClose = useCallback(async () => {
    if (isPopout) {
      try {
        const { getCurrentWebviewWindow } = await import('@tauri-apps/api/webviewWindow');
        const currentWin = getCurrentWebviewWindow();
        await currentWin.close();
      } catch {
        window.close();
      }
    } else {
      closeCritiqueDocument();
    }
  }, [isPopout, closeCritiqueDocument]);

  // Keyboard shortcut: ESC to close
  useEffect(() => {
    if (!critiqueDocumentPhotoId && !isPopout) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [critiqueDocumentPhotoId, isPopout, handleClose]);

  const critiqueText = photo?.ai_analysis?.critique || '';
  const mastheadData = useMemo(() => {
    if (!critiqueText) return { scores: null, summary: null };
    const { scores, remainingText } = extractScoreboard(critiqueText);
    const blocks = parseMarkdownToBlocks(remainingText);
    const summaryBlock = blocks.find((b) => b.type === 'executive_summary');
    const summary = summaryBlock && 'summary' in summaryBlock ? summaryBlock.summary : null;
    return { scores, summary };
  }, [critiqueText]);

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

  // 1. Text copy handler with fallback
  const handleCopyText = async () => {
    if (!critiqueText) return;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(critiqueText);
      } else {
        const textArea = document.createElement("textarea");
        textArea.value = critiqueText;
        textArea.style.position = "fixed";
        textArea.style.opacity = "0";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.warn("Clipboard copy failed, using fallback:", err);
      const textArea = document.createElement("textarea");
      textArea.value = critiqueText;
      textArea.style.position = "fixed";
      textArea.style.opacity = "0";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // 2. Export markdown document (.md) with native save dialog and visual feedback
  const handleExportMarkdown = async () => {
    if (!critiqueText || isExportingMd) return;
    setIsExportingMd(true);

    const baseName = photo?.file_name ? photo.file_name.replace(/\.[^/.]+$/, "") : "photo";
    const defaultFileName = `${baseName}_AI비평.md`;

    const exposureParts = [
      meta?.focal_length ? `${meta.focal_length}mm` : null,
      meta?.f_number ? `f/${meta.f_number}` : null,
      meta?.shutter_speed ? `${meta.shutter_speed}s` : null,
      meta?.iso ? `ISO ${meta.iso}` : null
    ].filter(Boolean).join(' | ');

    const scoreLines = mastheadData.scores ? [
      mastheadData.scores.overall !== null ? `> **종합 평가 점수:** ${mastheadData.scores.overall} / 100  ` : null,
      (mastheadData.scores.iaa !== null || mastheadData.scores.iqa !== null || mastheadData.scores.ista !== null)
        ? `> **세부 평가 지수:** ${[
            mastheadData.scores.iaa !== null ? `IAA(미학/구도) ${mastheadData.scores.iaa}` : null,
            mastheadData.scores.iqa !== null ? `IQA(화질/광학) ${mastheadData.scores.iqa}` : null,
            mastheadData.scores.ista !== null ? `ISTA(구조/질감) ${mastheadData.scores.ista}` : null
          ].filter(Boolean).join('  ·  ')}  `
        : null
    ].filter(Boolean) as string[] : [];

    const markdownDocument = [
      `# ${photo?.file_name || '사진'}`,
      ``,
      `> **Focal Node · AI Photo Critique Report**  `,
      formattedDate ? `> **분석 일시:** ${formattedDate}  ` : '',
      meta?.camera_model ? `> **카메라:** ${meta.camera_model}  ` : '',
      meta?.lens_model ? `> **렌즈:** ${meta.lens_model}  ` : '',
      exposureParts ? `> **노출 설정:** ${exposureParts}  ` : '',
      photo?.ai_analysis?.caption ? `> **캡션:** *"${photo.ai_analysis.caption}"*  ` : '',
      ...scoreLines,
      ``,
      `---`,
      ``,
      critiqueText
    ].filter(line => line !== null).join('\n');

    let selectedPath: string | null = null;
    try {
      const { save } = await import('@tauri-apps/plugin-dialog');
      selectedPath = await save({
        defaultPath: defaultFileName,
        filters: [{ name: 'Markdown 문서 (*.md)', extensions: ['md'] }]
      });
    } catch (dialogErr) {
      console.warn('Tauri dialog save is unavailable, will fallback to browser download:', dialogErr);
    }

    // 사용자가 파일 저장 창에서 "취소"를 누른 경우
    if (selectedPath === null && typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
      setIsExportingMd(false);
      return;
    }

    try {
      const encoder = new TextEncoder();
      const uint8Array = encoder.encode(markdownDocument);

      if (selectedPath) {
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('save_binary_file', {
          path: selectedPath,
          data: Array.from(uint8Array)
        });
        setLastSavedPath(selectedPath);
      } else {
        // 브라우저 fallback 다운로드
        const blob = new Blob([markdownDocument], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = defaultFileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }

      setExported(true);
      setExportProgress({
        active: true,
        type: 'md',
        title: '마크다운 리포트 저장 완료',
        step: '마크다운 파일(.md) 저장 성공',
        detail: selectedPath ? `저장 위치: ${selectedPath}` : '다운로드 폴더에 마크다운 파일이 저장되었습니다.',
        percent: 100,
        savedPath: selectedPath
      });

      // 2.5초 후 자동 닫기
      setTimeout(() => {
        setExportProgress((prev) => ({ ...prev, active: false }));
      }, 2500);

      setTimeout(() => setExported(false), 3000);
    } catch (err) {
      console.error('Failed to export markdown document:', err);
      alert('마크다운 파일 저장 중 오류가 발생했습니다.');
    } finally {
      setIsExportingMd(false);
    }
  };

  // 3. Export PDF report handler with step-by-step progress feedback
  const handleExportPdf = async () => {
    if (!critiqueText || isExportingPdf) return;

    setIsExportingPdf(true);
    setPdfExported(false);

    const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
    let container: HTMLDivElement | null = null;

    try {
      // 1) 사진 에셋 준비 (15%)
      setExportProgress({
        active: true,
        type: 'pdf',
        title: 'A4 비평 리포트 PDF 생성 중',
        step: '사진 및 그래픽 에셋 준비 중...',
        detail: '고해상도 인쇄를 위해 사진 이미지를 인라인으로 준비하고 있습니다.',
        percent: 15,
        savedPath: null
      });
      await delay(80);

      let embeddedImageUrl = await fetchImageAsDataUrl(imageUrl);
      if (!embeddedImageUrl.startsWith('data:') && imageUrl !== thumbUrl) {
        embeddedImageUrl = await fetchImageAsDataUrl(thumbUrl);
      }

      // 2) A4 리포트 레이아웃 구성 (35%)
      setExportProgress({
        active: true,
        type: 'pdf',
        title: 'A4 비평 리포트 PDF 생성 중',
        step: 'A4 리포트 레이아웃 렌더링 중...',
        detail: 'EXIF 메타데이터와 종합 평가 지수 그리드를 배치하고 있습니다.',
        percent: 35,
        savedPath: null
      });
      await delay(80);

      const paperElem = document.getElementById('critique-rendered-body');
      const contentHtml = paperElem ? paperElem.innerHTML : critiqueText;

      const printHtml = generatePrintHtml(
        photo,
        contentHtml,
        embeddedImageUrl,
        formattedDate,
        mastheadData.scores
      );

      // 오프스크린 렌더링 컨테이너 생성 (사용자에게는 보이지 않도록 z-index -9999로 배치하되 html2canvas 인식을 위해 opacity 1 유지)
      container = document.createElement('div');
      container.id = 'pdf-render-temp-container';
      container.style.position = 'fixed';
      container.style.left = '0';
      container.style.top = '0';
      container.style.width = '794px'; // 210mm at 96 DPI
      container.style.backgroundColor = '#ffffff';
      container.style.color = '#1f2937';
      container.style.zIndex = '-9999';
      container.style.opacity = '1';
      container.style.pointerEvents = 'none';
      container.innerHTML = printHtml;
      document.body.appendChild(container);

      // 내부 이미지 로드 및 디코딩 완료 대기
      const imgElements = Array.from(container.querySelectorAll('img'));
      await Promise.all(
        imgElements.map(
          (img) =>
            new Promise<void>((resolve) => {
              if (img.complete && img.naturalWidth > 0) {
                if ('decode' in img) {
                  img.decode().then(() => resolve()).catch(() => resolve());
                } else {
                  resolve();
                }
              } else {
                img.onload = () => {
                  if ('decode' in img) {
                    img.decode().then(() => resolve()).catch(() => resolve());
                  } else {
                    resolve();
                  }
                };
                img.onerror = () => resolve();
              }
            })
        )
      );

      // 브라우저 DOM 렌더링 파이프라인(Layout/Paint) 완료를 위해 2프레임 대기
      await new Promise<void>((resolve) => {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => resolve());
        });
      });

      // 3) 초고해상도 캔버스 캡처 (65%)
      setExportProgress({
        active: true,
        type: 'pdf',
        title: 'A4 비평 리포트 PDF 생성 중',
        step: '초고해상도(Retina 2x) 벡터 캔버스 캡처 중...',
        detail: '텍스트와 이미지를 선명한 픽셀로 정밀 렌더링하고 있습니다.',
        percent: 65,
        savedPath: null
      });
      await delay(100);

      const canvas = await html2canvas(container, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff',
        logging: false,
        x: 0,
        y: 0,
        scrollX: 0,
        scrollY: 0,
        width: 794,
        windowWidth: 794
      });

      if (!canvas || canvas.width <= 0 || canvas.height <= 0) {
        throw new Error('Canvas capture resulted in invalid dimensions');
      }

      // 4) A4 페이지 슬라이스 및 PDF 조립 (85%)
      setExportProgress({
        active: true,
        type: 'pdf',
        title: 'A4 비평 리포트 PDF 생성 중',
        step: 'A4 페이지 슬라이스 및 PDF 조립 중...',
        detail: '인쇄 규격에 맞춰 페이지를 분할하고 최종 문서를 조립하고 있습니다.',
        percent: 85,
        savedPath: null
      });
      await delay(80);

      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
        compress: true
      });

      const pageWidthMm = 210;
      const pageHeightMm = 297;
      if (canvas.width <= 0 || canvas.height <= 0) {
        throw new Error('Canvas capture resulted in invalid dimensions');
      }
      const pageHeightPx = Math.floor(canvas.width * (pageHeightMm / pageWidthMm));
      if (pageHeightPx <= 0) {
        throw new Error('Page height calculation resulted in 0');
      }

      let renderedHeight = 0;
      let pageIndex = 0;

      while (renderedHeight < canvas.height) {
        if (pageIndex > 0) {
          pdf.addPage();
        }

        const sliceHeightPx = Math.min(pageHeightPx, canvas.height - renderedHeight);
        const pageCanvas = document.createElement('canvas');
        pageCanvas.width = canvas.width;
        pageCanvas.height = pageHeightPx;

        const ctx = pageCanvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);
          ctx.drawImage(
            canvas,
            0,
            renderedHeight,
            canvas.width,
            sliceHeightPx,
            0,
            0,
            canvas.width,
            sliceHeightPx
          );
        }

        const pageDataUrl = pageCanvas.toDataURL('image/jpeg', 0.95);
        pdf.addImage(pageDataUrl, 'JPEG', 0, 0, pageWidthMm, pageHeightMm, undefined, 'FAST');

        renderedHeight += pageHeightPx;
        pageIndex++;
      }

      // 5) 파일 저장 경로 확인 (95%)
      setExportProgress({
        active: true,
        type: 'pdf',
        title: 'A4 비평 리포트 PDF 생성 중',
        step: '저장 경로 확인 및 파일 기록 중...',
        detail: '원하는 저장 위치와 파일명을 선택해 주세요.',
        percent: 95,
        savedPath: null
      });

      const baseName = photo?.file_name ? photo.file_name.replace(/\.[^/.]+$/, '') : 'photo';
      const defaultFileName = `${baseName}_AI비평_리포트.pdf`;

      let selectedPath: string | null = null;
      try {
        const { save } = await import('@tauri-apps/plugin-dialog');
        selectedPath = await save({
          defaultPath: defaultFileName,
          filters: [{ name: 'PDF 문서 (*.pdf)', extensions: ['pdf'] }]
        });
      } catch (dialogErr) {
        console.warn('Tauri dialog save is unavailable, will fallback to browser download:', dialogErr);
      }

      // 사용자가 파일 저장 창에서 "취소"를 누른 경우
      if (selectedPath === null && typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
        setExportProgress((prev) => ({ ...prev, active: false }));
        setIsExportingPdf(false);
        return;
      }

      const pdfArrayBuffer = pdf.output('arraybuffer');
      const uint8Array = new Uint8Array(pdfArrayBuffer);

      if (selectedPath) {
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('save_binary_file', {
          path: selectedPath,
          data: Array.from(uint8Array)
        });
        setLastSavedPath(selectedPath);
      } else {
        // 브라우저 fallback 다운로드
        pdf.save(defaultFileName);
      }

      // 6) 저장 완료 (100%)
      setExportProgress({
        active: true,
        type: 'pdf',
        title: 'PDF 리포트 저장 완료',
        step: 'PDF 리포트 저장 완료!',
        detail: selectedPath ? `파일이 성공적으로 저장되었습니다.` : '다운로드 폴더에 저장되었습니다.',
        percent: 100,
        savedPath: selectedPath
      });
      setPdfExported(true);

      // 완료 후 2.5초 뒤 모달 오버레이 자동 닫기
      setTimeout(() => {
        setExportProgress((prev) => ({ ...prev, active: false }));
      }, 2500);

      setTimeout(() => setPdfExported(false), 4000);
    } catch (error) {
      console.error('Failed to generate or save PDF report:', error);
      setExportProgress((prev) => ({ ...prev, active: false }));
      alert('PDF 생성 및 저장 중 오류가 발생했습니다.');
    } finally {
      if (container && container.parentNode) {
        container.parentNode.removeChild(container);
      }
      setIsExportingPdf(false);
    }
  };

  // 3-1. Reveal saved file in Finder / File Explorer
  const handleRevealFile = async (filePath?: string | null) => {
    const targetPath = filePath || lastSavedPath;
    if (!targetPath) return;
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('reveal_in_finder', { path: targetPath });
    } catch (e) {
      console.warn('Failed to reveal file in finder:', e);
    }
  };

  // 4. Popout into dedicated standalone window
  const handlePopout = async () => {
    try {
      const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow');
      const winLabel = `critique-doc-${critiqueDocumentPhotoId.slice(0, 8)}`;
      const existing = await WebviewWindow.getByLabel(winLabel);
      if (existing) {
        await existing.setFocus();
        closeCritiqueDocument();
        return;
      }

      const webview = new WebviewWindow(winLabel, {
        url: `/?popout=critique&photoId=${critiqueDocumentPhotoId}`,
        title: `AI 사진 비평 - ${photo?.file_name || '문서 뷰'}`,
        width: 1280,
        height: 860,
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
                background: 'linear-gradient(135deg, #e11d48 0%, #be123c 100%)',
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
                    background: 'var(--accent-focal-subtle)',
                    color: 'var(--accent-focal-hover)',
                    border: '1px solid rgba(225, 29, 72, 0.3)',
                    flexShrink: 0
                  }}>
                    {isPopout ? '독립 리포트 윈도우' : '리포트 뷰'}
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
              {/* Copy Text Button */}
              <button
                onClick={handleCopyText}
                disabled={!critiqueText}
                style={{
                  background: copied ? 'var(--accent-focal-subtle)' : 'rgba(255, 255, 255, 0.06)',
                  border: `1px solid ${copied ? 'var(--accent-focal)' : 'rgba(255, 255, 255, 0.12)'}`,
                  color: copied ? 'var(--accent-focal-hover)' : '#d4d4d8',
                  padding: '7px 12px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: critiqueText ? 'pointer' : 'not-allowed',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                  transition: 'all 0.2s ease'
                }}
                title="비평 본문 클립보드 복사"
              >
                {copied ? <Check size={14} style={{ flexShrink: 0 }} /> : <Copy size={14} style={{ flexShrink: 0 }} />}
                <span style={{ whiteSpace: 'nowrap' }}>{copied ? '복사 완료!' : '텍스트 복사'}</span>
              </button>

              {/* Export Markdown (.md) Button */}
              <button
                onClick={handleExportMarkdown}
                disabled={!critiqueText || isExportingMd}
                style={{
                  background: exported ? 'var(--accent-focal-subtle)' : 'rgba(255, 255, 255, 0.06)',
                  border: `1px solid ${exported ? 'var(--accent-focal)' : 'rgba(255, 255, 255, 0.12)'}`,
                  color: exported ? 'var(--accent-focal-hover)' : '#d4d4d8',
                  padding: '7px 12px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: critiqueText && !isExportingMd ? 'pointer' : 'not-allowed',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                  transition: 'all 0.2s ease',
                  opacity: isExportingMd ? 0.75 : 1
                }}
                title="마크다운 리포트 파일(.md)로 다운로드 저장"
              >
                {isExportingMd ? (
                  <Loader2 size={14} className="spin" style={{ flexShrink: 0 }} />
                ) : exported ? (
                  <Check size={14} style={{ flexShrink: 0 }} />
                ) : (
                  <Download size={14} style={{ flexShrink: 0 }} />
                )}
                <span style={{ whiteSpace: 'nowrap' }}>
                  {isExportingMd ? 'MD 저장 중...' : exported ? '저장 완료!' : 'MD 저장'}
                </span>
              </button>

              {/* Export PDF Button */}
              <button
                onClick={handleExportPdf}
                disabled={!critiqueText || isExportingPdf}
                style={{
                  background: pdfExported ? 'var(--accent-focal-subtle)' : 'rgba(255, 255, 255, 0.06)',
                  border: `1px solid ${pdfExported ? 'var(--accent-focal)' : 'rgba(255, 255, 255, 0.12)'}`,
                  color: pdfExported ? 'var(--accent-focal-hover)' : '#d4d4d8',
                  padding: '7px 12px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: critiqueText && !isExportingPdf ? 'pointer' : 'not-allowed',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                  transition: 'all 0.2s ease',
                  opacity: isExportingPdf ? 0.75 : 1
                }}
                title="사진과 점수, EXIF 메타데이터가 포함된 완성형 A4 PDF 리포트 파일로 저장"
              >
                {isExportingPdf ? (
                  <Loader2 size={14} className="spin" style={{ flexShrink: 0 }} />
                ) : pdfExported ? (
                  <Check size={14} style={{ flexShrink: 0 }} />
                ) : (
                  <FileDown size={14} style={{ flexShrink: 0 }} />
                )}
                <span style={{ whiteSpace: 'nowrap' }}>
                  {isExportingPdf ? 'PDF 생성 중...' : pdfExported ? '저장 완료!' : 'PDF 저장'}
                </span>
              </button>

              {/* Reveal saved file in Finder button (shown after successful save of PDF or MD) */}
              {lastSavedPath && (
                <button
                  onClick={() => handleRevealFile(lastSavedPath)}
                  style={{
                    background: 'rgba(225, 29, 72, 0.15)',
                    border: '1px solid rgba(225, 29, 72, 0.35)',
                    color: 'var(--accent-focal-hover)',
                    padding: '7px 10px',
                    borderRadius: '8px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    whiteSpace: 'nowrap',
                    flexShrink: 0,
                    transition: 'all 0.2s ease'
                  }}
                  title="저장된 파일 위치를 Finder에서 표시"
                >
                  <ExternalLink size={12} style={{ flexShrink: 0 }} />
                  <span>폴더 열기</span>
                </button>
              )}

              {/* Popout Button (Only in modal mode) */}
              {!isPopout && (
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
                    gap: '6px',
                    whiteSpace: 'nowrap',
                    flexShrink: 0,
                    transition: 'all 0.2s ease'
                  }}
                  title="별도 독립 데스크탑 윈도우로 분리"
                >
                  <ExternalLink size={14} style={{ flexShrink: 0 }} />
                  <span style={{ whiteSpace: 'nowrap' }}>새 창으로 분리</span>
                </button>
              )}

              {/* Maximize / Restore Toggle (Only in modal mode) */}
              {!isPopout && (
                <button
                  onClick={() => setIsMaximized((prev) => !prev)}
                  style={{
                    background: isMaximized ? 'var(--accent-focal-subtle)' : 'rgba(255, 255, 255, 0.06)',
                    border: `1px solid ${isMaximized ? 'rgba(225, 29, 72, 0.4)' : 'rgba(255, 255, 255, 0.12)'}`,
                    color: isMaximized ? 'var(--accent-focal-hover)' : '#d4d4d8',
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                  title={isMaximized ? '원래 창 크기로 복원' : '화면 전체로 크게 보기'}
                >
                  {isMaximized ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
                </button>
              )}

              <div style={{ width: '1px', height: '20px', backgroundColor: 'rgba(255, 255, 255, 0.1)', margin: '0 4px' }} />

              {/* Close Button */}
              <button
                onClick={handleClose}
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
                title={isPopout ? '창 닫기 (ESC)' : '모달 닫기 (ESC)'}
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

                {/* Floating Zoom Control Bar (Minimal Pill) */}
                <div
                  style={{
                    position: 'absolute',
                    top: '16px',
                    left: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    background: 'rgba(18, 18, 22, 0.65)',
                    backdropFilter: 'blur(12px)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '20px',
                    padding: '3px 8px',
                    zIndex: 10
                  }}
                >
                  <button
                    onClick={() => setScale((prev) => Math.max(prev - 0.2, 0.6))}
                    style={{ background: 'none', border: 'none', color: '#a1a1aa', cursor: 'pointer', padding: '2px', display: 'flex' }}
                    title="축소"
                  >
                    <ZoomOut size={13} />
                  </button>
                  <span className="font-mono" style={{ fontSize: '11px', color: '#f4f4f5', fontWeight: 600, minWidth: '36px', textAlign: 'center' }}>
                    {Math.round(scale * 100)}%
                  </span>
                  <button
                    onClick={() => setScale((prev) => Math.min(prev + 0.2, 3.5))}
                    style={{ background: 'none', border: 'none', color: '#a1a1aa', cursor: 'pointer', padding: '2px', display: 'flex' }}
                    title="확대"
                  >
                    <ZoomIn size={13} />
                  </button>
                  {scale !== 1 && (
                    <button
                      onClick={handleResetZoom}
                      style={{ background: 'none', border: 'none', color: 'var(--accent-focal-hover)', cursor: 'pointer', padding: '2px', display: 'flex', marginLeft: '2px' }}
                      title="줌 리셋"
                    >
                      <RotateCcw size={12} />
                    </button>
                  )}
                </div>
              </div>

              {/* Bottom EXIF HUD Overlay (Leica Monospace HUD) */}
              <div
                style={{
                  padding: '10px 18px',
                  backgroundColor: 'rgba(12, 12, 15, 0.95)',
                  borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px',
                  fontSize: '11.5px',
                  color: '#a1a1aa'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0, overflow: 'hidden' }}>
                  <Camera size={13} color="var(--accent-focal)" style={{ flexShrink: 0 }} />
                  <span style={{ color: '#e4e4e7', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {meta?.camera_model || '카메라'}
                  </span>
                  {meta?.lens_model && (
                    <span style={{ color: '#71717a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      · {meta.lens_model}
                    </span>
                  )}
                </div>

                <div
                  className="font-mono"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    color: '#f4f4f5',
                    fontSize: '11px',
                    whiteSpace: 'nowrap',
                    flexShrink: 0
                  }}
                >
                  {meta?.focal_length && <span>{meta.focal_length}mm</span>}
                  {meta?.focal_length && (meta?.f_number || meta?.shutter_speed || meta?.iso) && (
                    <span style={{ color: 'rgba(255, 255, 255, 0.2)' }}>·</span>
                  )}
                  {meta?.f_number && <span>f/{meta.f_number}</span>}
                  {meta?.f_number && (meta?.shutter_speed || meta?.iso) && (
                    <span style={{ color: 'rgba(255, 255, 255, 0.2)' }}>·</span>
                  )}
                  {meta?.shutter_speed && <span>{meta.shutter_speed}s</span>}
                  {meta?.shutter_speed && meta?.iso && (
                    <span style={{ color: 'rgba(255, 255, 255, 0.2)' }}>·</span>
                  )}
                  {meta?.iso && <span>ISO {meta.iso}</span>}
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
                {/* 1. Unified Editorial Masthead (Plan A) */}
                <div style={{ marginBottom: '20px' }}>
                  <h1 style={{
                    margin: '0 0 14px 0',
                    fontSize: '24px',
                    fontWeight: 700,
                    color: '#fff',
                    letterSpacing: '-0.02em',
                    lineHeight: '1.3'
                  }}>
                    {photo?.file_name}
                  </h1>

                  {/* Editorial Lead Subtitle (Executive Summary or Caption) */}
                  {(mastheadData.summary || photo?.ai_analysis?.caption) && (
                    <p style={{
                      margin: '0 0 20px 0',
                      fontSize: '15px',
                      lineHeight: '1.65',
                      color: '#e4e4e7',
                      fontStyle: 'italic',
                      letterSpacing: '-0.01em'
                    }}>
                      "{mastheadData.summary || photo?.ai_analysis?.caption}"
                    </p>
                  )}

                  {/* 1-Line Minimal Spec Divider */}
                  {mastheadData.scores && (
                    <div style={{
                      borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                      padding: '12px 0 0 0',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '12px'
                    }}>
                      {/* Overall Score */}
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                        <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em' }}>
                          TOTAL
                        </span>
                        <span className="font-mono" style={{ fontSize: '19px', fontWeight: 700, color: 'var(--accent-focal-hover)', letterSpacing: '-0.02em', lineHeight: 1 }}>
                          {mastheadData.scores.overall ?? '-'}
                        </span>
                        <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          / 100
                        </span>
                      </div>

                      {/* Detail Metrics Chips */}
                      <div
                        className="font-mono"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          fontSize: '11.5px',
                          color: 'var(--text-secondary)'
                        }}
                      >
                        {mastheadData.scores.iaa !== null && (
                          <span title="미학 & 구도 지수 (IAA)">
                            <span style={{ color: 'var(--text-muted)', marginRight: '3px' }}>IAA</span>
                            <strong style={{ color: '#fff' }}>{mastheadData.scores.iaa}</strong>
                          </span>
                        )}
                        {mastheadData.scores.iaa !== null && (mastheadData.scores.iqa !== null || mastheadData.scores.ista !== null) && (
                          <span style={{ color: 'rgba(255, 255, 255, 0.2)' }}>·</span>
                        )}
                        {mastheadData.scores.iqa !== null && (
                          <span title="화질 & 광학 지수 (IQA)">
                            <span style={{ color: 'var(--text-muted)', marginRight: '3px' }}>IQA</span>
                            <strong style={{ color: '#fff' }}>{mastheadData.scores.iqa}</strong>
                          </span>
                        )}
                        {mastheadData.scores.iqa !== null && mastheadData.scores.ista !== null && (
                          <span style={{ color: 'rgba(255, 255, 255, 0.2)' }}>·</span>
                        )}
                        {mastheadData.scores.ista !== null && (
                          <span title="구조 & 질감 지수 (ISTA)">
                            <span style={{ color: 'var(--text-muted)', marginRight: '3px' }}>ISTA</span>
                            <strong style={{ color: '#fff' }}>{mastheadData.scores.ista}</strong>
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Content Renderer or Empty State */}
                {isLoading ? (
                  <div style={{ padding: '60px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#a1a1aa' }}>
                    <Loader2 size={24} className="spin" color="var(--accent-focal)" style={{ marginBottom: '12px' }} />
                    <p style={{ margin: 0, fontSize: '14px' }}>비평 데이터를 불러오는 중입니다...</p>
                  </div>
                ) : critiqueText ? (
                  <div id="critique-rendered-body">
                    <CritiqueContentRenderer
                      content={critiqueText}
                      mode="document"
                      hideScoreboard={!!mastheadData.scores}
                      hideExecutiveSummary={!!mastheadData.summary}
                    />
                  </div>
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

          {/* Export Generation Progress & Completion Modal Overlay */}
          <AnimatePresence>
            {exportProgress.active && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.18 }}
                style={{
                  position: 'absolute',
                  inset: 0,
                  backgroundColor: 'rgba(5, 5, 8, 0.82)',
                  backdropFilter: 'blur(10px)',
                  zIndex: 99,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '24px'
                }}
              >
                <motion.div
                  initial={{ scale: 0.94, opacity: 0, y: 10 }}
                  animate={{ scale: 1, opacity: 1, y: 0 }}
                  exit={{ scale: 0.94, opacity: 0, y: 10 }}
                  transition={{ duration: 0.22, ease: 'easeOut' }}
                  style={{
                    width: '100%',
                    maxWidth: '460px',
                    backgroundColor: '#121216',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '16px',
                    boxShadow: '0 25px 60px rgba(0, 0, 0, 0.9), 0 0 35px rgba(225, 29, 72, 0.18)',
                    padding: '26px 28px',
                    boxSizing: 'border-box',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '18px'
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  {/* Modal Header */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <div
                      style={{
                        width: '42px',
                        height: '42px',
                        borderRadius: '10px',
                        backgroundColor: exportProgress.percent === 100 ? 'rgba(34, 197, 94, 0.15)' : 'rgba(225, 29, 72, 0.15)',
                        border: `1px solid ${exportProgress.percent === 100 ? 'rgba(34, 197, 94, 0.35)' : 'rgba(225, 29, 72, 0.35)'}`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}
                    >
                      {exportProgress.percent === 100 ? (
                        <Check size={20} color="#22c55e" />
                      ) : exportProgress.type === 'md' ? (
                        <FileText size={20} color="var(--accent-focal-hover)" />
                      ) : (
                        <FileDown size={20} color="var(--accent-focal-hover)" />
                      )}
                    </div>
                    <div style={{ overflow: 'hidden' }}>
                      <h3 style={{ margin: '0 0 3px 0', fontSize: '15px', fontWeight: 700, color: '#f4f4f5' }}>
                        {exportProgress.title}
                      </h3>
                      <p style={{ margin: 0, fontSize: '12px', color: '#a1a1aa', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {exportProgress.type === 'md'
                          ? `${photo?.file_name ? photo.file_name.replace(/\.[^/.]+$/, "") : "photo"}_AI비평.md`
                          : photo?.file_name}
                      </p>
                    </div>
                  </div>

                  {/* Progress Gauge Section */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <span style={{ fontSize: '12.5px', fontWeight: 600, color: '#e4e4e7' }}>
                        {exportProgress.step}
                      </span>
                      <span
                        className="font-mono"
                        style={{
                          fontSize: '13px',
                          fontWeight: 700,
                          color: exportProgress.percent === 100 ? '#22c55e' : 'var(--accent-focal-hover)'
                        }}
                      >
                        {exportProgress.percent}%
                      </span>
                    </div>

                    {/* Progress Bar Track */}
                    <div
                      style={{
                        width: '100%',
                        height: '7px',
                        backgroundColor: 'rgba(255, 255, 255, 0.08)',
                        borderRadius: '4px',
                        overflow: 'hidden',
                        position: 'relative'
                      }}
                    >
                      <motion.div
                        style={{
                          height: '100%',
                          borderRadius: '4px',
                          background: exportProgress.percent === 100
                            ? 'linear-gradient(90deg, #16a34a 0%, #22c55e 100%)'
                            : 'linear-gradient(90deg, #e11d48 0%, #f43f5e 100%)',
                          boxShadow: exportProgress.percent === 100
                            ? '0 0 10px rgba(34, 197, 94, 0.5)'
                            : '0 0 10px rgba(225, 29, 72, 0.5)',
                          width: `${exportProgress.percent}%`
                        }}
                        transition={{ ease: 'easeOut', duration: 0.3 }}
                      />
                    </div>

                    <span style={{ fontSize: '11.5px', color: '#71717a', lineHeight: 1.4 }}>
                      {exportProgress.detail}
                    </span>
                  </div>

                  {/* Footer Action or Status Notice */}
                  {exportProgress.percent === 100 && (exportProgress.savedPath || lastSavedPath) ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px', paddingTop: '4px' }}>
                      <button
                        onClick={() => handleRevealFile(exportProgress.savedPath || lastSavedPath)}
                        style={{
                          background: 'rgba(225, 29, 72, 0.15)',
                          border: '1px solid rgba(225, 29, 72, 0.35)',
                          color: 'var(--accent-focal-hover)',
                          padding: '7px 12px',
                          borderRadius: '8px',
                          fontSize: '12px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        <ExternalLink size={13} />
                        <span>Finder에서 파일 열기</span>
                      </button>
                      <button
                        onClick={() => setExportProgress((prev) => ({ ...prev, active: false }))}
                        style={{
                          background: 'rgba(255, 255, 255, 0.08)',
                          border: '1px solid rgba(255, 255, 255, 0.15)',
                          color: '#f4f4f5',
                          padding: '7px 14px',
                          borderRadius: '8px',
                          fontSize: '12px',
                          fontWeight: 500,
                          cursor: 'pointer',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        닫기
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '7px', fontSize: '11px', color: '#71717a' }}>
                      <Loader2 size={12} className="spin" color="var(--accent-focal)" />
                      <span>{exportProgress.type === 'md' ? '마크다운 리포트를 파일로 저장하고 있습니다...' : '고해상도 렌더링 중입니다. 잠시만 기다려주세요...'}</span>
                    </div>
                  )}
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
