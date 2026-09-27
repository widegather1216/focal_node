import React, { useState } from 'react';
import { AlertTriangle, RotateCcw, Loader2 } from 'lucide-react';
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

  const modalBackdropStyle: React.CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: isOverlay ? 'rgba(9, 9, 11, 0.88)' : 'var(--bg-canvas)',
    backdropFilter: isOverlay ? 'blur(16px)' : 'none',
    zIndex: 9999,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--text-primary)',
    padding: '30px',
    userSelect: 'none'
  };

  if (downloadError) {
    return (
      <div style={modalBackdropStyle}>
        <div style={{
          width: '44px',
          height: '44px',
          borderRadius: '50%',
          backgroundColor: 'rgba(239, 68, 68, 0.15)',
          color: '#ef4444',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '16px',
          border: '1px solid rgba(239, 68, 68, 0.3)'
        }}>
          <AlertTriangle size={20} color="#ef4444" />
        </div>
        <h2 style={{ marginBottom: '10px', fontSize: '20px', fontWeight: 600, wordBreak: 'keep-all', textAlign: 'center' }}>
          {downloadModelName} 다운로드 실패
        </h2>
        <p style={{
          marginBottom: '20px',
          color: '#f87171',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          padding: '10px 18px',
          borderRadius: '6px',
          border: '1px solid rgba(239, 68, 68, 0.2)',
          textAlign: 'center',
          maxWidth: '460px',
          fontSize: '13px',
          lineHeight: 1.6,
          wordBreak: 'keep-all'
        }}>
          {downloadError}
        </p>
        <button
          onClick={handleRetry}
          disabled={isRetrying}
          style={{
            padding: '9px 20px',
            backgroundColor: isRetrying ? 'var(--bg-elevated)' : 'var(--accent-focal)',
            color: '#ffffff',
            border: 'none',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 600,
            cursor: isRetrying ? 'not-allowed' : 'pointer',
            whiteSpace: 'nowrap',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          {isRetrying ? <Loader2 size={14} className="spin" /> : <RotateCcw size={14} />}
          <span>{isRetrying ? '재요청 중...' : '다시 시도'}</span>
        </button>
      </div>
    );
  }

  const isConnecting = downloadProgress === 0 || downloadedBytes === 0;
  const statusSubtitle = isConnecting
    ? '서버와 연결을 확인하는 중입니다. 잠시 후 데이터 수신이 시작됩니다.'
    : '로컬 추론을 위한 고품질 AI 모델을 다운로드하고 있습니다. 네트워크 환경에 따라 수 분 소요될 수 있습니다.';

  return (
    <div style={modalBackdropStyle}>
      <h2 style={{ marginBottom: '12px', fontSize: '20px', fontWeight: 600, whiteSpace: 'nowrap' }}>
        {downloadModelName} {isConnecting ? '연결 중...' : '다운로드 중...'}
      </h2>
      <p style={{
        marginBottom: '24px',
        color: 'var(--text-muted)',
        textAlign: 'center',
        maxWidth: '460px',
        lineHeight: 1.6,
        fontSize: '13px',
        wordBreak: 'keep-all'
      }}>
        {statusSubtitle}
      </p>
      <div style={{
        width: '380px',
        maxWidth: '90%',
        height: '6px',
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        borderRadius: '3px',
        overflow: 'hidden',
        marginBottom: '10px'
      }}>
        <div style={{
          width: isConnecting ? '100%' : `${downloadProgress}%`,
          height: '100%',
          backgroundColor: 'var(--accent-focal)',
          transition: 'width 0.3s ease',
          opacity: isConnecting ? 0.6 : 1,
        }} />
      </div>
      <div className="font-mono" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '18px', whiteSpace: 'nowrap' }}>
        {isConnecting ? '서버 연결 및 파일 준비 중...' : `${downloadProgress}%${bytesLabel}`}
      </div>
      <button
        onClick={handleRetry}
        disabled={isRetrying}
        style={{
          padding: '7px 16px',
          backgroundColor: 'var(--bg-card)',
          color: 'var(--text-secondary)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          fontSize: '12px',
          cursor: isRetrying ? 'not-allowed' : 'pointer',
          whiteSpace: 'nowrap',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}
      >
        {isRetrying ? <Loader2 size={13} className="spin" /> : <RotateCcw size={13} />}
        <span>{isRetrying ? '다운로드 재요청 중...' : '다운로드 재요청'}</span>
      </button>
    </div>
  );
};
