import React from 'react';
import { ModelDownloadModal } from '../ModelDownloadModal';

interface AppSplashProps {
  backendStatus: string | null;
  backendError: string | null;
  isDownloadingModel: boolean;
}

export const AppSplash: React.FC<AppSplashProps> = ({
  backendStatus,
  backendError,
  isDownloadingModel
}) => {
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
};
