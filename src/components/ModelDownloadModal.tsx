import React, { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';

interface ModelDownloadModalProps {
  isOverlay?: boolean;
}

export const ModelDownloadModal: React.FC<ModelDownloadModalProps> = ({ isOverlay = false }) => {
  const {
    isDownloadingModel,
    downloadProgress,
    downloadedBytes,
    totalBytes,
    downloadModelName,
    downloadError,
    setDownloadError,
    setDownloadProgress,
  } = useAppStore();

  const [isRetrying, setIsRetrying] = useState(false);

  if (!isDownloadingModel) return null;

  const dlGB = (downloadedBytes / (1024 * 1024 * 1024)).toFixed(1);
  const totalGB = (totalBytes / (1024 * 1024 * 1024)).toFixed(1);
  const bytesLabel = totalBytes > 0 ? ` (${dlGB} GB / ${totalGB} GB)` : '';

  const handleRetry = async () => {
    try {
      setIsRetrying(true);
      setDownloadError(null);
      setDownloadProgress(0);
      await api.triggerModelDownload();
    } catch (err: any) {
      setDownloadError(err.message || '다시 시도 요청에 실패했습니다.');
    } finally {
      setIsRetrying(false);
    }
  };

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

  if (downloadError) {
    return (
      <div style={style}>
        <div style={{
          width: '48px', height: '48px', borderRadius: '50%',
          backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#ef4444',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '24px', marginBottom: '16px', border: '1px solid rgba(239, 68, 68, 0.3)'
        }}>
          ⚠️
        </div>
        <h2 style={{ marginBottom: '12px', fontSize: '22px', fontWeight: 600 }}>
          {downloadModelName} 다운로드 실패
        </h2>
        <p style={{
          marginBottom: '24px', color: '#f87171', backgroundColor: 'rgba(239, 68, 68, 0.1)',
          padding: '12px 20px', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)',
          textAlign: 'center', maxWidth: '440px', fontSize: '14px', lineHeight: '1.5'
        }}>
          {downloadError}
        </p>
        <button
          onClick={handleRetry}
          disabled={isRetrying}
          style={{
            padding: '10px 24px',
            backgroundColor: isRetrying ? '#6b7280' : '#3b82f6',
            color: '#ffffff',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: 600,
            cursor: isRetrying ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.2s ease',
            boxShadow: '0 2px 8px rgba(59, 130, 246, 0.3)'
          }}
        >
          {isRetrying ? '재요청 중...' : '🔄 다시 시도 (Retry)'}
        </button>
      </div>
    );
  }

  const isConnecting = downloadProgress === 0 || downloadedBytes === 0;
  const statusSubtitle = isConnecting
    ? 'HuggingFace 서버와 연결을 확인하는 중입니다. (15~30초 후 데이터 수신 및 로딩바 이동이 시작됩니다)'
    : '고품질 사진 분석을 위한 모델을 백그라운드에서 다운로드하고 있습니다. 네트워크 환경에 따라 2~5분 정도 소요될 수 있습니다.';

  return (
    <div style={style}>
      <h2 style={{ marginBottom: '16px', fontSize: '24px' }}>
        {downloadModelName} {isConnecting ? '연결 중...' : '다운로드 중...'}
      </h2>
      <p style={{ marginBottom: '32px', color: '#aaa', textAlign: 'center', maxWidth: '420px', lineHeight: '1.5', fontSize: '14px' }}>
        {statusSubtitle}
      </p>
      <div style={{ width: '400px', height: '8px', backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: '4px', overflow: 'hidden', marginBottom: '12px' }}>
        <div style={{
          width: isConnecting ? '100%' : `${downloadProgress}%`,
          height: '100%',
          backgroundColor: isConnecting ? '#3b82f6' : '#4ade80',
          transition: 'width 0.3s ease',
          opacity: isConnecting ? 0.6 : 1,
        }} />
      </div>
      <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '20px' }}>
        {isConnecting ? '서버 연결 및 파일 준비 중...' : `${downloadProgress}%${bytesLabel}`}
      </div>
      <button
        onClick={handleRetry}
        disabled={isRetrying}
        style={{
          padding: '8px 18px',
          backgroundColor: 'rgba(255, 255, 255, 0.08)',
          color: '#ccc',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderRadius: '6px',
          fontSize: '13px',
          cursor: isRetrying ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s ease',
        }}
      >
        {isRetrying ? '다운로드 재요청 중...' : '🔄 다운로드 재요청 (Force Retry)'}
      </button>
    </div>
  );
};
