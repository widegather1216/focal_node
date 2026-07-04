import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "./store/useAppStore";
import { Sidebar } from "./components/Sidebar";
import { PhotoGallery } from "./components/PhotoGallery";
import { DetailPanel } from "./components/DetailPanel";
import { ActionBar } from "./components/ActionBar";
import "./App.css";

function App() {
  const [loading, setLoading] = useState(true);
  
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);

  const { 
    apiPort,
    setApiPort, 
    backendStatus, setBackendStatus, 
    backendError, setBackendError,
    setIsIndexing, setIndexingProgress,
    isDownloadingModel, setIsDownloadingModel,
    downloadProgress, setDownloadProgress,
    downloadModelName, setDownloadModelName
  } = useAppStore();
  const queryClient = useQueryClient();

  useEffect(() => {
    async function initBackend() {
      try {
        setBackendStatus("Waiting for Backend Port...");
        const port = await invoke<number>("get_api_port");
        setApiPort(port);
        setBackendStatus(`Port acquired: ${port}. Checking API health...`);

        const response = await fetch(`http://127.0.0.1:${port}/api/health`);
        if (response.ok) {
          const data = await response.json();
          if (data.status === "ok") {
            setBackendStatus("Backend API Online ✅");
          } else {
            setBackendStatus("Backend API response abnormal ⚠️");
          }
        } else {
          setBackendStatus(`Backend API returned error code ${response.status} ❌`);
        }
      } catch (err: any) {
        console.error("Failed to initialize backend:", err);
        setBackendError(err.toString());
        setBackendStatus("Backend connection failed ❌");
      } finally {
        setLoading(false);
      }
    }

    initBackend();

    const unlistenProgress = listen<{ processed: number; total: number; file_path: string }>(
      "indexing-progress",
      (event) => {
        setIsIndexing(true);
        setIndexingProgress({
          processed: event.payload.processed,
          total: event.payload.total,
          filePath: event.payload.file_path,
        });

        // Progressive loading: refresh gallery every 100 items
        if (event.payload.processed % 100 === 0) {
          // Delay invalidation slightly to allow the backend's DB batch commit to finish
          setTimeout(() => {
            queryClient.invalidateQueries({ queryKey: ['photos'] });
          }, 1500);
        }
      }
    );

    const unlistenCompleted = listen("indexing-completed", () => {
      setIsIndexing(false);
      setIndexingProgress(null);
      // Refresh the gallery to show the newly indexed photos
      queryClient.invalidateQueries({ queryKey: ['photos'] });
    });

    const unlistenSync = listen("sync-completed", () => {
      // Refresh the gallery to reflect deleted photos
      queryClient.invalidateQueries({ queryKey: ['photos'] });
    });

    const unlistenDownloadStarted = listen<string>("model-download-started", (event) => {
      setIsDownloadingModel(true);
      setDownloadProgress(0);
      if (event.payload) {
        setDownloadModelName(event.payload);
      }
    });

    const unlistenDownloadProgress = listen<number>("model-download-progress", (event) => {
      setDownloadProgress(event.payload);
    });

    const unlistenDownloadCompleted = listen("model-download-completed", () => {
      setIsDownloadingModel(false);
    });

    return () => {
      unlistenProgress.then((unlisten) => unlisten());
      unlistenCompleted.then((unlisten) => unlisten());
      unlistenSync.then((unlisten) => unlisten());
      unlistenDownloadStarted.then((unlisten) => unlisten());
      unlistenDownloadProgress.then((unlisten) => unlisten());
      unlistenDownloadCompleted.then((unlisten) => unlisten());
    };
  }, [setIsIndexing, setIndexingProgress, queryClient, setApiPort, setBackendStatus, setBackendError, setIsDownloadingModel, setDownloadProgress, setDownloadModelName]);

  // Continuous health ping to detect backend SIGKILL (Out of Memory crashes)
  useEffect(() => {
    if (!apiPort) return;

    const interval = setInterval(async () => {
      try {
        await fetch(`http://127.0.0.1:${apiPort}/api/health`, { method: 'GET' });
      } catch (err) {
        console.error("Health ping failed. Backend may have crashed.", err);
        setBackendError("백엔드 서버와 통신이 끊어졌습니다. (메모리 부족 등으로 AI 엔진이 강제 종료되었을 수 있습니다.) 앱을 재시작해주세요.");
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [apiPort, setBackendError]);

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

        {isDownloadingModel && (
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(17, 17, 17, 0.95)', zIndex: 9999,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            color: '#fff', padding: '40px'
          }}>
            <h2 style={{ marginBottom: '16px', fontSize: '24px' }}>{downloadModelName} 다운로드 중...</h2>
            <p style={{ marginBottom: '32px', color: '#aaa', textAlign: 'center', maxWidth: '400px', lineHeight: '1.5' }}>
              고품질 사진 분석을 위한 모델을 백그라운드에서 다운로드하고 있습니다.<br/>네트워크 환경에 따라 다소 시간이 소요될 수 있습니다. (최초 1회만 실행)
            </p>
            <div style={{ width: '400px', height: '8px', backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: '4px', overflow: 'hidden', marginBottom: '12px' }}>
              <div style={{
                width: `${downloadProgress}%`, height: '100%', backgroundColor: '#4ade80',
                transition: 'width 0.3s ease'
              }} />
            </div>
            <div style={{ fontSize: '14px', fontWeight: 'bold' }}>{downloadProgress}%</div>
          </div>
        )}
      </main>
    );
  }

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', backgroundColor: '#111', position: 'relative' }}>
      <Sidebar onSelectFolder={setSelectedFolder} selectedFolder={selectedFolder} />
      <PhotoGallery selectedFolder={selectedFolder} />
      <DetailPanel />
      <ActionBar />
      
      {isDownloadingModel && (
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.85)', zIndex: 9999,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          color: '#fff', padding: '40px'
        }}>
          <h2 style={{ marginBottom: '16px', fontSize: '24px' }}>{downloadModelName} 다운로드 중...</h2>
          <p style={{ marginBottom: '32px', color: '#aaa', textAlign: 'center', maxWidth: '400px', lineHeight: '1.5' }}>
            고품질 사진 분석을 위한 8-bit AI 모델을 백그라운드에서 다운로드하고 있습니다.<br/>네트워크 환경에 따라 2~5분 정도 소요될 수 있습니다. (최초 1회만 실행됩니다)
          </p>
          <div style={{ width: '400px', height: '8px', backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: '4px', overflow: 'hidden', marginBottom: '12px' }}>
            <div style={{
              width: `${downloadProgress}%`, height: '100%', backgroundColor: '#4ade80',
              transition: 'width 0.3s ease'
            }} />
          </div>
          <div style={{ fontSize: '14px', fontWeight: 'bold' }}>{downloadProgress}%</div>
        </div>
      )}
    </div>
  );
}

export default App;
