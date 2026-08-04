import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: number;
  color?: string;
  message?: string;
  fullScreen?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 36,
  color = '#c084fc',
  message,
  fullScreen = false
}) => {
  const content = (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#a1a1aa',
      height: fullScreen ? '100vh' : '100%',
      width: '100%'
    }}>
      <Loader2 size={size} className="spin-animation" style={{ color, marginBottom: message ? '16px' : 0 }} />
      {message && <p style={{ fontSize: '14px', fontWeight: 500, margin: 0 }}>{message}</p>}
      <style>{`
        @keyframes spinAnimation {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .spin-animation { animation: spinAnimation 1s linear infinite; }
      `}</style>
    </div>
  );

  return content;
};
