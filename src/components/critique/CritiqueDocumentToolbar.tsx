import React from 'react';
import { FileText, Calendar, ExternalLink, Maximize2, Minimize2, X } from 'lucide-react';
import { PhotoDetail } from '../../hooks/usePhotoDetail';
import { CritiqueToolbarExportMenu } from './CritiqueToolbarExportMenu';

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
        gap: '16px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #e11d48 0%, #be123c 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <FileText size={17} color="#fff" />
        </div>
        <div style={{ overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2
              style={{
                margin: 0,
                fontSize: '15px',
                fontWeight: 700,
                color: '#f4f4f5',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {photo?.file_name || '사진 비평 문서'}
            </h2>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                padding: '2px 7px',
                borderRadius: '6px',
                background: 'var(--accent-focal-subtle)',
                color: 'var(--accent-focal-hover)',
                border: '1px solid rgba(225, 29, 72, 0.3)',
                flexShrink: 0,
              }}
            >
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

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
        <CritiqueToolbarExportMenu
          critiqueText={critiqueText}
          copied={copied}
          exported={exported}
          isExportingMd={isExportingMd}
          isExportingPdf={isExportingPdf}
          pdfExported={pdfExported}
          lastSavedPath={lastSavedPath}
          onCopyText={onCopyText}
          onExportMarkdown={onExportMarkdown}
          onExportPdf={onExportPdf}
          onRevealFile={onRevealFile}
        />

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
              transition: 'all 0.2s ease',
            }}
            title="별도 독립 데스크탑 윈도우로 분리"
          >
            <ExternalLink size={14} style={{ flexShrink: 0 }} />
            <span style={{ whiteSpace: 'nowrap' }}>새 창으로 분리</span>
          </button>
        )}

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
              transition: 'all 0.2s ease',
            }}
            title={isMaximized ? '원래 창 크기로 복원' : '화면 전체로 크게 보기'}
          >
            {isMaximized ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </button>
        )}

        <div style={{ width: '1px', height: '20px', backgroundColor: 'rgba(255, 255, 255, 0.1)', margin: '0 4px' }} />

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
            transition: 'background 0.2s ease, color 0.2s ease',
          }}
          title={isPopout ? '창 닫기 (ESC)' : '모달 닫기 (ESC)'}
        >
          <X size={16} />
        </button>
      </div>
    </header>
  );
};
