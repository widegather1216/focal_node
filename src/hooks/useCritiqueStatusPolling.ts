import { useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import { CritiqueStatus } from '../types/critique';

export interface UseCritiqueStatusPollingOptions {
  intervalMs?: number;
  onTerminal?: (terminalStatus: CritiqueStatus) => void;
}

export function isTerminalCritiqueStatus(critiqueStatus: CritiqueStatus): boolean {
  return (
    critiqueStatus.status === 'completed' ||
    critiqueStatus.status === 'error' ||
    critiqueStatus.status === 'cancelled' ||
    critiqueStatus.progress === 100
  );
}

/**
 * Polls backend critique generation progress with a single active timer chain
 * and deduplicated wake-up checks across focus, online, and visibility events.
 */
export function useCritiqueStatusPolling(
  photoId: string | null | undefined,
  enabled: boolean,
  options?: UseCritiqueStatusPollingOptions
): CritiqueStatus | null {
  const intervalMs = options?.intervalMs ?? 1200;
  const onTerminalRef = useRef(options?.onTerminal);
  const [status, setStatus] = useState<CritiqueStatus | null>(null);

  useEffect(() => {
    onTerminalRef.current = options?.onTerminal;
  }, [options?.onTerminal]);

  useEffect(() => {
    if (!enabled || !photoId) {
      setStatus(null);
      return;
    }

    let isMounted = true;
    let isStopped = false;
    let inFlight = false;
    let onTerminalCalled = false;
    let timerId: ReturnType<typeof setTimeout> | null = null;

    const clearScheduledTimer = () => {
      if (timerId !== null) {
        clearTimeout(timerId);
        timerId = null;
      }
    };

    const pollStatus = async () => {
      if (!isMounted || isStopped || inFlight) return;
      clearScheduledTimer();
      inFlight = true;

      try {
        const fetchedStatus = await api.getCritiqueStatus(photoId);
        if (!isMounted || !fetchedStatus) return;

        setStatus(fetchedStatus);
        if (isTerminalCritiqueStatus(fetchedStatus)) {
          isStopped = true;
          if (!onTerminalCalled) {
            onTerminalCalled = true;
            onTerminalRef.current?.(fetchedStatus);
          }
        }
      } catch (error: unknown) {
        console.debug('[useCritiqueStatusPolling] Transient status poll error:', error);
      } finally {
        inFlight = false;
        if (isMounted && !isStopped) {
          clearScheduledTimer();
          timerId = setTimeout(pollStatus, intervalMs);
        }
      }
    };

    const handleWake = () => {
      if (document.visibilityState === 'hidden') return;
      clearScheduledTimer();
      void pollStatus();
    };

    void pollStatus();
    window.addEventListener('focus', handleWake);
    window.addEventListener('online', handleWake);
    document.addEventListener('visibilitychange', handleWake);

    return () => {
      isMounted = false;
      isStopped = true;
      clearScheduledTimer();
      window.removeEventListener('focus', handleWake);
      window.removeEventListener('online', handleWake);
      document.removeEventListener('visibilitychange', handleWake);
    };
  }, [photoId, enabled, intervalMs]);

  return status;
}

/**
 * Polls critique status after a transient disconnect during generation
 * until a terminal status is reached or maxAttempts is exhausted.
 */
export async function pollAndRecoverCritique(
  photoId: string,
  signal: AbortSignal
): Promise<string | null> {
  const maxAttempts = 35; // Poll up to ~50 seconds to allow MLX pipeline completion after sleep
  const intervalMs = 1500;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    if (signal.aborted) {
      return null;
    }
    try {
      const critiqueStatus = await api.getCritiqueStatus(photoId);
      if (critiqueStatus.status === 'completed' && critiqueStatus.critique) {
        return critiqueStatus.critique;
      }
      if (critiqueStatus.status === 'cancelled') {
        return null;
      }
      if (critiqueStatus.status === 'error') {
        throw new Error(critiqueStatus.message || "비평 생성 오류");
      }
    } catch (error: unknown) {
      if (error instanceof Error && error.message.includes("비평 생성 오류")) {
        throw error;
      }
      console.debug("[useCritiqueStatusPolling] Transient critique recovery poll error:", error);
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  return null;
}
