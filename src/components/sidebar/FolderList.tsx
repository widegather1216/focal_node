import React from 'react';
import { motion } from 'framer-motion';
import { Folder, Trash2 } from 'lucide-react';
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
    <div style={{ flex: 1, overflowY: 'auto' }}>
      <motion.div 
        onClick={() => {
          setActiveTab('gallery');
          onSelectFolder(null);
        }}
        whileHover={{ 
          backgroundColor: selectedFolder === null ? 'rgba(255, 255, 255, 0.12)' : 'rgba(255, 255, 255, 0.05)',
          color: '#fff'
        }}
        whileTap={{ scale: 0.98 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
        style={{
          padding: '8px 10px',
          borderRadius: '6px',
          cursor: 'pointer',
          backgroundColor: selectedFolder === null ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          color: selectedFolder === null ? '#fff' : '#aaa',
        }}
      >
        <Folder size={16} />
        <span style={{ fontSize: '14px' }}>All Photos</span>
      </motion.div>
      
      {folders.map(folder => (
        <motion.div 
          key={folder.path}
          whileHover={{ 
            backgroundColor: selectedFolder === folder.path ? 'rgba(255, 255, 255, 0.12)' : 'rgba(255, 255, 255, 0.03)' 
          }}
          transition={{ type: "spring", stiffness: 400, damping: 20 }}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 10px',
            borderRadius: '6px',
            backgroundColor: selectedFolder === folder.path ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
            marginTop: '4px',
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
              gap: '10px',
              color: selectedFolder === folder.path ? '#fff' : '#aaa',
              cursor: 'pointer',
              overflow: 'hidden',
              flex: 1
            }}
            title={folder.path}
          >
            <Folder size={16} style={{ flexShrink: 0 }} />
            <span style={{ fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {folder.path.split('/').filter(Boolean).pop() || folder.path}
            </span>
          </motion.div>
          
          <motion.button
            onClick={async (e) => {
              e.stopPropagation();
              if (apiPort && confirm(`Remove folder ${folder.path} and all its indexed photos?`)) {
                await removeFolder(folder.path);
                queryClient.invalidateQueries({ queryKey: ['photos'] });
                queryClient.invalidateQueries({ queryKey: ['analyticsStats'] });
                if (selectedFolder === folder.path) {
                  onSelectFolder(null);
                }
              }
            }}
            whileHover={{ scale: 1.15, color: '#ff6666' }}
            whileTap={{ scale: 0.9 }}
            transition={{ type: "spring", stiffness: 500, damping: 15 }}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#ff4d4d',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="Remove Folder"
          >
            <Trash2 size={14} />
          </motion.button>
        </motion.div>
      ))}
    </div>
  );
};
