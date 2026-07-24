import { useState } from "react";
import { useAppStore } from "./store/useAppStore";
import { useBackendInit } from "./hooks/useBackendInit";
import { useTauriEvents } from "./hooks/useTauriEvents";
import { Sidebar } from "./components/Sidebar";
import { PhotoGallery } from "./components/PhotoGallery";
import { DetailPanel } from "./components/DetailPanel";
import { ActionBar } from "./components/ActionBar";
import { ModelDownloadModal } from "./components/ModelDownloadModal";
import "./App.css";

function App() {
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  
  const { loading, backendStatus, backendError } = useBackendInit();
  useTauriEvents();

  const { isDownloadingModel } = useAppStore();

  if (loading || backendError) {
    return (
      <main className="container" style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", height: "100vh", backgroundColor: '#111', color: '#fff', position: 'relative' }}>
        <style>
          {`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          `}
        </style>
        
        <h1 style={{ marginBottom: '8px', fontSize: '32px' }}>Focal Node</h1>
        
        {!backendError && !isDownloadingModel && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '32px' }}>
            <div style={{ 
              width: '40px', height: '40px', 
              border: '4px solid rgba(255, 255, 255, 0.1)', 
              borderTopColor: '#4ade80', 
              borderRadius: '50%', 
              animation: 'spin 1s linear infinite',
              marginBottom: '16px'
            }} />
            <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>앱 환경을 준비하고 있습니다...</h2>
            <p style={{ color: '#aaa', fontSize: '14px' }}>{backendStatus || "초기 설정 중..."}</p>
          </div>
        )}

        {backendError && (
          <p className="loading-text" style={{ color: '#ff8888', marginTop: '20px', maxWidth: '80%', textAlign: 'center', lineHeight: '1.5' }}>
            에러 발생: {backendError}
          </p>
        )}

        <ModelDownloadModal isOverlay={false} />
      </main>
    );
  }

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', backgroundColor: '#111', position: 'relative' }}>
      <Sidebar onSelectFolder={setSelectedFolder} selectedFolder={selectedFolder} />
      <PhotoGallery selectedFolder={selectedFolder} />
      <DetailPanel />
      <ActionBar />
      
      <ModelDownloadModal isOverlay={true} />
    </div>
  );
}

export default App;
