import { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { open } from '@tauri-apps/plugin-dialog';
import { FolderPlus, Folder, Loader2, Search, RefreshCw, Trash2, Heart } from 'lucide-react';
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
          <button
            onClick={() => {
              const { is_favorite, ...rest } = searchFilters;
              if (is_favorite) {
                setSearchFilters(rest);
              } else {
                setSearchFilters({ ...rest, is_favorite: true });
              }
            }}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: '36px', height: '36px',
              backgroundColor: searchFilters.is_favorite ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 255, 255, 0.05)',
              border: searchFilters.is_favorite ? '1px solid #ef4444' : '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s', flexShrink: 0
            }}
            title="즐겨찾기 모아보기"
          >
            <Heart size={16} fill={searchFilters.is_favorite ? '#ef4444' : 'none'} color={searchFilters.is_favorite ? '#ef4444' : '#aaa'} />
          </button>
        </div>

        <button 
          onClick={handleAddFolder}
          disabled={isIndexing}
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
            transition: 'background-color 0.2s',
            marginBottom: '10px'
          }}
        >
          <FolderPlus size={18} />
          {isIndexing ? 'Indexing...' : 'Add Photos'}
        </button>

        <button 
          onClick={async () => {
            if (!apiPort) return;
            try {
              await api.syncDatabase();
            } catch (e: any) {
              alert(e.message);
            }
          }}
          disabled={isIndexing}
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
            opacity: isIndexing ? 0.5 : 1,
            transition: 'background-color 0.2s'
          }}
        >
          <RefreshCw size={16} />
          Sync Database
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        <div 
          onClick={() => onSelectFolder(null)}
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
        </div>
        
        {folders.map(folder => (
          <div 
            key={folder.path}
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
            <div 
              onClick={() => onSelectFolder(folder.path)}
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
            </div>
            
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (apiPort && confirm(`Remove folder ${folder.path} and all its indexed photos?`)) {
                  removeFolder(folder.path);
                  if (selectedFolder === folder.path) {
                    onSelectFolder(null);
                  }
                }
              }}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#ff4d4d',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                opacity: 0.7,
                transition: 'opacity 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
              title="Remove Folder"
            >
              <Trash2 size={14} />
            </button>
          </div>
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
