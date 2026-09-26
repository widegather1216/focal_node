import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Copy, 
  Check, 
  Printer, 
  ExternalLink, 
  Download,
  Maximize2,
  Minimize2,
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
import { PhotoDetail } from '../../hooks/usePhotoDetail';

interface CritiqueDocumentModalProps {
  isStandalone?: boolean;
}

/**
 * Builds a clean, professional A4 print HTML document with photo, EXIF, and critique.
 */
function generatePrintHtml(
  photo: PhotoDetail | null | undefined,
  critiqueContentHtml: string,
  imageUrl: string,
  formattedDate: string | null
): string {
  const meta = photo?.metadata;
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>AI 사진 비평 리포트 - ${photo?.file_name || 'Focal Node'}</title>
  <style>
    @page {
      size: A4 portrait;
      margin: 15mm;
    }
    * {
      box-sizing: border-box;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
      color: #1f2937;
      background: #ffffff;
      margin: 0;
      padding: 0;
      font-size: 13px;
      line-height: 1.6;
    }
    .report-container {
      max-width: 100%;
      margin: 0 auto;
    }
    .report-header {
      border-bottom: 2px solid #9333ea;
      padding-bottom: 12px;
      margin-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }
    .brand-title {
      font-size: 11px;
      font-weight: 700;
      color: #9333ea;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 4px;
    }
    .report-title {
      font-size: 22px;
      font-weight: 800;
      color: #111827;
      margin: 0;
    }
    .report-date {
      font-size: 12px;
      color: #6b7280;
    }
    .photo-summary-card {
      display: flex;
      gap: 20px;
      background: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 24px;
      page-break-inside: avoid;
    }
    .photo-img {
      max-width: 240px;
      max-height: 180px;
      object-fit: contain;
      border-radius: 6px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      background: #111;
    }
    .meta-details {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
      gap: 6px;
    }
    .meta-row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12.5px;
    }
    .meta-label {
      color: #6b7280;
      font-weight: 500;
      min-width: 60px;
    }
    .meta-value {
      color: #111827;
      font-weight: 600;
    }
    .caption-box {
      margin-top: 8px;
      padding: 8px 12px;
      background: #f3e8ff;
      border-left: 3px solid #9333ea;
      border-radius: 4px;
      font-style: italic;
      color: #4c1d95;
      font-size: 12px;
    }
    .critique-body {
      color: #374151;
      font-size: 13.5px;
      line-height: 1.7;
    }
    .critique-body h1, .critique-body h2, .critique-body h3, .critique-body h4 {
      color: #111827 !important;
      page-break-after: avoid;
    }
    .critique-body section, .critique-body div {
      page-break-inside: avoid;
    }
    .report-footer {
      margin-top: 36px;
      padding-top: 14px;
      border-top: 1px solid #e5e7eb;
      display: flex;
      justify-content: space-between;
      color: #9ca3af;
      font-size: 11px;
      page-break-inside: avoid;
    }
  </style>
</head>
<body>
  <div class="report-container">
    <div class="report-header">
      <div>
        <div class="brand-title">Focal Node · AI Photo Critique Report</div>
        <h1 class="report-title">${photo?.file_name || '사진'} 심층 미학 평론</h1>
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

    <div class="critique-body">
      ${critiqueContentHtml}
    </div>

    <div class="report-footer">
      <span>On-device AI Local Photo Search & Aesthetic Curator</span>
      <span>Focal Node</span>
    </div>
  </div>
</body>
</html>`;
}

export const CritiqueDocumentModal: React.FC<CritiqueDocumentModalProps> = ({ isStandalone = false }) => {
  const { critiqueDocumentPhotoId, closeCritiqueDocument } = useAppStore();
  const { data: photo, isLoading } = usePhotoDetailQuery(critiqueDocumentPhotoId);

  const [copied, setCopied] = useState(false);
  const [exported, setExported] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imgError, setImgError] = useState(false);

  // Check if current page is opened in dedicated popout window
  const urlParams = new URLSearchParams(window.location.search);
  const isPopout = isStandalone || urlParams.get('popout') === 'critique';

  // Reset zoom & pan when photo changes
  useEffect(() => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
    setImgError(false);
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

  // 2. Export markdown document (.md)
  const handleExportMarkdown = () => {
    if (!critiqueText) return;
    const baseName = photo?.file_name ? photo.file_name.replace(/\.[^/.]+$/, "") : "photo";
    const fileName = `${baseName}_AI비평.md`;

    const exposureParts = [
      meta?.focal_length ? `${meta.focal_length}mm` : null,
      meta?.f_number ? `f/${meta.f_number}` : null,
      meta?.shutter_speed ? `${meta.shutter_speed}s` : null,
      meta?.iso ? `ISO ${meta.iso}` : null
    ].filter(Boolean).join(' | ');

    const markdownDocument = [
      `# ${photo?.file_name || '사진'} 심층 미학 평론`,
      ``,
      `> **Focal Node · AI Photo Critique Report**  `,
      formattedDate ? `> **분석 일시:** ${formattedDate}  ` : '',
      meta?.camera_model ? `> **카메라:** ${meta.camera_model}  ` : '',
      meta?.lens_model ? `> **렌즈:** ${meta.lens_model}  ` : '',
      exposureParts ? `> **노출 설정:** ${exposureParts}  ` : '',
      photo?.ai_analysis?.caption ? `> **캡션:** *"${photo.ai_analysis.caption}"*  ` : '',
      ``,
      `---`,
      ``,
      critiqueText
    ].filter(line => line !== null).join('\n');

    const blob = new Blob([markdownDocument], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setExported(true);
    setTimeout(() => setExported(false), 2000);
  };

  // 3. Print / PDF report handler
  const handlePrint = () => {
    const paperElem = document.getElementById('critique-rendered-body');
    const contentHtml = paperElem ? paperElem.innerHTML : critiqueText;
    const printHtml = generatePrintHtml(photo, contentHtml, imageUrl, formattedDate);

    let iframe = document.getElementById('critique-print-frame') as HTMLIFrameElement;
    if (!iframe) {
      iframe = document.createElement('iframe');
      iframe.id = 'critique-print-frame';
      iframe.style.position = 'fixed';
      iframe.style.right = '0';
      iframe.style.bottom = '0';
      iframe.style.width = '0';
      iframe.style.height = '0';
      iframe.style.border = 'none';
      document.body.appendChild(iframe);
    }

    const doc = iframe.contentWindow?.document || iframe.contentDocument;
    if (doc) {
      doc.open();
      doc.write(printHtml);
      doc.close();

      setTimeout(() => {
        try {
          iframe.contentWindow?.focus();
          iframe.contentWindow?.print();
        } catch {
          window.print();
        }
      }, 250);
    } else {
      window.print();
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
            boxShadow: isPopout || isMaximized ? 'none' : '0 25px 60px -15px rgba(0, 0, 0, 0.7), 0 0 40px rgba(168, 85, 247, 0.12)',
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {/* Copy Text Button */}
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
                title="비평 본문 클립보드 복사"
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                <span>{copied ? '복사 완료!' : '텍스트 복사'}</span>
              </button>

              {/* Export Markdown (.md) Button */}
              <button
                onClick={handleExportMarkdown}
                disabled={!critiqueText}
                style={{
                  background: exported ? 'rgba(168, 85, 247, 0.2)' : 'rgba(255, 255, 255, 0.06)',
                  border: `1px solid ${exported ? '#c084fc' : 'rgba(255, 255, 255, 0.12)'}`,
                  color: exported ? '#c084fc' : '#d4d4d8',
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
                title="마크다운 리포트 파일(.md)로 다운로드 저장"
              >
                {exported ? <Check size={14} /> : <Download size={14} />}
                <span>{exported ? '저장 완료!' : 'MD 저장'}</span>
              </button>

              {/* Print / PDF Button */}
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
                  gap: '6px',
                  transition: 'all 0.2s ease'
                }}
                title="사진과 EXIF가 포함된 완성형 A4 인쇄 또는 PDF 저장"
              >
                <Printer size={14} />
                <span>인쇄 / PDF</span>
              </button>

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
                    transition: 'all 0.2s ease'
                  }}
                  title="별도 독립 데스크탑 윈도우로 분리"
                >
                  <ExternalLink size={14} />
                  <span>새 창으로 분리</span>
                </button>
              )}

              {/* Maximize / Restore Toggle (Only in modal mode) */}
              {!isPopout && (
                <button
                  onClick={() => setIsMaximized((prev) => !prev)}
                  style={{
                    background: isMaximized ? 'rgba(168, 85, 247, 0.15)' : 'rgba(255, 255, 255, 0.06)',
                    border: `1px solid ${isMaximized ? 'rgba(168, 85, 247, 0.4)' : 'rgba(255, 255, 255, 0.12)'}`,
                    color: isMaximized ? '#c084fc' : '#d4d4d8',
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
                  <div id="critique-rendered-body">
                    <CritiqueContentRenderer content={critiqueText} mode="document" />
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
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
