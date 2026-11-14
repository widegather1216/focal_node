import { motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, Loader2, Pause, Play, Square, X } from 'lucide-react';
import { api } from '../../services/api';

interface IndexingProgressCardProps {
  isIndexing: boolean;
  indexingState: string;
  indexingProgress: { processed: number; total: number; filePath: string } | null;
  indexingError: string | null;
  onDismissError: () => void;
}

export const IndexingProgressCard: React.FC<IndexingProgressCardProps> = ({
  isIndexing,
  indexingState,
  indexingProgress,
  indexingError,
  onDismissError,
}) => {
  const isError = indexingState === 'error' || Boolean(indexingError);
  if (!isIndexing && !indexingProgress && !isError) return null;

  const isPaused = indexingState === 'paused';
  const isProcessing = indexingState === 'processing';
  const total = indexingProgress?.total || 0;
  const processed = indexingProgress?.processed || 0;
  const progressPct = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;

  const rawPath = indexingProgress?.filePath || '인덱싱 준비 중...';
  const currentFileName = rawPath.includes('/') || rawPath.includes('\\')
    ? rawPath.split(/[/\\]/).pop()
    : rawPath;

  const statusTitle = isError
    ? '인덱싱 실패'
    : isPaused
      ? '인덱싱 일시정지'
      : isProcessing
        ? total > 0
          ? `사진 인덱싱 중 (${progressPct}%)`
          : '폴더 스캔 중...'
        : '인덱싱 완료';

  const cardBorder = isError
    ? '1px solid rgba(225, 29, 72, 0.45)'
    : isPaused
      ? '1px solid rgba(255, 255, 255, 0.12)'
      : '1px solid var(--border-subtle)';

  const renderStatusIcon = () => {
    if (isError) return <AlertTriangle size={13} color="var(--accent-focal)" style={{ flexShrink: 0 }} />;
    if (isPaused) return <Pause size={13} color="var(--text-secondary)" style={{ flexShrink: 0 }} />;
    if (isProcessing) return <Loader2 size={13} className="spin" color="var(--accent-focal)" style={{ flexShrink: 0 }} />;
    return <CheckCircle2 size={13} color="var(--accent-emerald)" style={{ flexShrink: 0 }} />;
  };

  const runIndexingControlAction = async (actionLabel: string, action: () => Promise<unknown>) => {
    try {
      await action();
    } catch (err: unknown) {
      console.error(`${actionLabel} error:`, err);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      transition={{ duration: 0.2 }}
      style={{
        marginTop: 'auto',
        padding: '12px',
        backgroundColor: 'var(--bg-card)',
        borderRadius: '6px',
        border: cardBorder,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {renderStatusIcon()}
          <span
            style={{
              fontSize: '11px',
              fontWeight: 600,
              color: isError ? '#fda4af' : isPaused ? 'var(--text-secondary)' : 'var(--text-primary)',
            }}
          >
            {statusTitle}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {isError ? (
            <button
              onClick={onDismissError}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center' }}
              title="닫기"
            >
              <X size={13} />
            </button>
          ) : (isProcessing || isPaused) ? (
            <>
              {isProcessing ? (
                <button
                  onClick={() => runIndexingControlAction('Pause', () => api.pauseIndexing())}
                  style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center' }}
                  title="일시정지"
                >
                  <Pause size={13} />
                </button>
              ) : (
                <button
                  onClick={() => runIndexingControlAction('Resume', () => api.resumeIndexing())}
                  style={{ background: 'none', border: 'none', color: 'var(--accent-focal)', cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center' }}
                  title="계속 진행"
                >
                  <Play size={13} />
                </button>
              )}

              <button
                onClick={() => runIndexingControlAction('Cancel', () => api.cancelIndexing())}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center' }}
                title="취소"
              >
                <Square size={11} fill="currentColor" />
              </button>
            </>
          ) : null}
        </div>
      </div>

      {isError ? (
        <>
          <div
            style={{
              fontSize: '11px',
              lineHeight: 1.45,
              color: '#fda4af',
              backgroundColor: 'rgba(225, 29, 72, 0.08)',
              border: '1px solid rgba(225, 29, 72, 0.2)',
              borderRadius: '4px',
              padding: '6px 8px',
              marginBottom: '6px',
              wordBreak: 'break-word',
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
            title={indexingError || undefined}
          >
            {indexingError || '데이터베이스 저장 중 오류가 발생했습니다.'}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
            <span className="font-mono">{total > 0 ? `${processed} / ${total}` : '저장 실패'}</span>
            <span>다시 동기화해 주세요</span>
          </div>
        </>
      ) : (
        <>
          <div style={{
            width: '100%',
            height: '3px',
            backgroundColor: 'rgba(255, 255, 255, 0.08)',
            borderRadius: '2px',
            marginBottom: '6px',
            overflow: 'hidden'
          }}>
            <div style={{
              width: `${progressPct}%`,
              height: '100%',
              backgroundColor: isPaused ? 'rgba(225, 29, 72, 0.4)' : 'var(--accent-focal)',
              transition: 'width 0.25s ease'
            }} />
          </div>

          <div style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
            <span className="font-mono">{total > 0 ? `${processed} / ${total}` : 'Scanning...'}</span>
            <span
              style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              title={rawPath}
            >
              {currentFileName}
            </span>
          </div>
        </>
      )}
    </motion.div>
  );
};
