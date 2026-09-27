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
          setIndexingState('processing');
          setIndexingProgress({ processed: 0, total: 0, filePath: "Scanning directories..." });
          await api.startIndexing(folderPaths);
          fetchFolders();
        } catch (err: any) {
          setIsIndexing(false);
          setIndexingState('idle');
          setIndexingProgress(null);
          alert(`Failed to start indexing: ${err.message}`);
        }
      }
    } catch (error) {
      console.error("Failed to open dialog:", error);
    }
  };

  return (
    <aside className="sidebar" style={{
      width: '260px',
      height: '100vh',
      backgroundColor: 'var(--bg-surface)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      padding: '16px 12px',
      boxSizing: 'border-box',
      userSelect: 'none'
    }}>
      <div style={{ padding: '0 4px', marginBottom: '14px' }}>
        {/* Brand Header with Camera Red Dot Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: 'var(--accent-focal)',
            boxShadow: '0 0 10px rgba(225, 29, 72, 0.7)'
          }} />
          <h2 style={{
            fontSize: '15px',
            fontWeight: 600,
            margin: 0,
            color: 'var(--text-primary)',
            letterSpacing: '-0.02em',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            Focal Node
            <span style={{ fontSize: '10px', fontWeight: 500, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>PRO</span>
          </h2>
        </div>
        
        {/* View Switcher Tabs */}
        <div style={{
          display: 'flex',
          gap: '2px',
          marginBottom: '14px',
          background: 'var(--bg-canvas)',
          padding: '3px',
          borderRadius: '8px',
          border: '1px solid var(--border-subtle)'
        }}>
          <button
            onClick={() => setActiveTab('gallery')}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '4px',
              background: activeTab === 'gallery' ? 'var(--bg-elevated)' : 'transparent',
              color: activeTab === 'gallery' ? 'var(--text-primary)' : 'var(--text-secondary)',
              border: activeTab === 'gallery' ? '1px solid rgba(255, 255, 255, 0.08)' : '1px solid transparent',
              padding: '6px 2px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              flexShrink: 0,
              transition: 'all 0.15s ease'
            }}
          >
            <ImageIcon size={13} style={{ flexShrink: 0 }} />
            <span style={{ whiteSpace: 'nowrap' }}>갤러리</span>
          </button>

          <button
            onClick={() => setActiveTab('analytics')}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '4px',
              background: activeTab === 'analytics' ? 'var(--bg-elevated)' : 'transparent',
              color: activeTab === 'analytics' ? 'var(--text-primary)' : 'var(--text-secondary)',
              border: activeTab === 'analytics' ? '1px solid rgba(255, 255, 255, 0.08)' : '1px solid transparent',
              padding: '6px 2px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              flexShrink: 0,
              transition: 'all 0.15s ease'
            }}
          >
            <BarChart3 size={13} style={{ flexShrink: 0 }} />
            <span style={{ whiteSpace: 'nowrap' }}>장비 분석</span>
          </button>

          <button
            onClick={() => setActiveTab('critique')}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '4px',
              background: activeTab === 'critique' ? 'var(--bg-elevated)' : 'transparent',
              color: activeTab === 'critique' ? 'var(--text-primary)' : 'var(--text-secondary)',
              border: activeTab === 'critique' ? '1px solid rgba(255, 255, 255, 0.08)' : '1px solid transparent',
              padding: '6px 2px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 500,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              flexShrink: 0,
              transition: 'all 0.15s ease'
            }}
          >
            <Sparkles size={13} style={{ flexShrink: 0 }} />
            <span style={{ whiteSpace: 'nowrap' }}>AI 비평</span>
          </button>
        </div>

        {/* Search & Filter Inputs (Active for Gallery) */}
        <div style={{ display: 'flex', gap: '6px', marginBottom: '14px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input 
              type="text" 
              placeholder="자연어 / 무드 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '7px 8px 7px 30px',
                color: 'var(--text-primary)',
                fontSize: '12px',
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
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.92 }}
            transition={{ type: "spring", stiffness: 500, damping: 15 }}
            style={{
              backgroundColor: searchFilters.is_favorite ? 'var(--accent-focal-subtle)' : 'var(--bg-card)',
              border: `1px solid ${searchFilters.is_favorite ? 'var(--accent-focal)' : 'var(--border-subtle)'}`,
              boxShadow: searchFilters.is_favorite ? '0 0 10px rgba(225, 29, 72, 0.35)' : 'none',
              borderRadius: '6px',
              padding: '7px',
              color: searchFilters.is_favorite ? 'var(--accent-focal)' : 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '32px',
              width: '32px',
              outline: 'none',
            }}
            title="즐겨찾기 필터"
          >
            <motion.div
              key={searchFilters.is_favorite ? "fav-active" : "fav-inactive"}
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 500, damping: 12 }}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <Heart 
                size={15} 
                fill={searchFilters.is_favorite ? 'var(--accent-focal)' : 'none'} 
                color={searchFilters.is_favorite ? 'var(--accent-focal)' : 'currentColor'} 
              />
            </motion.div>
          </motion.button>
        </div>

        {/* Action Buttons: Add Photos & Sync */}
        <motion.button 
          onClick={handleAddFolder}
          disabled={isIndexing}
          whileHover={isIndexing ? {} : { scale: 1.01, backgroundColor: 'var(--bg-elevated)', borderColor: 'var(--border-active)' }}
          whileTap={isIndexing ? {} : { scale: 0.98 }}
          transition={{ type: "spring", stiffness: 400, damping: 15 }}
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
            whiteSpace: 'nowrap'
          }}
        >
          <FolderPlus size={15} color="var(--text-secondary)" style={{ flexShrink: 0 }} />
          <span style={{ whiteSpace: 'nowrap' }}>{isIndexing ? '인덱싱 중...' : '사진 폴더 추가'}</span>
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
          whileHover={isIndexing ? {} : { scale: 1.01, backgroundColor: 'rgba(255, 255, 255, 0.03)' }}
          whileTap={isIndexing ? {} : { scale: 0.98 }}
          transition={{ type: "spring", stiffness: 400, damping: 15 }}
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
            whiteSpace: 'nowrap'
          }}
        >
          <RefreshCw size={13} className={isIndexing ? 'spin' : ''} style={{ flexShrink: 0 }} />
          <span style={{ whiteSpace: 'nowrap' }}>DB 동기화</span>
        </motion.button>
      </div>

      {/* Folder Tree List */}
      <FolderList
        folders={folders}
        selectedFolder={selectedFolder}
        apiPort={apiPort}
        onSelectFolder={onSelectFolder}
        setActiveTab={setActiveTab}
        removeFolder={removeFolder}
      />

      {/* Indexing Status Drawer */}
      <IndexingProgressCard
        isIndexing={isIndexing}
        indexingState={indexingState}
        indexingProgress={indexingProgress}
      />
    </aside>
  );
}
