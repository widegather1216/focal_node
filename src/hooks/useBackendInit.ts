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

  // Continuous health ping to detect backend crashes with consecutive failure resilience
  useEffect(() => {
    if (!apiPort) return;

    let consecutiveFailures = 0;
    const MAX_FAILURES = 3;

    const interval = setInterval(async () => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      try {
        const res = await fetch(`http://127.0.0.1:${apiPort}/api/health`, {
          method: 'GET',
          signal: controller.signal,
        });
        clearTimeout(timeoutId);

        if (res.ok) {
          consecutiveFailures = 0;
        } else {
          consecutiveFailures += 1;
        }
      } catch (err) {
        clearTimeout(timeoutId);
        consecutiveFailures += 1;
      }

      if (consecutiveFailures >= MAX_FAILURES) {
        console.error("Health ping failed 3 consecutive times. Backend is unreachable.");
        setBackendError("백엔드 서버와 통신이 끊어졌습니다. (AI 모델 가중치 로딩 실패 또는 메모리 부족으로 종료되었을 수 있습니다.) 앱을 재시작해주세요.");
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [apiPort, setBackendError]);

  return { loading, backendStatus, backendError };
}
