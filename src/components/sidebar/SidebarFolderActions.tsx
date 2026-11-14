import { open } from '@tauri-apps/plugin-dialog';
import { motion } from 'framer-motion';
import { FolderPlus, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';
import { useAppStore } from '../../store/useAppStore';

function extractErrorMessage(err: unknown, fallbackMessage: string): string {
  if (err instanceof Error && err.message.trim()) {
    return err.message;
  }
  return fallbackMessage;
}

export function SidebarFolderActions() {
  const {
    apiPort,
    isIndexing,
    fetchFolders,
    setIsIndexing,
    setIndexingState,
    setIndexingProgress,
    setIndexingError,
  } = useAppStore();

  const beginIndexingState = (statusMessage: string) => {
    setIndexingError(null);
    setIsIndexing(true);
    setIndexingState('processing');
    setIndexingProgress({ processed: 0, total: 0, filePath: statusMessage });
  };

  const resetIndexingState = () => {
    setIsIndexing(false);
    setIndexingState('idle');
    setIndexingProgress(null);
  };

  const handleAddFolder = async () => {
    let selectedPaths: string[] | string | null = null;
    try {
      selectedPaths = await open({ directory: true, multiple: true });
    } catch (dialogErr: unknown) {
      console.error('Failed to open dialog:', dialogErr);
      return;
    }

    if (!selectedPaths || selectedPaths.length === 0) return;
    if (!apiPort) {
      alert('Backend is not connected.');
      return;
    }

    const folderPaths = Array.isArray(selectedPaths) ? selectedPaths : [selectedPaths];
    try {
      beginIndexingState('Scanning directories...');
      await api.startIndexing(folderPaths);
      fetchFolders();
    } catch (startErr: unknown) {
      resetIndexingState();
      alert(`Failed to start indexing: ${extractErrorMessage(startErr, 'Unknown error')}`);
    }
  };

  const handleSyncDatabase = async () => {
    if (!apiPort) return;
    try {
      beginIndexingState('Scanning database folders...');
      await api.syncDatabase();
    } catch (syncErr: unknown) {
      resetIndexingState();
      alert(extractErrorMessage(syncErr, 'Failed to sync database.'));
    }
  };

  return (
    <>
      <motion.button
        onClick={handleAddFolder}
        disabled={isIndexing}
        whileHover={
          isIndexing
            ? {}
            : { scale: 1.01, backgroundColor: 'var(--bg-elevated)', borderColor: 'var(--border-active)' }
        }
        whileTap={isIndexing ? {} : { scale: 0.98 }}
        transition={{ type: 'spring', stiffness: 400, damping: 15 }}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          padding: '8px',
          borderRadius: '6px',
          color: 'var(--text-primary)',
          fontSize: '12px',
          fontWeight: 500,
          cursor: isIndexing ? 'not-allowed' : 'pointer',
          opacity: isIndexing ? 0.5 : 1,
          marginBottom: '8px',
          whiteSpace: 'nowrap',
        }}
      >
        <FolderPlus size={15} color="var(--text-secondary)" style={{ flexShrink: 0 }} />
        <span style={{ whiteSpace: 'nowrap' }}>{isIndexing ? '인덱싱 중...' : '사진 폴더 추가'}</span>
      </motion.button>

      <motion.button
        onClick={handleSyncDatabase}
        disabled={isIndexing}
        whileHover={isIndexing ? {} : { scale: 1.01, backgroundColor: 'rgba(255, 255, 255, 0.03)' }}
        whileTap={isIndexing ? {} : { scale: 0.98 }}
        transition={{ type: 'spring', stiffness: 400, damping: 15 }}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          backgroundColor: 'transparent',
          border: '1px dashed var(--border-subtle)',
          padding: '6px',
          borderRadius: '6px',
          color: 'var(--text-muted)',
          fontSize: '11px',
          cursor: isIndexing ? 'not-allowed' : 'pointer',
          opacity: isIndexing ? 0.5 : 1,
          whiteSpace: 'nowrap',
        }}
      >
        <RefreshCw size={13} className={isIndexing ? 'spin' : ''} style={{ flexShrink: 0 }} />
        <span style={{ whiteSpace: 'nowrap' }}>DB 동기화</span>
      </motion.button>
    </>
  );
}
