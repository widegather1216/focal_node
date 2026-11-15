import React from 'react';
import { Copy, Check, Download, FileDown, Loader2, ExternalLink } from 'lucide-react';

interface CritiqueToolbarExportMenuProps {
  critiqueText: string;
  copied: boolean;
  exported: boolean;
  isExportingMd: boolean;
  isExportingPdf: boolean;
  pdfExported: boolean;
  lastSavedPath: string | null;
  onCopyText: () => void;
  onExportMarkdown: () => void;
  onExportPdf: () => void;
  onRevealFile: (path: string) => void;
}

function getActionButtonStyle(isHighlighted: boolean, isEnabled: boolean, isBusy = false): React.CSSProperties {
  return {
    background: isHighlighted ? 'var(--accent-focal-subtle)' : 'rgba(255, 255, 255, 0.06)',
    border: `1px solid ${isHighlighted ? 'var(--accent-focal)' : 'rgba(255, 255, 255, 0.12)'}`,
    color: isHighlighted ? 'var(--accent-focal-hover)' : '#d4d4d8',
    padding: '7px 12px',
    borderRadius: '8px',
    fontSize: '12px',
    fontWeight: 500,
    cursor: isEnabled ? 'pointer' : 'not-allowed',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    whiteSpace: 'nowrap',
    flexShrink: 0,
    transition: 'all 0.2s ease',
    opacity: isBusy ? 0.75 : 1,
  };
}

export const CritiqueToolbarExportMenu: React.FC<CritiqueToolbarExportMenuProps> = ({
  critiqueText,
  copied,
  exported,
  isExportingMd,
  isExportingPdf,
  pdfExported,
  lastSavedPath,
  onCopyText,
  onExportMarkdown,
  onExportPdf,
  onRevealFile,
}) => {
  const canExportMd = Boolean(critiqueText && !isExportingMd);
  const canExportPdf = Boolean(critiqueText && !isExportingPdf);

  return (
    <>
      <button
        onClick={onCopyText}
        disabled={!critiqueText}
        style={getActionButtonStyle(copied, Boolean(critiqueText))}
        title="비평 본문 클립보드 복사"
      >
        {copied ? <Check size={14} style={{ flexShrink: 0 }} /> : <Copy size={14} style={{ flexShrink: 0 }} />}
        <span style={{ whiteSpace: 'nowrap' }}>{copied ? '복사 완료!' : '텍스트 복사'}</span>
      </button>

      <button
        onClick={onExportMarkdown}
        disabled={!canExportMd}
        style={getActionButtonStyle(exported, canExportMd, isExportingMd)}
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

      <button
        onClick={onExportPdf}
        disabled={!canExportPdf}
        style={getActionButtonStyle(pdfExported, canExportPdf, isExportingPdf)}
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
            transition: 'all 0.2s ease',
          }}
          title="저장된 파일 위치를 Finder에서 표시"
        >
          <ExternalLink size={12} style={{ flexShrink: 0 }} />
          <span>폴더 열기</span>
        </button>
      )}
    </>
  );
};
