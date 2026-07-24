import React from 'react';
import { useAppStore } from '../store/useAppStore';

interface ModelDownloadModalProps {
  isOverlay?: boolean;
}

export const ModelDownloadModal: React.FC<ModelDownloadModalProps> = ({ isOverlay = false }) => {
  const { isDownloadingModel, downloadProgress, downloadModelName } = useAppStore();

  if (!isDownloadingModel) return null;

  const style: React.CSSProperties = isOverlay
    ? {
        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.85)', zIndex: 9999,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        color: '#fff', padding: '40px'
      }
    : {
        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(17, 17, 17, 0.95)', zIndex: 9999,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        color: '#fff', padding: '40px'
      };

  return (
    <div style={style}>
      <h2 style={{ marginBottom: '16px', fontSize: '24px' }}>{downloadModelName} 다운로드 중...</h2>
      <p style={{ marginBottom: '32px', color: '#aaa', textAlign: 'center', maxWidth: '400px', lineHeight: '1.5' }}>
        고품질 사진 분석을 위한 모델을 백그라운드에서 다운로드하고 있습니다.<br />
        네트워크 환경에 따라 2~5분 정도 소요될 수 있습니다. (최초 1회만 실행됩니다)
      </p>
      <div style={{ width: '400px', height: '8px', backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: '4px', overflow: 'hidden', marginBottom: '12px' }}>
        <div style={{
          width: `${downloadProgress}%`, height: '100%', backgroundColor: '#4ade80',
          transition: 'width 0.3s ease'
        }} />
      </div>
      <div style={{ fontSize: '14px', fontWeight: 'bold' }}>{downloadProgress}%</div>
    </div>
  );
};
