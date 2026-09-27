import { motion } from 'framer-motion';
import { Loader2, Pause, Play, Square } from 'lucide-react';
import { api } from '../../services/api';

interface IndexingProgressCardProps {
  isIndexing: boolean;
  indexingState: string;
  indexingProgress: { processed: number; total: number; filePath: string } | null;
}

export const IndexingProgressCard: React.FC<IndexingProgressCardProps> = ({
  isIndexing,
  indexingState,
  indexingProgress
}) => {
  if (!isIndexing && !indexingProgress) return null;

  const isPaused = indexingState === 'paused';
  const total = indexingProgress?.total || 0;
  const processed = indexingProgress?.processed || 0;
  const progressPct = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;
  
  const rawPath = indexingProgress?.filePath || '인덱싱 준비 중...';
  const currentFileName = rawPath.includes('/') || rawPath.includes('\\') 
    ? rawPath.split(/[/\\]/).pop() 
    : rawPath;

  const statusTitle = isPaused
    ? '인덱싱 일시정지'
    : total > 0
      ? `사진 인덱싱 중 (${progressPct}%)`
      : '폴더 스캔 중...';

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
        border: isPaused ? '1px solid var(--accent-amber)' : '1px solid var(--border-subtle)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {isPaused ? (
            <Pause size={13} color="var(--accent-amber)" style={{ flexShrink: 0 }} />
          ) : (
            <Loader2 size={13} className="spin" color="var(--accent-focal)" style={{ flexShrink: 0 }} />
          )}
          <span style={{ fontSize: '11px', fontWeight: 600, color: isPaused ? 'var(--accent-amber)' : 'var(--text-primary)' }}>
            {statusTitle}
          </span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {indexingState === 'processing' ? (
            <button
              onClick={async () => {
                try {
                  await api.pauseIndexing();
                } catch (e: any) {
                  console.error("Pause error:", e);
                }
              }}
              style={{ background: 'none', border: 'none', color: 'var(--accent-amber)', cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center' }}
              title="일시정지"
            >
              <Pause size={13} />
            </button>
          ) : (
            <button
              onClick={async () => {
                try {
                  await api.resumeIndexing();
                } catch (e: any) {
                  console.error("Resume error:", e);
                }
              }}
              style={{ background: 'none', border: 'none', color: 'var(--accent-emerald)', cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center' }}
              title="계속 진행"
            >
              <Play size={13} />
            </button>
          )}
          
          <button
            onClick={async () => {
              try {
                await api.cancelIndexing();
              } catch (e: any) {
                console.error("Cancel error:", e);
              }
            }}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center' }}
            title="취소"
          >
            <Square size={11} fill="currentColor" />
          </button>
        </div>
      </div>

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
          backgroundColor: isPaused ? 'var(--accent-amber)' : 'var(--accent-focal)',
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
    </motion.div>
  );
};
