import { useState, useEffect, lazy, Suspense } from "react";
import { useAppStore } from "./store/useAppStore";
import { useBackendInit } from "./hooks/useBackendInit";
import { useTauriEvents } from "./hooks/useTauriEvents";
import { useModelDownloadStatus } from "./hooks/useModelDownloadStatus";
import { useIndexingStatus } from "./hooks/useIndexingStatus";
import { Sidebar } from "./components/Sidebar";
import { PhotoGallery } from "./components/PhotoGallery";
import { ActionBar } from "./components/ActionBar";
import { ModelDownloadModal } from "./components/ModelDownloadModal";
import { GlobalCritiqueToast } from "./components/critique/GlobalCritiqueToast";
import { AppSplash } from "./components/common/AppSplash";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { LoadingSpinner } from "./components/common/LoadingSpinner";
import "./App.css";

// Lazy-loaded heavy views for fast initial load
const AnalyticsView = lazy(() => import("./components/AnalyticsView").then(m => ({ default: m.AnalyticsView })));
const CritiqueView = lazy(() => import("./components/CritiqueView").then(m => ({ default: m.CritiqueView })));
const DetailPanel = lazy(() => import("./components/DetailPanel").then(m => ({ default: m.DetailPanel })));
const FullscreenViewer = lazy(() => import("./components/FullscreenViewer").then(m => ({ default: m.FullscreenViewer })));
const CritiqueDocumentModal = lazy(() => import("./components/critique/CritiqueDocumentModal").then(m => ({ default: m.CritiqueDocumentModal })));

function App() {
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const { loading, backendStatus, backendError } = useBackendInit();
  useTauriEvents();
  useModelDownloadStatus();
  useIndexingStatus();

  const { isDownloadingModel, activeTab, openCritiqueDocument } = useAppStore();

  // Detect popout mode from query params
  const urlParams = new URLSearchParams(window.location.search);
  const isPopoutCritique = urlParams.get('popout') === 'critique';
  const popoutPhotoId = urlParams.get('photoId');

  useEffect(() => {
    if (isPopoutCritique && popoutPhotoId) {
      openCritiqueDocument(popoutPhotoId);
    }
  }, [isPopoutCritique, popoutPhotoId, openCritiqueDocument]);

  if (loading || backendError) {
    return (
      <AppSplash
        backendStatus={backendStatus}
        backendError={backendError}
        isDownloadingModel={isDownloadingModel}
      />
    );
  }

  // Pure standalone window mode when popped out
  if (isPopoutCritique) {
    return (
      <ErrorBoundary fallbackTitle="비평 문서 뷰어 로딩 중 오류가 발생했습니다">
        <div style={{ width: '100vw', height: '100vh', backgroundColor: '#09090b', overflow: 'hidden' }}>
          <Suspense fallback={<LoadingSpinner fullScreen message="비평 문서를 불러오는 중..." />}>
            <CritiqueDocumentModal />
          </Suspense>
        </div>
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary fallbackTitle="애플리케이션 오류가 발생했습니다">
      <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', backgroundColor: '#111', position: 'relative' }}>
        <Sidebar onSelectFolder={setSelectedFolder} selectedFolder={selectedFolder} />
        
        <main style={{ flex: 1, height: '100%', position: 'relative', overflow: 'hidden' }}>
          {activeTab === 'gallery' ? (
            <ErrorBoundary fallbackTitle="갤러리 렌더링 중 오류가 발생했습니다">
              <PhotoGallery selectedFolder={selectedFolder} />
            </ErrorBoundary>
          ) : activeTab === 'analytics' ? (
            <ErrorBoundary fallbackTitle="장비 통계 분석 중 오류가 발생했습니다">
              <Suspense fallback={<LoadingSpinner fullScreen message="장비 분석 통계를 불러오는 중..." />}>
                <AnalyticsView />
              </Suspense>
            </ErrorBoundary>
          ) : (
            <ErrorBoundary fallbackTitle="AI 사진 비평 목록 중 오류가 발생했습니다">
              <Suspense fallback={<LoadingSpinner fullScreen message="AI 사진 비평을 불러오는 중..." />}>
                <CritiqueView />
              </Suspense>
            </ErrorBoundary>
          )}
        </main>

        <Suspense fallback={null}>
          <DetailPanel />
        </Suspense>
        
        <ActionBar />
        <GlobalCritiqueToast />
        
        <ModelDownloadModal isOverlay={true} />
        
        <Suspense fallback={null}>
          <FullscreenViewer />
        </Suspense>

        <Suspense fallback={null}>
          <CritiqueDocumentModal />
        </Suspense>
      </div>
    </ErrorBoundary>
  );
}

export default App;
