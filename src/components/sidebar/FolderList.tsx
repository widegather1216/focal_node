import React from 'react';
import { motion } from 'framer-motion';
import { Folder, Trash2, Library } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';

interface FolderItem {
  path: string;
}

interface FolderListProps {
  folders: FolderItem[];
  selectedFolder: string | null;
  apiPort: number | null;
  onSelectFolder: (path: string | null) => void;
  setActiveTab: (tab: 'gallery' | 'analytics' | 'critique') => void;
  removeFolder: (path: string) => Promise<void>;
}

export const FolderList: React.FC<FolderListProps> = ({
  folders,
  selectedFolder,
  apiPort,
  onSelectFolder,
  setActiveTab,
  removeFolder
}) => {
  const queryClient = useQueryClient();

  return (
    <div style={{ flex: 1, overflowY: 'auto', paddingRight: '2px' }}>
      <div style={{
        fontSize: '10px',
        fontWeight: 600,
        color: 'var(--text-muted)',
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        padding: '0 8px 6px 8px',
        marginTop: '4px'
      }}>
        Library Folders
      </div>

      {/* All Photos Root Item */}
      <motion.div 
        onClick={() => {
          setActiveTab('gallery');
          onSelectFolder(null);
        }}
        whileHover={{ 
          backgroundColor: selectedFolder === null ? 'var(--bg-elevated)' : 'var(--bg-hover)',
          color: 'var(--text-primary)'
        }}
        whileTap={{ scale: 0.98 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
        style={{
          padding: '7px 10px',
          borderRadius: '6px',
          cursor: 'pointer',
          backgroundColor: selectedFolder === null ? 'var(--bg-elevated)' : 'transparent',
          borderLeft: selectedFolder === null ? '2px solid var(--accent-focal)' : '2px solid transparent',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: selectedFolder === null ? 'var(--text-primary)' : 'var(--text-secondary)',
          transition: 'background-color 0.15s ease'
        }}
      >
        <Library size={14} color={selectedFolder === null ? 'var(--text-primary)' : 'var(--text-muted)'} style={{ flexShrink: 0 }} />
        <span style={{ fontSize: '13px', fontWeight: selectedFolder === null ? 500 : 400, whiteSpace: 'nowrap' }}>모든 사진</span>
      </motion.div>
      
      {/* Individual Indexed Folders */}
      {folders.map(folder => {
        const isSelected = selectedFolder === folder.path;
        const folderName = folder.path.split('/').filter(Boolean).pop() || folder.path;

        return (
          <motion.div 
            key={folder.path}
            whileHover={{ 
              backgroundColor: isSelected ? 'var(--bg-elevated)' : 'var(--bg-hover)' 
            }}
            transition={{ type: "spring", stiffness: 400, damping: 20 }}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 10px',
              borderRadius: '6px',
              backgroundColor: isSelected ? 'var(--bg-elevated)' : 'transparent',
              borderLeft: isSelected ? '2px solid var(--accent-focal)' : '2px solid transparent',
              marginTop: '2px',
              transition: 'background-color 0.15s ease'
            }}
          >
            <motion.div 
              onClick={() => {
                setActiveTab('gallery');
                onSelectFolder(folder.path);
              }}
              whileTap={{ scale: 0.98 }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
                overflow: 'hidden',
                flex: 1
              }}
              title={folder.path}
            >
              <Folder size={14} color={isSelected ? 'var(--text-primary)' : 'var(--text-muted)'} style={{ flexShrink: 0 }} />
              <span style={{ fontSize: '13px', fontWeight: isSelected ? 500 : 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {folderName}
              </span>
            </motion.div>
            
            <motion.button
              onClick={async (e) => {
                e.stopPropagation();
                if (apiPort && confirm(`폴더 "${folderName}" 및 관련 인덱스를 삭제하시겠습니까?`)) {
                  await removeFolder(folder.path);
                  queryClient.invalidateQueries({ queryKey: ['photos'] });
                  queryClient.invalidateQueries({ queryKey: ['analyticsStats'] });
                  if (selectedFolder === folder.path) {
                    onSelectFolder(null);
                  }
                }
              }}
              whileHover={{ scale: 1.1, color: 'var(--accent-focal)' }}
              whileTap={{ scale: 0.9 }}
              transition={{ type: "spring", stiffness: 500, damping: 15 }}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '3px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              title="폴더 제외 (Unindex)"
            >
              <Trash2 size={13} />
            </motion.button>
          </motion.div>
        );
      })}
    </div>
  );
};
