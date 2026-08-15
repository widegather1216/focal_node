import { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { open } from '@tauri-apps/plugin-dialog';
import { FolderPlus, Search, RefreshCw, Heart, BarChart3, Image as ImageIcon, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import { SearchFilterMenu } from './SearchFilterMenu';
import { FolderList } from './sidebar/FolderList';
import { IndexingProgressCard } from './sidebar/IndexingProgressCard';
import { api } from '../services/api';

interface SidebarProps {
  onSelectFolder: (folderPath: string | null) => void;
  selectedFolder: string | null;
}

export function Sidebar({ onSelectFolder, selectedFolder }: SidebarProps) {
  const { 
    apiPort, 
    activeTab,
    setActiveTab,
    isIndexing, 
    indexingState, 
    indexingProgress, 
    searchQuery, 
    setSearchQuery, 
    searchFilters, 
    setSearchFilters, 
    folders, 
    fetchFolders, 
    removeFolder, 
    setIsIndexing, 
    setIndexingState,
    setIndexingProgress 
  } = useAppStore();

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
      <div style={{ padding: '0 10px', marginBottom: '16px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: '600', margin: '0 0 12px 0', color: '#fff' }}>Focal Node</h2>
        
        {/* View Switcher Tabs */}
        <div style={{ display: 'flex', gap: '4px', marginBottom: '16px', background: '#09090b', padding: '4px', borderRadius: '8px', border: '1px solid #27272a' }}>
          <button
            onClick={() => setActiveTab('gallery')}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '4px',
              background: activeTab === 'gallery' ? '#27272a' : 'transparent',
              color: activeTab === 'gallery' ? '#fff' : '#a1a1aa',
              border: 'none',
              padding: '6px 4px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
            <ImageIcon size={14} />
            <span>갤러리</span>
          </button>

          <button
            onClick={() => setActiveTab('analytics')}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '4px',
              background: activeTab === 'analytics' ? '#27272a' : 'transparent',
              color: activeTab === 'analytics' ? '#38bdf8' : '#a1a1aa',
              border: 'none',
              padding: '6px 4px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
            <BarChart3 size={14} />
            <span>분석</span>
          </button>

          <button
            onClick={() => setActiveTab('critique')}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '4px',
              background: activeTab === 'critique' ? '#27272a' : 'transparent',
              color: activeTab === 'critique' ? '#c084fc' : '#a1a1aa',
              border: 'none',
              padding: '6px 4px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
            <Sparkles size={14} />
            <span>AI 비평</span>
          </button>
        </div>

        {/* Search & Filter Inputs (Only active in Gallery Tab) */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={16} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#888' }} />
            <input 
              type="text" 
              placeholder="자연어/유사검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                backgroundColor: '#333',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                padding: '8px 8px 8px 32px',
                color: '#fff',
                fontSize: '13px',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
          </div>
          
          <SearchFilterMenu />

          {/* Favorite Toggle Button */}
          <motion.button
            onClick={() => {
              setSearchFilters({
                ...searchFilters,
                is_favorite: searchFilters.is_favorite ? undefined : true
              });
            }}
            whileHover={{ scale: 1.08, y: -1 }}
            whileTap={{ scale: 0.9 }}
            transition={{ type: "spring", stiffness: 500, damping: 15 }}
            style={{
              backgroundColor: searchFilters.is_favorite ? 'rgba(239, 68, 68, 0.25)' : 'rgba(255, 255, 255, 0.05)',
              border: `1px solid ${searchFilters.is_favorite ? '#ef4444' : 'rgba(255, 255, 255, 0.2)'}`,
              boxShadow: searchFilters.is_favorite ? '0 0 10px rgba(239, 68, 68, 0.4)' : 'none',
              borderRadius: '8px',
              padding: '8px',
              color: searchFilters.is_favorite ? '#ef4444' : '#aaa',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '34px',
              width: '34px',
              outline: 'none',
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
            backgroundColor: 'rgba(255, 255, 255, 0.15)',
            boxShadow: '0 0 12px rgba(255, 255, 255, 0.1)'
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
              setIsIndexing(true);
              setIndexingState('processing');
              setIndexingProgress({ processed: 0, total: 0, filePath: "Scanning database folders..." });
              await api.syncDatabase();
            } catch (e: any) {
              setIsIndexing(false);
              setIndexingState('idle');
              setIndexingProgress(null);
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

      <FolderList
        folders={folders}
        selectedFolder={selectedFolder}
        apiPort={apiPort}
        onSelectFolder={onSelectFolder}
        setActiveTab={setActiveTab}
        removeFolder={removeFolder}
      />

      <IndexingProgressCard
        isIndexing={isIndexing}
        indexingState={indexingState}
        indexingProgress={indexingProgress}
      />
    </div>
  );
}
