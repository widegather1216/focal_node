import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useAppStore } from '../store/useAppStore';

export function useBackendInit() {
  const [loading, setLoading] = useState(true);
  const {
    apiPort,
    setApiPort,
    backendStatus,
    setBackendStatus,
    backendError,
    setBackendError
  } = useAppStore();

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
  }, [setApiPort, setBackendStatus, setBackendError]);

  // Continuous health ping to detect backend crashes
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

  return { loading, backendStatus, backendError };
}
