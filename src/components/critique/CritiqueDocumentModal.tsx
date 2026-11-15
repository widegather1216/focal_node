import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { revealSavedFile } from '../../utils/critiqueExporter';
import { useCritiqueDocumentModal } from '../../hooks/useCritiqueDocumentModal';
import { CritiqueDocumentToolbar } from './CritiqueDocumentToolbar';
import { CritiqueDocumentPhotoViewer } from './CritiqueDocumentPhotoViewer';
import { CritiqueDocumentArticle } from './CritiqueDocumentArticle';
import { CritiqueExportProgressOverlay } from './CritiqueExportProgressOverlay';

interface CritiqueDocumentModalProps {
  isStandalone?: boolean;
}

const PRINT_FALLBACK_STYLES = `
  @media print {
    body { background: #fff !important; color: #111 !important; }
    .no-print { display: none !important; }
    #critique-document-modal { position: static !important; padding: 0 !important; background: #fff !important; }
    .print-paper { background: #fff !important; color: #111 !important; box-shadow: none !important; border: none !important; }
    .print-paper h1, .print-paper h2, .print-paper h3, .print-paper h4, .print-paper strong, .print-paper th {
      color: #111827 !important;
    }
    .print-paper p, .print-paper li, .print-paper td, .print-paper em, .print-paper blockquote,
    .print-paper span:not(.font-mono) {
      color: #374151 !important;
    }
    .print-paper button { display: none !important; }
  }
`;

export const CritiqueDocumentModal: React.FC<CritiqueDocumentModalProps> = ({ isStandalone = false }) => {
  const modal = useCritiqueDocumentModal(isStandalone);

  if (!modal.critiqueDocumentPhotoId) return null;

  return (
    <AnimatePresence>
      <div
        id="critique-document-modal"
        style={{
          position: modal.isPopout ? 'relative' : 'fixed',
          inset: 0,
          zIndex: 999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: modal.isPopout ? '#0e0e11' : 'rgba(4, 4, 6, 0.85)',
          backdropFilter: modal.isPopout ? 'none' : 'blur(16px)',
          padding: modal.isPopout || modal.isMaximized ? 0 : '24px',
          width: '100vw',
          height: '100vh',
          boxSizing: 'border-box',
        }}
        onClick={(event) => {
          if (!modal.isPopout && event.target === event.currentTarget) {
            modal.handleClose();
          }
        }}
      >
        <style>{PRINT_FALLBACK_STYLES}</style>

        <motion.div
          initial={{ opacity: 0, scale: modal.isPopout ? 1 : 0.96, y: modal.isPopout ? 0 : 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: modal.isPopout ? 1 : 0.96, y: modal.isPopout ? 0 : 15 }}
          transition={{ duration: 0.22, ease: 'easeOut' }}
          style={{
            width: '100%',
            maxWidth: modal.isPopout || modal.isMaximized ? '100%' : '1600px',
            height: modal.isPopout || modal.isMaximized ? '100%' : '92vh',
            maxHeight: modal.isPopout || modal.isMaximized ? '100vh' : '1000px',
            backgroundColor: '#0e0e11',
            borderRadius: modal.isPopout || modal.isMaximized ? 0 : '20px',
            border: modal.isPopout || modal.isMaximized ? 'none' : '1px solid rgba(255, 255, 255, 0.1)',
            boxShadow:
              modal.isPopout || modal.isMaximized
                ? 'none'
                : '0 25px 60px -15px rgba(0, 0, 0, 0.7), 0 0 40px rgba(225, 29, 72, 0.12)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            position: 'relative',
          }}
          onClick={(event) => event.stopPropagation()}
        >
          <CritiqueDocumentToolbar
            photo={modal.photo}
            isPopout={modal.isPopout}
            formattedDate={modal.formattedDate}
            critiqueText={modal.critiqueText}
            copied={modal.copied}
            exported={modal.exported}
            isExportingMd={modal.isExportingMd}
            isExportingPdf={modal.isExportingPdf}
            pdfExported={modal.pdfExported}
            lastSavedPath={modal.lastSavedPath}
            isMaximized={modal.isMaximized}
            onCopyText={modal.handleCopyText}
            onExportMarkdown={modal.handleExportMarkdown}
            onExportPdf={modal.handleExportPdf}
            onRevealFile={revealSavedFile}
            onPopout={modal.handlePopout}
            onToggleMaximize={() => modal.setIsMaximized((prev) => !prev)}
            onClose={modal.handleClose}
          />

          <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
            <CritiqueDocumentPhotoViewer
              photo={modal.photo}
              imageUrl={modal.imageUrl}
              scale={modal.zoomPan.scale}
              position={modal.zoomPan.position}
              isDragging={modal.zoomPan.isDragging}
              onWheel={modal.zoomPan.handleWheel}
              onMouseDown={modal.zoomPan.handleMouseDown}
              onMouseMove={modal.zoomPan.handleMouseMove}
              onMouseUp={modal.zoomPan.handleMouseUp}
              onResetZoom={modal.zoomPan.handleResetZoom}
              onZoomIn={modal.zoomPan.zoomIn}
              onZoomOut={modal.zoomPan.zoomOut}
              onImageError={() => modal.setImgError(true)}
            />

            <CritiqueDocumentArticle
              photo={modal.photo}
              isLoading={modal.isLoading}
              critiqueText={modal.critiqueText}
              mastheadData={modal.mastheadSummary}
            />
          </div>

          <CritiqueExportProgressOverlay
            exportProgress={modal.exportProgress}
            photoName={modal.photo?.file_name}
            lastSavedPath={modal.lastSavedPath}
            onRevealFile={revealSavedFile}
            onClose={() => modal.setExportProgress((prev) => ({ ...prev, active: false }))}
          />
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
