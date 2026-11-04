import React from 'react';
import { 
  FileText, 
  Calendar, 
  Copy, 
  Check, 
  Download, 
  FileDown, 
  Loader2, 
  ExternalLink, 
  Maximize2, 
  Minimize2, 
  X 
} from 'lucide-react';
import { PhotoDetail } from '../../hooks/usePhotoDetail';

interface CritiqueDocumentToolbarProps {
  photo: PhotoDetail | null | undefined;
  isPopout: boolean;
  formattedDate: string | null;
  critiqueText: string;
  copied: boolean;
  exported: boolean;
  isExportingMd: boolean;
  isExportingPdf: boolean;
  pdfExported: boolean;
  lastSavedPath: string | null;
  isMaximized: boolean;
  onCopyText: () => void;
  onExportMarkdown: () => void;
  onExportPdf: () => void;
  onRevealFile: (path: string) => void;
  onPopout: () => void;
  onToggleMaximize: () => void;
  onClose: () => void;
}

export const CritiqueDocumentToolbar: React.FC<CritiqueDocumentToolbarProps> = ({
  photo,
  isPopout,
  formattedDate,
  critiqueText,
  copied,
  exported,
  isExportingMd,
  isExportingPdf,
  pdfExported,
  lastSavedPath,
  isMaximized,
  onCopyText,
  onExportMarkdown,
  onExportPdf,
  onRevealFile,
  onPopout,
  onToggleMaximize,
  onClose,
}) => {
  return (
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
          onClick={onCopyText}
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
          onClick={onExportMarkdown}
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
          onClick={onExportPdf}
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

        {/* Reveal saved file in Finder button */}
        {lastSavedPath && (
          <button
            onClick={() => onRevealFile(lastSavedPath)}
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
            onClick={onPopout}
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
            onClick={onToggleMaximize}
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
          onClick={onClose}
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
  );
};
