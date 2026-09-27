import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: number;
  color?: string;
  message?: string;
  fullScreen?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 32,
  color = 'var(--accent-focal)',
  message,
  fullScreen = false
}) => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'var(--text-secondary)',
      height: fullScreen ? '100vh' : '100%',
      width: '100%',
      padding: '20px',
      boxSizing: 'border-box',
      userSelect: 'none'
    }}>
      <Loader2
        size={size}
        className="spin"
        style={{ color, marginBottom: message ? '14px' : 0, flexShrink: 0 }}
      />
      {message && (
        <p style={{
          fontSize: '13px',
          fontWeight: 500,
          margin: 0,
          wordBreak: 'keep-all',
          whiteSpace: 'nowrap',
          textAlign: 'center',
          color: 'var(--text-primary)',
          letterSpacing: '-0.01em'
        }}>
          {message}
        </p>
      )}
    </div>
  );
};
