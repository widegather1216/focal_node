import test from 'node:test';
import assert from 'node:assert/strict';
import {
  isAbortError,
  parseExportSseStream,
} from '../../src/utils/exportStream.ts';
import { createPhotoExportController } from '../../src/utils/photoExport.ts';

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function createFakeSelectionStore(initialIds = []) {
  let selectedPhotoIds = new Set(initialIds);
  const listeners = new Set();

  const notify = (prevSet) => {
    const prevState = { selectedPhotoIds: prevSet };
    const nextState = { selectedPhotoIds };
    for (const listener of listeners) {
      listener(nextState, prevState);
    }
  };

  return {
    getSelectedPhotoIds: () => selectedPhotoIds,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    setSelection: (ids) => {
      const prevSet = selectedPhotoIds;
      selectedPhotoIds = new Set(ids);
      notify(prevSet);
    },
    deselectPhotoIds: (ids) => {
      const prevSet = selectedPhotoIds;
      const nextSet = new Set(selectedPhotoIds);
      let changed = false;
      for (const photoId of ids) {
        if (nextSet.delete(photoId)) {
          changed = true;
        }
      }
      if (!changed) return;
      selectedPhotoIds = nextSet;
      notify(prevSet);
    },
    clearSelection: () => {
      if (selectedPhotoIds.size === 0) return;
      const prevSet = selectedPhotoIds;
      selectedPhotoIds = new Set();
      notify(prevSet);
    },
  };
}

function createHarness(options = {}) {
  const store = createFakeSelectionStore(options.initialIds ?? ['photo-a']);
  let apiPort = options.apiPort ?? 8000;
  let mounted = true;
  let exporting = false;
  let feedback = null;
  let nextTimerId = 1;
  const scheduledTimers = new Map();

  const controller = createPhotoExportController({
    getApiPort: () => apiPort,
    getSelectedPhotoIds: store.getSelectedPhotoIds,
    deselectPhotoIds: store.deselectPhotoIds,
    pickDestinationFolder: options.pickDestinationFolder ?? (async () => '/tmp/export'),
    exportPhotos: options.exportPhotos,
    isMounted: () => mounted,
    onExportingChange: (nextExporting) => {
      exporting = nextExporting;
    },
    onFeedbackChange: (nextFeedback) => {
      feedback = nextFeedback;
    },
    scheduleTimer: (callback, delayMs) => {
      const timerId = nextTimerId++;
      scheduledTimers.set(timerId, { callback, delayMs });
      return timerId;
    },
    cancelTimer: (timerId) => {
      scheduledTimers.delete(timerId);
    },
  });

  const unsubscribe = store.subscribe((nextState, prevState) => {
    if (nextState.selectedPhotoIds.size === 0 && prevState.selectedPhotoIds.size > 0) {
      controller.resetOnEmptySelection();
    }
  });

  return {
    store,
    controller,
    scheduledTimers,
    setMounted: (value) => {
      mounted = value;
    },
    setApiPort: (value) => {
      apiPort = value;
    },
    getExporting: () => exporting,
    getFeedback: () => feedback,
    flushTimers: () => {
      const entries = Array.from(scheduledTimers.entries());
      scheduledTimers.clear();
      for (const [, entry] of entries) {
        entry.callback();
      }
    },
    cleanup: () => {
      unsubscribe();
      controller.dispose();
    },
  };
}

test('TC-IDX-22.1: clearing selection during SSE export aborts signal, ignores late error/result, and keeps next selection clean', async () => {
  const deferredExport = createDeferred();
  const receivedSignals = [];
  let exportCalls = 0;

  const harness = createHarness({
    initialIds: ['photo-a'],
    exportPhotos: (_ids, _folder, signal) => {
      exportCalls += 1;
      receivedSignals.push(signal);
      return deferredExport.promise;
    },
  });

  const firstExport = harness.controller.handleExport();
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(exportCalls, 1);
  assert.equal(harness.getExporting(), true);
  assert.equal(receivedSignals[0].aborted, false);

  // User clears selection (size -> 0) while SSE export is in-flight
  harness.store.clearSelection();

  assert.equal(receivedSignals[0].aborted, true);
  assert.equal(harness.getExporting(), false);
  assert.equal(harness.getFeedback(), null);

  // User selects a new photo (0 -> 1); ActionBar must show clean [내보내기] state
  harness.store.setSelection(['photo-b']);
  assert.equal(harness.getFeedback(), null);
  assert.equal(harness.getExporting(), false);

  // First request resolves/fails late (non-abort error or delayed payload) -> must be ignored
  deferredExport.resolve({
    status: 'failed',
    exported_count: 0,
    failed_count: 1,
    total_count: 1,
    exported_ids: [],
    failed_ids: ['photo-a'],
    errors: ['disk full'],
  });
  await firstExport;

  assert.equal(harness.getFeedback(), null);
  assert.equal(harness.getExporting(), false);

  // User can immediately start a fresh export on photo-b
  const secondDeferred = createDeferred();
  let secondSignal = null;
  const secondHarnessExport = harness.controller;
  assert.ok(secondHarnessExport);
  harness.cleanup();

  // Verify fresh export works cleanly in same controller after reset
  const retryDeferreds = [createDeferred(), createDeferred()];
  let callIndex = 0;
  const retryHarness = createHarness({
    initialIds: ['photo-a'],
    exportPhotos: (_ids, _folder, signal) => {
      const idx = callIndex++;
      secondSignal = signal;
      return retryDeferreds[idx].promise;
    },
  });

  const p1 = retryHarness.controller.handleExport();
  await new Promise((resolve) => setTimeout(resolve, 0));
  retryHarness.store.clearSelection();
  retryHarness.store.setSelection(['photo-b']);

  const p2 = retryHarness.controller.handleExport();
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(retryHarness.getExporting(), true);
  assert.equal(secondSignal.aborted, false);

  // Late failure of p1 must NOT clobber p2's exporting flag or set stale feedback
  const origConsoleError = console.error;
  console.error = () => {};
  try {
    retryDeferreds[0].reject(new Error('late network drop'));
    await p1;
  } finally {
    console.error = origConsoleError;
  }

  assert.equal(retryHarness.getExporting(), true);
  assert.equal(retryHarness.getFeedback(), null);

  retryDeferreds[1].resolve({
    status: 'success',
    exported_count: 1,
    failed_count: 0,
    total_count: 1,
    exported_ids: ['photo-b'],
    failed_ids: [],
    errors: null,
  });
  await p2;

  assert.equal(retryHarness.getExporting(), false);
  assert.equal(retryHarness.getFeedback()?.kind, 'success');
  retryHarness.cleanup();
});

test('TC-IDX-22.2: clearing selection during folder picker invalidates request and skips exportPhotos on late folder resolve', async () => {
  const pickerDeferred = createDeferred();
  let exportCallCount = 0;

  const harness = createHarness({
    initialIds: ['photo-a'],
    pickDestinationFolder: () => pickerDeferred.promise,
    exportPhotos: async () => {
      exportCallCount += 1;
      return {
        status: 'success',
        exported_count: 1,
        failed_count: 0,
        total_count: 1,
        exported_ids: ['photo-a'],
        failed_ids: [],
        errors: null,
      };
    },
  });

  const pendingExport = harness.controller.handleExport();
  assert.equal(harness.getExporting(), true);

  harness.store.clearSelection();
  assert.equal(harness.getExporting(), false);
  assert.equal(harness.getFeedback(), null);

  // Next photo selected before OS folder picker resolves
  harness.store.setSelection(['photo-b']);
  pickerDeferred.resolve('/tmp/late-dir');
  await pendingExport;

  assert.equal(exportCallCount, 0);
  assert.equal(harness.getExporting(), false);
  assert.equal(harness.getFeedback(), null);
  harness.cleanup();
});

test('TC-IDX-22.3: partial failure deselects exported_ids while keeping failed_ids selected and preserving partial feedback', async () => {
  const harness = createHarness({
    initialIds: ['photo-a', 'photo-b'],
    exportPhotos: async () => ({
      status: 'partial',
      exported_count: 1,
      failed_count: 1,
      total_count: 2,
      exported_ids: ['photo-a'],
      failed_ids: ['photo-b'],
      errors: ['photo-b: Permission denied'],
    }),
  });

  await harness.controller.handleExport();

  assert.equal(harness.getExporting(), false);
  assert.deepEqual(Array.from(harness.store.getSelectedPhotoIds()), ['photo-b']);
  assert.equal(harness.getFeedback()?.kind, 'partial');
  assert.equal(harness.getFeedback()?.message, '1장 내보내기 완료 (1장 실패)');

  // When user later clears the remaining failed photo, feedback clears so next selection is clean
  harness.store.clearSelection();
  assert.equal(harness.getFeedback(), null);

  harness.store.setSelection(['photo-c']);
  assert.equal(harness.getFeedback(), null);
  harness.cleanup();
});

test('TC-IDX-22.4: synchronous 1 -> 0 -> 1 store transition invalidates in-flight export immediately', async () => {
  const deferredExport = createDeferred();
  let capturedSignal = null;

  const harness = createHarness({
    initialIds: ['photo-a'],
    exportPhotos: (_ids, _folder, signal) => {
      capturedSignal = signal;
      return deferredExport.promise;
    },
  });

  const exportPromise = harness.controller.handleExport();
  await new Promise((resolve) => setTimeout(resolve, 0));

  // Synchronous clear + re-select before React render/effect could run
  harness.store.clearSelection();
  harness.store.setSelection(['photo-b']);

  assert.equal(capturedSignal.aborted, true);
  assert.equal(harness.getExporting(), false);
  assert.equal(harness.getFeedback(), null);

  deferredExport.resolve({
    status: 'success',
    exported_count: 1,
    failed_count: 0,
    total_count: 1,
    exported_ids: ['photo-a'],
    failed_ids: [],
    errors: null,
  });
  await exportPromise;

  assert.equal(harness.getFeedback(), null);
  assert.deepEqual(Array.from(harness.store.getSelectedPhotoIds()), ['photo-b']);
  harness.cleanup();
});

test('TC-IDX-22.5: success auto-clear timer is cancelled on empty selection so new selection is never deselected', async () => {
  const harness = createHarness({
    initialIds: ['photo-a'],
    exportPhotos: async () => ({
      status: 'success',
      exported_count: 1,
      failed_count: 0,
      total_count: 1,
      exported_ids: ['photo-a'],
      failed_ids: [],
      errors: null,
    }),
  });

  await harness.controller.handleExport();
  assert.equal(harness.getFeedback()?.kind, 'success');
  assert.equal(harness.scheduledTimers.size, 1);

  harness.store.clearSelection();
  assert.equal(harness.scheduledTimers.size, 0);
  assert.equal(harness.getFeedback(), null);

  harness.store.setSelection(['photo-a']);
  harness.flushTimers();
  assert.deepEqual(Array.from(harness.store.getSelectedPhotoIds()), ['photo-a']);
  harness.cleanup();
});

test('TC-IDX-22.6: parseExportSseStream aborts cleanly mid-JSON chunk without JSON parse error or missing-final error', async () => {
  const controller = new AbortController();
  const encoder = new TextEncoder();
  let readerCancelled = false;
  let pullCount = 0;

  const fakeStream = {
    getReader() {
      return {
        async read() {
          pullCount += 1;
          if (pullCount === 1) {
            return {
              value: encoder.encode('event: done\ndata: {"status":"suc'),
              done: false,
            };
          }
          // Simulate Web Stream resolving { done: true } when reader.cancel() is invoked on abort
          return new Promise((resolve) => {
            controller.signal.addEventListener(
              'abort',
              () => resolve({ value: undefined, done: true }),
              { once: true },
            );
          });
        },
        async cancel() {
          readerCancelled = true;
        },
        releaseLock() {},
      };
    },
  };

  const streamPromise = parseExportSseStream(fakeStream, controller.signal);
  await new Promise((resolve) => setTimeout(resolve, 0));
  controller.abort();

  await assert.rejects(streamPromise, (caughtErr) => isAbortError(caughtErr));
  assert.equal(readerCancelled, true);
});

test('TC-IDX-22.7: unmount dispose aborts active request and suppresses post-unmount state updates', async () => {
  const deferredExport = createDeferred();
  let capturedSignal = null;
  let stateUpdatesAfterUnmount = 0;

  const store = createFakeSelectionStore(['photo-a']);
  let mounted = true;
  const controller = createPhotoExportController({
    getApiPort: () => 8000,
    getSelectedPhotoIds: store.getSelectedPhotoIds,
    deselectPhotoIds: store.deselectPhotoIds,
    pickDestinationFolder: async () => '/tmp/export',
    exportPhotos: (_ids, _folder, signal) => {
      capturedSignal = signal;
      return deferredExport.promise;
    },
    isMounted: () => mounted,
    onExportingChange: () => {
      if (!mounted) stateUpdatesAfterUnmount += 1;
    },
    onFeedbackChange: () => {
      if (!mounted) stateUpdatesAfterUnmount += 1;
    },
  });

  const exportPromise = controller.handleExport();
  await new Promise((resolve) => setTimeout(resolve, 0));

  mounted = false;
  controller.dispose();
  assert.equal(capturedSignal.aborted, true);

  deferredExport.reject(new DOMException('Aborted', 'AbortError'));
  await exportPromise;

  assert.equal(stateUpdatesAfterUnmount, 0);
});
