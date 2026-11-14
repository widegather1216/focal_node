import { motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, Download, Loader2, RotateCcw, X } from 'lucide-react';
import { ExportFeedback, ExportOutcomeKind } from '../../utils/exportStream';

export interface BannerTheme {
  border: string;
  backgroundColor: string;
  textColor: string;
}

export function getBannerTheme(feedbackKind: ExportOutcomeKind | null): BannerTheme {
  if (feedbackKind === 'error') {
    return {
      border: '1px solid rgba(225, 29, 72, 0.55)',
      backgroundColor: 'rgba(32, 14, 20, 0.95)',
      textColor: '#fda4af',
    };
  }
  if (feedbackKind === 'partial') {
    return {
      border: '1px solid rgba(245, 158, 11, 0.5)',
      backgroundColor: 'rgba(28, 20, 12, 0.95)',
      textColor: '#fde68a',
    };
  }
  if (feedbackKind === 'success') {
    return {
      border: '1px solid rgba(16, 185, 129, 0.45)',
      backgroundColor: 'rgba(18, 18, 21, 0.94)',
      textColor: 'var(--text-primary)',
    };
  }
  return {
    border: '1px solid var(--border-subtle)',
    backgroundColor: 'rgba(18, 18, 21, 0.92)',
    textColor: 'var(--text-primary)',
  };
}

function FeedbackIcon({ kind }: { kind: ExportOutcomeKind }) {
  if (kind === 'error') {
    return <AlertTriangle size={14} color="var(--accent-focal-hover)" style={{ flexShrink: 0 }} />;
  }
  if (kind === 'partial') {
    return <AlertTriangle size={14} color="var(--accent-amber)" style={{ flexShrink: 0 }} />;
  }
  return <CheckCircle2 size={14} color="var(--accent-emerald)" style={{ flexShrink: 0 }} />;
}

interface ExportStatusLabelProps {
  feedback: ExportFeedback | null;
  selectedCount: number;
  textColor: string;
}

export function ExportStatusLabel({ feedback, selectedCount, textColor }: ExportStatusLabelProps) {
  return (
    <span
      title={feedback?.detail ? `${feedback.message}\n${feedback.detail}` : feedback?.message}
      style={{
        fontWeight: 500,
        fontSize: '12px',
        color: textColor,
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        minWidth: 0,
      }}
    >
      {feedback ? (
        <>
          <FeedbackIcon kind={feedback.kind} />
          <span
            style={{
              maxWidth: '420px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {feedback.message}
          </span>
        </>
      ) : (
        <>
          <span className="font-mono" style={{ fontWeight: 700, color: 'var(--accent-focal)' }}>
            {selectedCount}
          </span>
          <span style={{ color: 'var(--text-secondary)' }}>장의 사진 선택됨</span>
        </>
      )}
    </span>
  );
}

interface ExportActionControlsProps {
  exporting: boolean;
  canRecover: boolean;
  showDefaultActions: boolean;
  textColor: string;
  onExport: () => void;
  onClearSelection: () => void;
  onDismissFeedback: () => void;
}

export function ExportActionControls({
  exporting,
  canRecover,
  showDefaultActions,
  textColor,
  onExport,
  onClearSelection,
  onDismissFeedback,
}: ExportActionControlsProps) {
  if (showDefaultActions) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
        <motion.button
          onClick={onExport}
          disabled={exporting}
          whileHover={exporting ? {} : { scale: 1.02, backgroundColor: 'var(--accent-focal-hover)' }}
          whileTap={exporting ? {} : { scale: 0.97 }}
          transition={{ type: 'spring', stiffness: 400, damping: 15 }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'var(--accent-focal)',
            color: '#fff',
            border: 'none',
            padding: '6px 14px',
            borderRadius: '16px',
            cursor: exporting ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            fontSize: '12px',
          }}
        >
          {exporting ? <Loader2 size={13} className="spin" /> : <Download size={13} />}
          {exporting ? '내보내는 중...' : '내보내기'}
        </motion.button>

        <motion.button
          onClick={onClearSelection}
          disabled={exporting}
          whileHover={exporting ? {} : { scale: 1.1, backgroundColor: 'var(--bg-elevated)', color: 'var(--text-primary)' }}
          whileTap={exporting ? {} : { scale: 0.9 }}
          transition={{ type: 'spring', stiffness: 500, damping: 15 }}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'var(--bg-card)',
            color: 'var(--text-muted)',
            border: '1px solid var(--border-subtle)',
            padding: '6px',
            borderRadius: '50%',
            cursor: exporting ? 'not-allowed' : 'pointer',
            opacity: exporting ? 0.5 : 1,
          }}
          title="선택 해제"
        >
          <X size={13} />
        </motion.button>
      </div>
    );
  }

  if (!canRecover) return null;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
      <button
        onClick={onExport}
        disabled={exporting}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '5px',
          backgroundColor: 'var(--accent-focal)',
          color: '#fff',
          border: 'none',
          padding: '5px 12px',
          borderRadius: '14px',
          cursor: exporting ? 'not-allowed' : 'pointer',
          fontWeight: 600,
          fontSize: '11px',
        }}
      >
        <RotateCcw size={12} />
        다시 시도
      </button>
      <button
        onClick={onDismissFeedback}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(255, 255, 255, 0.08)',
          color: textColor,
          border: '1px solid rgba(255, 255, 255, 0.14)',
          padding: '5px',
          borderRadius: '50%',
          cursor: 'pointer',
        }}
        title="알림 닫기"
      >
        <X size={12} />
      </button>
    </div>
  );
}
