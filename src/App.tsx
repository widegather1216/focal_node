import { useState } from "react";
import { useAppStore } from "./store/useAppStore";
import { useBackendInit } from "./hooks/useBackendInit";
import { useTauriEvents } from "./hooks/useTauriEvents";
import { useModelDownloadStatus } from "./hooks/useModelDownloadStatus";
import { Sidebar } from "./components/Sidebar";
import { PhotoGallery } from "./components/PhotoGallery";
import { AnalyticsView } from "./components/AnalyticsView";
import { CritiqueView } from "./components/CritiqueView";
import { DetailPanel } from "./components/DetailPanel";
import { ActionBar } from "./components/ActionBar";
import { ModelDownloadModal } from "./components/ModelDownloadModal";
import { FullscreenViewer } from "./components/FullscreenViewer";
import { AppSplash } from "./components/common/AppSplash";
import "./App.css";

function App() {
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const { loading, backendStatus, backendError } = useBackendInit();
  useTauriEvents();
  useModelDownloadStatus();

  const { isDownloadingModel, activeTab } = useAppStore();

  if (loading || backendError) {
    return (
      <AppSplash
        backendStatus={backendStatus}
        backendError={backendError}
        isDownloadingModel={isDownloadingModel}
      />
    );
  }

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', backgroundColor: '#111', position: 'relative' }}>
      <Sidebar onSelectFolder={setSelectedFolder} selectedFolder={selectedFolder} />
      
      {activeTab === 'gallery' ? (
        <PhotoGallery selectedFolder={selectedFolder} />
      ) : activeTab === 'analytics' ? (
        <AnalyticsView />
      ) : (
        <CritiqueView />
      )}

      <DetailPanel />
      <ActionBar />
      
      <ModelDownloadModal isOverlay={true} />
      <FullscreenViewer />
    </div>
  );
}

export default App;
