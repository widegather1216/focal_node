import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  private handleReload = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            flex: 1,
            height: '100%',
            minHeight: '300px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '32px',
            backgroundColor: '#0c0c0e',
            color: '#f4f4f5',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '16px',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '16px',
            }}
          >
            <AlertTriangle size={28} color="#ef4444" />
          </div>
          <h2 style={{ fontSize: '18px', fontWeight: 600, margin: '0 0 8px 0' }}>
            {this.props.fallbackTitle || '컴포넌트 렌더링 중 오류가 발생했습니다'}
          </h2>
          <p
            style={{
              fontSize: '13px',
              color: '#a1a1aa',
              maxWidth: '480px',
              margin: '0 0 20px 0',
              lineHeight: 1.5,
              wordBreak: 'break-word',
            }}
          >
            {this.state.error?.message || '알 수 없는 에러가 발생했습니다.'}
          </p>
          <button
            onClick={this.handleReload}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#27272a',
              border: '1px solid #3f3f46',
              color: '#f4f4f5',
              padding: '8px 16px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'background-color 0.2s',
            }}
          >
            <RefreshCw size={14} /> 다시 시도
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
