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
    <main style={{
      display: "flex",
      flexDirection: "column",
      justifyContent: "center",
      alignItems: "center",
      height: "100vh",
      backgroundColor: 'var(--bg-canvas)',
      color: 'var(--text-primary)',
      position: 'relative',
      userSelect: 'none'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <div style={{
          width: '10px',
          height: '10px',
          borderRadius: '50%',
          backgroundColor: 'var(--accent-focal)',
          boxShadow: '0 0 12px rgba(225, 29, 72, 0.8)'
        }} />
        <h1 style={{ margin: 0, fontSize: '28px', fontWeight: 700, letterSpacing: '-0.02em' }}>
          Focal Node
        </h1>
      </div>
      
      {!backendError && !isDownloadingModel && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '28px' }}>
          <div style={{ 
            width: '36px',
            height: '36px', 
            border: '3px solid rgba(255, 255, 255, 0.1)', 
            borderTopColor: 'var(--accent-focal)', 
            borderRadius: '50%', 
            marginBottom: '16px'
          }} className="spin" />
          <h2 style={{ fontSize: '16px', fontWeight: 600, margin: '0 0 6px 0', whiteSpace: 'nowrap' }}>
            앱 환경을 준비하고 있습니다...
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', margin: 0, whiteSpace: 'nowrap' }}>
            {backendStatus || "초기 설정 중..."}
          </p>
        </div>
      )}

      {backendError && (
        <p style={{ color: '#f87171', marginTop: '20px', maxWidth: '80%', textAlign: 'center', lineHeight: '1.5', wordBreak: 'keep-all', fontSize: '13px' }}>
          에러 발생: {backendError}
        </p>
      )}

      <ModelDownloadModal isOverlay={false} />
    </main>
  );
};
