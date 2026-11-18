import { evaluateExportOutcome, isAbortError } from './exportStream.ts';
import type { ExportFeedback, ExportResult } from './exportStream.ts';

export const EXPORT_SUCCESS_AUTO_CLEAR_MS = 1800;

export interface PhotoExportControllerDeps {
  getApiPort: () => number | null;
  getSelectedPhotoIds: () => ReadonlySet<string>;
  deselectPhotoIds: (ids: Iterable<string>) => void;
  pickDestinationFolder: () => Promise<string | null>;
  exportPhotos: (
    photoIds: string[],
    destinationFolder: string,
    signal: AbortSignal,
  ) => Promise<ExportResult>;
  isMounted: () => boolean;
  onExportingChange: (exporting: boolean) => void;
  onFeedbackChange: (feedback: ExportFeedback | null) => void;
  scheduleTimer?: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>;
  cancelTimer?: (timerId: ReturnType<typeof setTimeout>) => void;
  autoClearDelayMs?: number;
}

export interface PhotoExportController {
  handleExport: () => Promise<void>;
  dismissFeedback: () => void;
  resetOnEmptySelection: () => void;
  dispose: () => void;
}

interface ExportRuntimeState {
  isBusy: boolean;
  requestId: number;
  feedbackTimer: ReturnType<typeof setTimeout> | null;
  abortController: AbortController | null;
}

/**
 * Formats an unexpected export exception into a user-facing error banner payload.
 */
export function formatCaughtExportError(caughtErr: unknown): ExportFeedback {
  const rawMessage =
    caughtErr instanceof Error && caughtErr.message.trim()
      ? caughtErr.message.trim()
      : '내보내기 도중 오류가 발생했습니다.';
  const formattedMessage = rawMessage.startsWith('내보내기 실패')
    ? rawMessage
    : `내보내기 실패: ${rawMessage}`;
  return { kind: 'error', message: formattedMessage, detail: rawMessage };
}

function clearScheduledFeedbackTimer(
  state: ExportRuntimeState,
  cancelTimer: (timerId: ReturnType<typeof setTimeout>) => void,
): void {
  if (state.feedbackTimer !== null) {
    cancelTimer(state.feedbackTimer);
    state.feedbackTimer = null;
  }
}

function invalidateInFlightExport(
  state: ExportRuntimeState,
  deps: PhotoExportControllerDeps,
  cancelTimer: (timerId: ReturnType<typeof setTimeout>) => void,
  notifyUi: boolean,
): void {
  clearScheduledFeedbackTimer(state, cancelTimer);
  state.requestId += 1;
  state.abortController?.abort();
  state.abortController = null;
  state.isBusy = false;
  if (notifyUi && deps.isMounted()) {
    deps.onExportingChange(false);
    deps.onFeedbackChange(null);
  }
}

function isActiveExportRequest(
  state: ExportRuntimeState,
  deps: PhotoExportControllerDeps,
  currentRequestId: number,
): boolean {
  return (
    deps.isMounted() &&
    state.requestId === currentRequestId &&
    deps.getSelectedPhotoIds().size > 0
  );
}

function applyExportOutcome(
  state: ExportRuntimeState,
  deps: PhotoExportControllerDeps,
  exportResult: ExportResult,
  targetPhotoIds: string[],
  currentRequestId: number,
  scheduleTimer: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>,
  autoClearDelayMs: number,
): void {
  const outcome = evaluateExportOutcome(exportResult, targetPhotoIds.length);
  deps.onFeedbackChange(outcome);

  if (outcome.kind === 'success') {
    state.feedbackTimer = scheduleTimer(() => {
      state.feedbackTimer = null;
      if (!deps.isMounted() || state.requestId !== currentRequestId) {
        return;
      }
      deps.deselectPhotoIds(targetPhotoIds);
      if (state.requestId === currentRequestId) {
        deps.onFeedbackChange(null);
      }
    }, autoClearDelayMs);
    return;
  }

  const hasPartialSuccessAndFailure =
    outcome.kind === 'partial' &&
    exportResult.exported_ids.length > 0 &&
    exportResult.failed_ids.length > 0;
  if (hasPartialSuccessAndFailure) {
    // Keep failed items selected so retrying only re-exports failed photos without duplicating successes.
    deps.deselectPhotoIds(exportResult.exported_ids);
  }
}

function handleExportFailure(
  caughtErr: unknown,
  state: ExportRuntimeState,
  deps: PhotoExportControllerDeps,
  currentRequestId: number,
): void {
  if (isAbortError(caughtErr)) {
    // Explicit abort on empty selection or unmount must not surface as a user-facing export failure.
    return;
  }
  if (!deps.isMounted() || state.requestId !== currentRequestId) {
    console.debug('Ignoring stale export error after cancellation or unmount:', caughtErr);
    return;
  }
  console.error('Export error:', caughtErr);
  deps.onFeedbackChange(formatCaughtExportError(caughtErr));
}

function finalizeExportRequest(
  state: ExportRuntimeState,
  deps: PhotoExportControllerDeps,
  controller: AbortController | null,
  currentRequestId: number,
): void {
  if (controller && state.abortController === controller) {
    state.abortController = null;
  }
  if (state.requestId !== currentRequestId) {
    return;
  }
  state.isBusy = false;
  if (deps.isMounted()) {
    deps.onExportingChange(false);
  }
}

async function executePhotoExportAttempt(
  state: ExportRuntimeState,
  deps: PhotoExportControllerDeps,
  targetPhotoIds: string[],
  currentRequestId: number,
  scheduleTimer: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>,
  autoClearDelayMs: number,
): Promise<void> {
  let controller: AbortController | null = null;
  try {
    const targetFolder = await deps.pickDestinationFolder();
    if (!targetFolder || !isActiveExportRequest(state, deps, currentRequestId)) {
      return;
    }
    controller = new AbortController();
    state.abortController = controller;

    const exportResult = await deps.exportPhotos(targetPhotoIds, targetFolder, controller.signal);
    if (!isActiveExportRequest(state, deps, currentRequestId)) {
      return;
    }
    applyExportOutcome(
      state,
      deps,
      exportResult,
      targetPhotoIds,
      currentRequestId,
      scheduleTimer,
      autoClearDelayMs,
    );
  } catch (caughtErr: unknown) {
    handleExportFailure(caughtErr, state, deps, currentRequestId);
  } finally {
    finalizeExportRequest(state, deps, controller, currentRequestId);
  }
}

/**
 * Creates a lifecycle-safe photo export controller that aborts and invalidates
 * stale folder-picker or SSE export requests whenever the selection is emptied.
 */
export function createPhotoExportController(
  deps: PhotoExportControllerDeps,
): PhotoExportController {
  const scheduleTimer = deps.scheduleTimer ?? ((callback, delayMs) => setTimeout(callback, delayMs));
  const cancelTimer = deps.cancelTimer ?? ((timerId) => clearTimeout(timerId));
  const autoClearDelayMs = deps.autoClearDelayMs ?? EXPORT_SUCCESS_AUTO_CLEAR_MS;

  const state: ExportRuntimeState = {
    isBusy: false,
    requestId: 0,
    feedbackTimer: null,
    abortController: null,
  };

  const handleExport = async (): Promise<void> => {
    if (!deps.getApiPort() || state.isBusy) return;
    const targetPhotoIds = Array.from(new Set(deps.getSelectedPhotoIds()));
    if (targetPhotoIds.length === 0) return;

    clearScheduledFeedbackTimer(state, cancelTimer);
    state.isBusy = true;
    const currentRequestId = ++state.requestId;
    deps.onExportingChange(true);
    deps.onFeedbackChange(null);

    await executePhotoExportAttempt(
      state,
      deps,
      targetPhotoIds,
      currentRequestId,
      scheduleTimer,
      autoClearDelayMs,
    );
  };

  return {
    handleExport,
    dismissFeedback: () => {
      clearScheduledFeedbackTimer(state, cancelTimer);
      if (deps.isMounted()) {
        deps.onFeedbackChange(null);
      }
    },
    resetOnEmptySelection: () => invalidateInFlightExport(state, deps, cancelTimer, true),
    dispose: () => invalidateInFlightExport(state, deps, cancelTimer, false),
  };
}
