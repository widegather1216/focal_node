import { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { FolderList } from './sidebar/FolderList';
import { IndexingProgressCard } from './sidebar/IndexingProgressCard';
import { SidebarFolderActions } from './sidebar/SidebarFolderActions';
import { SidebarSearchControls } from './sidebar/SidebarSearchControls';
import { SidebarViewTabs } from './sidebar/SidebarViewTabs';

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
    indexingError,
    searchQuery,
    setSearchQuery,
    searchFilters,
    setSearchFilters,
    folders,
    fetchFolders,
    removeFolder,
    dismissIndexingError,
  } = useAppStore();

  useEffect(() => {
    if (apiPort) {
      fetchFolders();
    }
  }, [apiPort, fetchFolders]);

  return (
    <aside
      className="sidebar"
      style={{
        width: '260px',
        height: '100vh',
        backgroundColor: 'var(--bg-surface)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        padding: '16px 12px',
        boxSizing: 'border-box',
        userSelect: 'none',
      }}
    >
      <div style={{ padding: '0 4px', marginBottom: '14px' }}>
        <SidebarViewTabs activeTab={activeTab} onSelectTab={setActiveTab} />

        <SidebarSearchControls
          searchQuery={searchQuery}
          searchFilters={searchFilters}
          onSearchQueryChange={setSearchQuery}
          onSearchFiltersChange={setSearchFilters}
        />

        <SidebarFolderActions />
      </div>

      <FolderList
        folders={folders}
        selectedFolder={selectedFolder}
        apiPort={apiPort}
        isIndexing={isIndexing}
        onSelectFolder={onSelectFolder}
        setActiveTab={setActiveTab}
        removeFolder={removeFolder}
      />

      <IndexingProgressCard
        isIndexing={isIndexing}
        indexingState={indexingState}
        indexingProgress={indexingProgress}
        indexingError={indexingError}
        onDismissError={dismissIndexingError}
      />
    </aside>
  );
}
