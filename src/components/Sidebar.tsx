import { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { open } from '@tauri-apps/plugin-dialog';
import { FolderPlus, Folder, Loader2, Search, RefreshCw, Trash2, Heart } from 'lucide-react';
import { motion } from 'framer-motion';
import { SearchFilterMenu } from './SearchFilterMenu';
import { api } from '../services/api';

interface SidebarProps {
  onSelectFolder: (folderPath: string | null) => void;
  selectedFolder: string | null;
}

export function Sidebar({ onSelectFolder, selectedFolder }: SidebarProps) {
  const { apiPort, isIndexing, indexingProgress, searchQuery, setSearchQuery, searchFilters, setSearchFilters, folders, fetchFolders, removeFolder, setIsIndexing, setIndexingProgress } = useAppStore();

  useEffect(() => {
    if (apiPort) {
      fetchFolders();
    }
  }, [apiPort, fetchFolders]);

  const handleAddFolder = async () => {
    try {
      const selected = await open({
        directory: true,
        multiple: true,
      });
      
      if (selected && selected.length > 0) {
        const folderPaths = selected;
        if (!apiPort) {
          alert("Backend is not connected.");
          return;
        }

        try {
          setIsIndexing(true);
          setIndexingProgress({ processed: 0, total: 0, filePath: "Scanning directories..." });
          await api.startIndexing(folderPaths);
          fetchFolders();
        } catch (err: any) {
          setIsIndexing(false);
          setIndexingProgress(null);
          alert(`Failed to start indexing: ${err.message}`);
        }
      }
    } catch (error) {
      console.error("Failed to open dialog:", error);
    }
  };

  return (
    <div className="sidebar" style={{
      width: '260px',
      height: '100vh',
      backgroundColor: 'rgba(25, 25, 25, 0.95)',
      borderRight: '1px solid rgba(255, 255, 255, 0.1)',
      display: 'flex',
      flexDirection: 'column',
      padding: '20px 10px',
      boxSizing: 'border-box'
    }}>
      <div style={{ padding: '0 10px', marginBottom: '20px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: '600', margin: '0 0 16px 0', color: '#fff' }}>Focal Node</h2>
        
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={16} color="#aaa" style={{ position: 'absolute', left: '10px', top: '10px' }} />
            <input 
              type="text" 
              placeholder="Search photos..." 
              value={searchQuery.startsWith('similar:') ? '✨ 유사의미지 검색 중...' : searchQuery}
              onChange={(e) => {
                if (searchQuery.startsWith('similar:')) {
                  setSearchQuery('');
                } else {
                  setSearchQuery(e.target.value);
                }
              }}
              style={{
                width: '100%',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '8px',
                padding: '8px 10px 8px 32px',
                color: '#fff',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
          </div>
          <SearchFilterMenu />
          <motion.button
            onClick={() => {
              const { is_favorite, ...rest } = searchFilters;
              if (is_favorite) {
                setSearchFilters(rest);
              } else {
                setSearchFilters({ ...rest, is_favorite: true });
              }
            }}
            whileHover={{ 
              scale: 1.05, 
              y: -1,
              backgroundColor: searchFilters.is_favorite ? 'rgba(239, 68, 68, 0.25)' : 'rgba(255, 255, 255, 0.08)'
            }}
            whileTap={{ scale: 0.92 }}
            transition={{ type: "spring", stiffness: 400, damping: 15 }}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: '36px', height: '36px',
              backgroundColor: searchFilters.is_favorite ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 255, 255, 0.05)',
              border: searchFilters.is_favorite ? '1px solid #ef4444' : '1px solid rgba(255, 255, 255, 0.2)',
              boxShadow: searchFilters.is_favorite ? '0 0 12px rgba(239, 68, 68, 0.4)' : 'none',
              borderRadius: '8px', cursor: 'pointer', flexShrink: 0
            }}
            title="즐겨찾기 모아보기"
          >
            <motion.div
              key={searchFilters.is_favorite ? "fav-active" : "fav-inactive"}
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 500, damping: 12 }}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <Heart 
                size={19} 
                fill={searchFilters.is_favorite ? '#ef4444' : 'rgba(239, 68, 68, 0.08)'} 
                color={searchFilters.is_favorite ? '#ef4444' : 'rgba(255, 255, 255, 0.5)'} 
              />
            </motion.div>
          </motion.button>
        </div>

        <motion.button 
          onClick={handleAddFolder}
          disabled={isIndexing}
          whileHover={isIndexing ? {} : { 
            scale: 1.02, 
            backgroundColor: 'rgba(255, 255, 255, 0.15)' 
          }}
          whileTap={isIndexing ? {} : { scale: 0.98 }}
          transition={{ type: "spring", stiffness: 400, damping: 15 }}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            padding: '10px',
            borderRadius: '8px',
            color: '#fff',
            cursor: isIndexing ? 'not-allowed' : 'pointer',
            opacity: isIndexing ? 0.5 : 1,
            marginBottom: '10px'
          }}
        >
          <FolderPlus size={18} />
          {isIndexing ? 'Indexing...' : 'Add Photos'}
        </motion.button>

        <motion.button 
          onClick={async () => {
            if (!apiPort) return;
            try {
              await api.syncDatabase();
            } catch (e: any) {
              alert(e.message);
            }
          }}
          disabled={isIndexing}
          whileHover={isIndexing ? {} : { 
            scale: 1.02, 
            backgroundColor: 'rgba(255, 255, 255, 0.08)' 
          }}
          whileTap={isIndexing ? {} : { scale: 0.98 }}
          transition={{ type: "spring", stiffness: 400, damping: 15 }}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            backgroundColor: 'transparent',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            padding: '10px',
            borderRadius: '8px',
            color: '#ccc',
            cursor: isIndexing ? 'not-allowed' : 'pointer',
            opacity: isIndexing ? 0.5 : 1
          }}
        >
          <RefreshCw size={16} />
          Sync Database
        </motion.button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        <motion.div 
          onClick={() => onSelectFolder(null)}
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
              onClick={() => onSelectFolder(folder.path)}
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
              onClick={(e) => {
                e.stopPropagation();
                if (apiPort && confirm(`Remove folder ${folder.path} and all its indexed photos?`)) {
                  removeFolder(folder.path);
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

      {isIndexing && indexingProgress && (
        <div style={{
          marginTop: 'auto',
          padding: '16px',
          backgroundColor: 'rgba(0, 0, 0, 0.3)',
          borderRadius: '8px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Loader2 size={16} className="spinner" style={{ animation: 'spin 1s linear infinite' }} />
            <span style={{ fontSize: '12px', fontWeight: '600' }}>Indexing Photos</span>
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
              width: `${(indexingProgress.processed / Math.max(1, indexingProgress.total)) * 100}%`,
              height: '100%',
              backgroundColor: '#4ade80',
              transition: 'width 0.3s ease'
            }} />
          </div>
          <div style={{ fontSize: '11px', color: '#aaa', display: 'flex', justifyContent: 'space-between' }}>
            <span>{indexingProgress.processed} / {indexingProgress.total}</span>
            <span style={{ maxWidth: '80px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={indexingProgress.filePath}>
              {indexingProgress.filePath.split('/').pop()}
            </span>
          </div>
        </div>
      )}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
