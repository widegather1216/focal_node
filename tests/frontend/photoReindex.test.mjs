import test from 'node:test';
import assert from 'node:assert/strict';
import {
  addReindexingPhotoId,
  clearPhotoReindexError,
  executePhotoReindex,
  formatReindexErrorMessage,
  removeReindexingPhotoId,
  setPhotoReindexError,
  shouldSyncPhotoEditFields,
} from '../../src/utils/photoReindex.ts';

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function makePhotoDetail(id, caption, tags = []) {
  return {
    id,
    file_name: `${id}.jpg`,
    file_path: `/photos/${id}.jpg`,
    file_size: 1024,
    mime_type: 'image/jpeg',
    is_favorite: false,
    metadata: {
      width: 4000,
      height: 3000,
      color_space: 'sRGB',
      camera_model: 'ILCE-7M4',
      lens_model: 'FE 35mm F1.4 GM',
      f_number: 1.4,
      focal_length: 35,
      focal_length_35mm: 35,
      crop_factor: 1,
      sensor_format: 'Full Frame',
      shutter_speed: '1/250',
      iso: 100,
      capture_date: '2026-01-01T12:00:00',
    },
    ai_analysis: {
      caption,
      tags,
      aesthetic_tags: [],
      is_user_edited: false,
      critique: null,
      critique_en: null,
      overall_score: null,
      iaa_score: null,
      iqa_score: null,
      ista_score: null,
      critique_updated_at: null,
    },
  };
}

function createFakeQueryClient() {
  const operations = [];
  const cache = new Map();
  return {
    operations,
    cache,
    async cancelQueries({ queryKey }) {
      operations.push({ type: 'cancel', queryKey });
    },
    setQueryData(queryKey, data) {
      operations.push({ type: 'set', queryKey, data });
      cache.set(JSON.stringify(queryKey), data);
    },
    async invalidateQueries({ queryKey }) {
      operations.push({ type: 'invalidate', queryKey });
    },
  };
}

test('TC-IDX-20.1: syncs photoDetail cache (cancelling in-flight GETs first) and invalidates photos/analyticsStats/critiques', async () => {
  const queryClient = createFakeQueryClient();
  const updatedA = makePhotoDetail('photo-a', 'Updated caption A', ['sunset']);
  let reindexingIds = new Set();
  let errorsById = {};
  const activeUpdates = [];

  const succeeded = await executePhotoReindex({
    targetId: 'photo-a',
    inFlightIds: new Set(),
    requestSeqByPhoto: new Map(),
    reindexPhoto: async () => updatedA,
    queryClient,
    getSelectedPhotoId: () => 'photo-a',
    isMounted: () => true,
    onStart: (id) => {
      reindexingIds = addReindexingPhotoId(reindexingIds, id);
      errorsById = clearPhotoReindexError(errorsById, id);
    },
    onSuccessActive: (photo) => {
      activeUpdates.push(photo);
    },
    onError: (id, message) => {
      errorsById = setPhotoReindexError(errorsById, id, message);
    },
    onFinish: (id) => {
      reindexingIds = removeReindexingPhotoId(reindexingIds, id);
    },
  });

  assert.equal(succeeded, true);
  assert.equal(reindexingIds.size, 0);
  assert.deepEqual(errorsById, {});
  assert.equal(activeUpdates.length, 1);
  assert.equal(activeUpdates[0].ai_analysis.caption, 'Updated caption A');

  const cachedA = queryClient.cache.get(JSON.stringify(['photoDetail', 'photo-a']));
  assert.deepEqual(cachedA, updatedA);

  assert.deepEqual(queryClient.operations[0], { type: 'cancel', queryKey: ['photoDetail', 'photo-a'] });
  assert.equal(queryClient.operations[1].type, 'set');
  assert.deepEqual(queryClient.operations[1].queryKey, ['photoDetail', 'photo-a']);

  const invalidatedKeys = queryClient.operations
    .filter((op) => op.type === 'invalidate')
    .map((op) => op.queryKey[0]);
  assert.deepEqual(invalidatedKeys.sort(), ['analyticsStats', 'critiques', 'photos']);
});

test('TC-IDX-20.2: switching A -> B mid-reindex isolates B reindexing state and prevents overwriting B edit buffer while still updating A cache', async () => {
  const queryClient = createFakeQueryClient();
  const deferredA = createDeferred();
  const updatedA = makePhotoDetail('photo-a', 'Reindexed A', ['tagA']);
  let selectedPhotoId = 'photo-a';
  let reindexingIds = new Set();
  let errorsById = {};
  let activeCaptionBuffer = 'Initial A';
  let activeTagsBuffer = ['initA'];

  const reindexPromise = executePhotoReindex({
    targetId: 'photo-a',
    inFlightIds: new Set(),
    requestSeqByPhoto: new Map(),
    reindexPhoto: () => deferredA.promise,
    queryClient,
    getSelectedPhotoId: () => selectedPhotoId,
    isMounted: () => true,
    onStart: (id) => {
      reindexingIds = addReindexingPhotoId(reindexingIds, id);
      errorsById = clearPhotoReindexError(errorsById, id);
    },
    onSuccessActive: (photo) => {
      activeCaptionBuffer = photo.ai_analysis.caption || '';
      activeTagsBuffer = [...photo.ai_analysis.tags];
    },
    onError: (id, message) => {
      errorsById = setPhotoReindexError(errorsById, id, message);
    },
    onFinish: (id) => {
      reindexingIds = removeReindexingPhotoId(reindexingIds, id);
    },
  });

  assert.equal(reindexingIds.has('photo-a'), true);
  assert.equal(reindexingIds.has('photo-b'), false);

  // User switches to photo-b and begins editing its caption/tags
  selectedPhotoId = 'photo-b';
  activeCaptionBuffer = 'User typing on B';
  activeTagsBuffer = ['customB'];

  deferredA.resolve(updatedA);
  const succeeded = await reindexPromise;

  assert.equal(succeeded, true);
  assert.equal(reindexingIds.has('photo-a'), false);
  // B's edit buffer must remain intact!
  assert.equal(activeCaptionBuffer, 'User typing on B');
  assert.deepEqual(activeTagsBuffer, ['customB']);
  // A's cache MUST still be updated so revisiting A does not show stale 5m data
  assert.deepEqual(queryClient.cache.get(JSON.stringify(['photoDetail', 'photo-a'])), updatedA);
});

test('TC-IDX-20.3: switching A -> B -> A before completion preserves A spinner and updates A buffer on completion', async () => {
  const queryClient = createFakeQueryClient();
  const deferredA = createDeferred();
  const updatedA = makePhotoDetail('photo-a', 'Fresh A caption', ['fresh']);
  let selectedPhotoId = 'photo-a';
  let reindexingIds = new Set();
  let activeCaptionBuffer = 'Old A';

  const reindexPromise = executePhotoReindex({
    targetId: 'photo-a',
    inFlightIds: new Set(),
    requestSeqByPhoto: new Map(),
    reindexPhoto: () => deferredA.promise,
    queryClient,
    getSelectedPhotoId: () => selectedPhotoId,
    isMounted: () => true,
    onStart: (id) => {
      reindexingIds = addReindexingPhotoId(reindexingIds, id);
    },
    onSuccessActive: (photo) => {
      activeCaptionBuffer = photo.ai_analysis.caption || '';
    },
    onError: () => {},
    onFinish: (id) => {
      reindexingIds = removeReindexingPhotoId(reindexingIds, id);
    },
  });

  selectedPhotoId = 'photo-b';
  assert.equal(reindexingIds.has('photo-b'), false);
  assert.equal(reindexingIds.has('photo-a'), true);

  // Switch back to A before A finishes
  selectedPhotoId = 'photo-a';
  assert.equal(reindexingIds.has('photo-a'), true);

  deferredA.resolve(updatedA);
  await reindexPromise;

  assert.equal(reindexingIds.has('photo-a'), false);
  assert.equal(activeCaptionBuffer, 'Fresh A caption');
});

test('TC-IDX-20.4: concurrent reindex on A and B tracks per-photo busy state and blocks duplicate reindex on same photo', async () => {
  const queryClient = createFakeQueryClient();
  const deferredA = createDeferred();
  const deferredB = createDeferred();
  const inFlightIds = new Set();
  const requestSeqByPhoto = new Map();
  let selectedPhotoId = 'photo-a';
  let reindexingIds = new Set();
  let callCountA = 0;

  const makeDeps = (targetId, reindexPhoto) => ({
    targetId,
    inFlightIds,
    requestSeqByPhoto,
    reindexPhoto,
    queryClient,
    getSelectedPhotoId: () => selectedPhotoId,
    isMounted: () => true,
    onStart: (id) => {
      reindexingIds = addReindexingPhotoId(reindexingIds, id);
    },
    onSuccessActive: () => {},
    onError: () => {},
    onFinish: (id) => {
      reindexingIds = removeReindexingPhotoId(reindexingIds, id);
    },
  });

  const promiseA1 = executePhotoReindex(
    makeDeps('photo-a', () => {
      callCountA += 1;
      return deferredA.promise;
    }),
  );
  // Duplicate trigger on A while A is still in-flight must be ignored
  const duplicateA = await executePhotoReindex(
    makeDeps('photo-a', () => {
      callCountA += 1;
      return deferredA.promise;
    }),
  );
  assert.equal(duplicateA, false);
  assert.equal(callCountA, 1);

  selectedPhotoId = 'photo-b';
  const promiseB = executePhotoReindex(makeDeps('photo-b', () => deferredB.promise));
  assert.equal(reindexingIds.has('photo-a'), true);
  assert.equal(reindexingIds.has('photo-b'), true);

  deferredA.resolve(makePhotoDetail('photo-a', 'A done'));
  await promiseA1;
  assert.equal(reindexingIds.has('photo-a'), false);
  assert.equal(reindexingIds.has('photo-b'), true);

  deferredB.resolve(makePhotoDetail('photo-b', 'B done'));
  await promiseB;
  assert.equal(reindexingIds.has('photo-b'), false);
});

test('TC-IDX-20.5: reindex errors are isolated per photo and cleared on retry, and unmount skips state setters without losing cache update', async () => {
  const queryClient = createFakeQueryClient();
  const inFlightIds = new Set();
  const requestSeqByPhoto = new Map();
  let reindexingIds = new Set();
  let errorsById = {};
  let mounted = true;
  let stateCallbackCount = 0;

  // Simulate console.error suppression during expected error test
  const origConsoleError = console.error;
  console.error = () => {};
  try {
    const failed = await executePhotoReindex({
      targetId: 'photo-a',
      inFlightIds,
      requestSeqByPhoto,
      reindexPhoto: async () => {
        throw new Error('Failed to reindex photo: File not found');
      },
      queryClient,
      getSelectedPhotoId: () => 'photo-b',
      isMounted: () => mounted,
      onStart: (id) => {
        reindexingIds = addReindexingPhotoId(reindexingIds, id);
        errorsById = clearPhotoReindexError(errorsById, id);
      },
      onSuccessActive: () => {},
      onError: (id, msg) => {
        errorsById = setPhotoReindexError(errorsById, id, msg);
      },
      onFinish: (id) => {
        reindexingIds = removeReindexingPhotoId(reindexingIds, id);
      },
    });

    assert.equal(failed, false);
    assert.equal(errorsById['photo-a'], '재분석 실패: File not found');
    assert.equal(errorsById['photo-b'], undefined);
    assert.equal(inFlightIds.size, 0);

    // Retry clears error immediately on start, then succeeds even if unmounted before settling
    const deferredRetry = createDeferred();
    const retryPromise = executePhotoReindex({
      targetId: 'photo-a',
      inFlightIds,
      requestSeqByPhoto,
      reindexPhoto: () => deferredRetry.promise,
      queryClient,
      getSelectedPhotoId: () => 'photo-a',
      isMounted: () => mounted,
      onStart: (id) => {
        reindexingIds = addReindexingPhotoId(reindexingIds, id);
        errorsById = clearPhotoReindexError(errorsById, id);
      },
      onSuccessActive: () => {
        stateCallbackCount += 1;
      },
      onError: () => {
        stateCallbackCount += 1;
      },
      onFinish: () => {
        stateCallbackCount += 1;
      },
    });

    assert.equal(errorsById['photo-a'], undefined);
    mounted = false;
    const updatedA = makePhotoDetail('photo-a', 'Recovered A');
    deferredRetry.resolve(updatedA);
    await retryPromise;

    assert.equal(stateCallbackCount, 0);
    assert.deepEqual(queryClient.cache.get(JSON.stringify(['photoDetail', 'photo-a'])), updatedA);
  } finally {
    console.error = origConsoleError;
  }
});

test('TC-IDX-20.6: shouldSyncPhotoEditFields protects active editing on same photo while resetting on photo switch', () => {
  assert.equal(shouldSyncPhotoEditFields('photo-a', 'photo-a', true), false);
  assert.equal(shouldSyncPhotoEditFields('photo-a', 'photo-a', false), true);
  assert.equal(shouldSyncPhotoEditFields('photo-b', 'photo-a', true), true);
  assert.equal(shouldSyncPhotoEditFields('photo-a', null, true), true);
  assert.equal(formatReindexErrorMessage(new Error('Failed to reindex photo: GPU error')), '재분석 실패: GPU error');
  assert.equal(formatReindexErrorMessage('unknown'), '사진 재분석 도중 오류가 발생했습니다.');
});
