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
  
  const rawPath = indexingProgress?.filePath || 'Preparing indexing...';
  const currentFileName = rawPath.includes('/') || rawPath.includes('\\') 
    ? rawPath.split(/[/\\]/).pop() 
    : rawPath;

  const statusTitle = isPaused
    ? 'Indexing Paused'
    : total > 0
      ? 'Indexing Photos'
      : 'Scanning Folders...';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      transition={{ duration: 0.25 }}
      style={{
          marginTop: 'auto',
          padding: '14px',
          backgroundColor: isPaused ? 'rgba(234, 179, 8, 0.12)' : 'rgba(0, 0, 0, 0.35)',
          borderRadius: '8px',
          border: isPaused ? '1px solid rgba(234, 179, 8, 0.3)' : '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isPaused ? (
            <span style={{ fontSize: '12px' }}>⏸️</span>
          ) : (
            <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
          )}
          <span style={{ fontSize: '12px', fontWeight: '600', color: isPaused ? '#fde047' : '#fff' }}>
            {statusTitle}
          </span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {indexingState === 'processing' ? (
            <button
              onClick={async () => {
                try {
                  await api.pauseIndexing();
                } catch (e: any) {
                  console.error("Pause error:", e);
                }
              }}
              style={{ background: 'none', border: 'none', color: '#fbbf24', cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center' }}
              title="Pause Indexing"
            >
              <Pause size={14} />
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
              style={{ background: 'none', border: 'none', color: '#4ade80', cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center' }}
              title="Resume Indexing"
            >
              <Play size={14} />
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
            style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center' }}
            title="Cancel Indexing"
          >
            <Square size={12} fill="#ef4444" />
          </button>
        </div>
      </div>

      <div style={{
        width: '100%',
        height: '4px',
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
        borderRadius: '2px',
        marginBottom: '8px',
        overflow: 'hidden'
      }}>
        <div style={{
          width: `${progressPct}%`,
          height: '100%',
          backgroundColor: isPaused ? '#facc15' : '#4ade80',
          transition: 'width 0.3s ease'
        }} />
      </div>
      <div style={{ fontSize: '11px', color: '#aaa', display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
        <span>{total > 0 ? `${processed} / ${total}` : 'Scanning...'}</span>
        <span 
          style={{ maxWidth: '110px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} 
          title={rawPath}
        >
          {currentFileName}
        </span>
      </div>
    </motion.div>
  );
};
