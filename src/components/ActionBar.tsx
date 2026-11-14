import { AnimatePresence, motion } from 'framer-motion';
import { useAppStore } from '../store/useAppStore';
import { usePhotoExport } from '../hooks/usePhotoExport';
import {
  ExportActionControls,
  ExportStatusLabel,
  getBannerTheme,
} from './actionbar/ExportActionControls';

export function ActionBar() {
  const { selectedPhotoIds, clearSelection } = useAppStore();
  const { exporting, feedback, dismissFeedback, handleExport } = usePhotoExport();

  const theme = getBannerTheme(feedback ? feedback.kind : null);
  const canRecover = feedback?.kind === 'error' || feedback?.kind === 'partial';

  return (
    <AnimatePresence>
      {selectedPhotoIds.size > 0 && (
        <motion.div
          role={canRecover ? 'alert' : 'status'}
          initial={{ y: 100, opacity: 0, x: '-50%' }}
          animate={{ y: 0, opacity: 1, x: '-50%' }}
          exit={{ y: 100, opacity: 0, x: '-50%' }}
          style={{
            position: 'fixed',
            bottom: '24px',
            left: '50%',
            maxWidth: 'calc(100vw - 48px)',
            backgroundColor: theme.backgroundColor,
            border: theme.border,
            color: theme.textColor,
            padding: '8px 16px',
            borderRadius: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            boxShadow: '0 16px 36px rgba(0,0,0,0.7)',
            zIndex: 50,
            backdropFilter: 'blur(16px)',
            userSelect: 'none',
          }}
        >
          <ExportStatusLabel
            feedback={feedback}
            selectedCount={selectedPhotoIds.size}
            textColor={theme.textColor}
          />
          <ExportActionControls
            exporting={exporting}
            canRecover={canRecover}
            showDefaultActions={!feedback}
            textColor={theme.textColor}
            onExport={handleExport}
            onClearSelection={clearSelection}
            onDismissFeedback={dismissFeedback}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
