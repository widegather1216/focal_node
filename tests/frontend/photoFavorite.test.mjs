import test from 'node:test';
import assert from 'node:assert/strict';
import { QueryClient } from '@tanstack/react-query';
import { createFavoriteMutationOptions } from '../../src/utils/photoFavorite.ts';

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function makePhotoSummary(id, isFavorite = false) {
  return {
    id,
    file_name: `${id}.jpg`,
    file_path: `/Trip/${id}.jpg`,
    is_favorite: isFavorite,
    metadata: null,
  };
}

function makePhotoDetail(id, isFavorite = false) {
  return {
    id,
    file_name: `${id}.jpg`,
    file_path: `/Trip/${id}.jpg`,
    file_size: 2048,
    mime_type: 'image/jpeg',
    is_favorite: isFavorite,
    metadata: {
      width: 4000,
      height: 3000,
      color_space: 'sRGB',
      camera_model: 'ILCE-7M4',
      lens_model: null,
      f_number: 2.8,
      focal_length: 35,
      focal_length_35mm: 35,
      crop_factor: 1,
      sensor_format: 'Full Frame',
      shutter_speed: '1/250',
      iso: 100,
      capture_date: null,
    },
    ai_analysis: {
      caption: 'Sample caption',
      tags: ['travel'],
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

function executeFavoriteMutation(queryClient, toggleFavoriteApi, photoId) {
  const options = createFavoriteMutationOptions(queryClient, toggleFavoriteApi);
  return queryClient.getMutationCache().build(queryClient, options).execute(photoId);
}

test('TC-IDX-21.1: syncs all matching photos queries (folder, all, search) and photoDetail cache optimistically and on success', async () => {
  const queryClient = new QueryClient();
  const folderKey = ['photos', '/Trip', '', {}];
  const allKey = ['photos', null, '', {}];
  const searchKey = ['photos', null, 'sunset', {}];
  const unrelatedFolderKey = ['photos', '/Other', '', {}];
  const detailKey = ['photoDetail', 'photo-1'];
  const analyticsKey = ['analyticsStats'];

  queryClient.setQueryData(allKey, { pages: [[makePhotoSummary('photo-1', false)]], pageParams: [0] }, { updatedAt: 1000 });
  queryClient.setQueryData(folderKey, { pages: [[makePhotoSummary('photo-1', false), makePhotoSummary('photo-2', false)]], pageParams: [0] }, { updatedAt: 2000 });
  queryClient.setQueryData(searchKey, [makePhotoSummary('photo-1', false)], { updatedAt: 1500 });
  queryClient.setQueryData(unrelatedFolderKey, { pages: [[makePhotoSummary('photo-9', false)]], pageParams: [0] }, { updatedAt: 500 });
  queryClient.setQueryData(detailKey, makePhotoDetail('photo-1', false), { updatedAt: 2500 });
  queryClient.setQueryData(analyticsKey, { total_photos: 2 }, { updatedAt: 1000 });

  const deferred = createDeferred();
  const mutationPromise = executeFavoriteMutation(queryClient, () => deferred.promise, 'photo-1');

  // Wait a microtask for async onMutate to finish cancelling and applying optimistic update.
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(queryClient.getQueryData(folderKey).pages[0][0].is_favorite, true);
  assert.equal(queryClient.getQueryData(allKey).pages[0][0].is_favorite, true);
  assert.equal(queryClient.getQueryData(searchKey)[0].is_favorite, true);
  assert.equal(queryClient.getQueryData(detailKey).is_favorite, true);

  // Server confirms authoritative value (even if optimistic state had drifted, server wins)
  deferred.resolve({ id: 'photo-1', is_favorite: true });
  const result = await mutationPromise;
  assert.deepEqual(result, { id: 'photo-1', is_favorite: true });

  assert.equal(queryClient.getQueryData(folderKey).pages[0][0].is_favorite, true);
  assert.equal(queryClient.getQueryData(allKey).pages[0][0].is_favorite, true);
  assert.equal(queryClient.getQueryData(searchKey)[0].is_favorite, true);
  assert.equal(queryClient.getQueryData(detailKey).is_favorite, true);
  assert.equal(queryClient.getQueryData(folderKey).pages[0][1].is_favorite, false);
  assert.equal(queryClient.getQueryState(analyticsKey)?.isInvalidated, false);
});

test('TC-IDX-21.2: preserves dataUpdatedAt on all updated photos queries so active folder list ordering is never hijacked', async () => {
  const queryClient = new QueryClient();
  const inactiveAllKey = ['photos', null, '', {}];
  const activeFolderKey = ['photos', '/Trip', '', {}];
  const unrelatedKey = ['photos', '/Other', '', {}];

  queryClient.setQueryData(inactiveAllKey, { pages: [[makePhotoSummary('photo-1', false)]], pageParams: [0] }, { updatedAt: 1000 });
  queryClient.setQueryData(activeFolderKey, { pages: [[makePhotoSummary('photo-1', false)]], pageParams: [0] }, { updatedAt: 5000 });
  queryClient.setQueryData(unrelatedKey, { pages: [[makePhotoSummary('photo-9', false)]], pageParams: [0] }, { updatedAt: 200 });

  await executeFavoriteMutation(
    queryClient,
    async () => ({ id: 'photo-1', is_favorite: true }),
    'photo-1',
  );

  assert.equal(queryClient.getQueryState(inactiveAllKey)?.dataUpdatedAt, 1000);
  assert.equal(queryClient.getQueryState(activeFolderKey)?.dataUpdatedAt, 5000);
  assert.equal(queryClient.getQueryState(unrelatedKey)?.dataUpdatedAt, 200);
});

test('TC-IDX-21.3: rolls back all photos queries and photoDetail on error without polluting uncached photoDetail', async () => {
  const queryClient = new QueryClient();
  const folderKey = ['photos', '/Trip', '', {}];
  const detailKey = ['photoDetail', 'photo-1'];
  const uncachedDetailKey = ['photoDetail', 'photo-2'];

  queryClient.setQueryData(folderKey, { pages: [[makePhotoSummary('photo-1', true), makePhotoSummary('photo-2', false)]], pageParams: [0] }, { updatedAt: 3000 });
  queryClient.setQueryData(detailKey, makePhotoDetail('photo-1', true), { updatedAt: 3100 });

  await assert.rejects(
    executeFavoriteMutation(
      queryClient,
      async () => {
        throw new Error('Network failure');
      },
      'photo-1',
    ),
    /Network failure/,
  );

  assert.equal(queryClient.getQueryData(folderKey).pages[0][0].is_favorite, true);
  assert.equal(queryClient.getQueryData(detailKey).is_favorite, true);
  assert.equal(queryClient.getQueryState(folderKey)?.dataUpdatedAt, 3000);

  // Photo without cached photoDetail also rolls back photos list and leaves photoDetail uncached.
  await assert.rejects(
    executeFavoriteMutation(
      queryClient,
      async () => {
        throw new Error('Server error');
      },
      'photo-2',
    ),
    /Server error/,
  );

  assert.equal(queryClient.getQueryData(folderKey).pages[0][1].is_favorite, false);
  assert.equal(queryClient.getQueryData(uncachedDetailKey), undefined);
});

test('TC-IDX-21.4: serializes rapid concurrent toggles per photo and reconciles partial failure/success cleanly', async () => {
  const queryClient = new QueryClient();
  const folderKey = ['photos', '/Trip', '', {}];
  const detailKey = ['photoDetail', 'photo-1'];

  // Case A: First succeeds (false -> true), second fails -> server truth is true!
  queryClient.setQueryData(folderKey, { pages: [[makePhotoSummary('photo-1', false)]], pageParams: [0] });
  queryClient.setQueryData(detailKey, makePhotoDetail('photo-1', false));

  let callCount = 0;
  let callOrder = [];
  let serverFavorite = false;
  const firstDeferred = createDeferred();
  const secondDeferred = createDeferred();

  const toggleApi = async () => {
    const attempt = ++callCount;
    callOrder.push(`start-${attempt}`);
    if (attempt === 1) {
      const value = await firstDeferred.promise;
      callOrder.push(`end-${attempt}`);
      return value;
    }
    const value = await secondDeferred.promise;
    callOrder.push(`end-${attempt}`);
    return value;
  };

  const p1 = executeFavoriteMutation(queryClient, toggleApi, 'photo-1');
  const p2 = executeFavoriteMutation(queryClient, toggleApi, 'photo-1');

  await new Promise((resolve) => setTimeout(resolve, 0));
  // Because requests are serialized, start-2 must NOT fire before start-1 resolves!
  assert.deepEqual(callOrder, ['start-1']);
  // Two rapid flips from false -> true -> false optimistically
  assert.equal(queryClient.getQueryData(detailKey).is_favorite, false);

  serverFavorite = !serverFavorite;
  firstDeferred.resolve({ id: 'photo-1', is_favorite: serverFavorite });
  await p1;

  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.deepEqual(callOrder, ['start-1', 'end-1', 'start-2']);

  secondDeferred.reject(new Error('Second toggle failed'));
  await assert.rejects(p2, /Second toggle failed/);

  // Final UI state MUST match server truth (true from p1), not baseline (false)!
  assert.equal(queryClient.getQueryData(folderKey).pages[0][0].is_favorite, true);
  assert.equal(queryClient.getQueryData(detailKey).is_favorite, true);

  // Case B: First fails, second succeeds (true -> false) -> server truth is false!
  callOrder = [];
  const d3 = createDeferred();
  const d4 = createDeferred();
  const toggleApiB = async () => {
    const attempt = callOrder.length + 1;
    callOrder.push(attempt);
    return attempt === 1 ? d3.promise : d4.promise;
  };

  const p3 = executeFavoriteMutation(queryClient, toggleApiB, 'photo-1');
  const p4 = executeFavoriteMutation(queryClient, toggleApiB, 'photo-1');
  await new Promise((resolve) => setTimeout(resolve, 0));

  d3.reject(new Error('First toggle failed'));
  await assert.rejects(p3, /First toggle failed/);
  await new Promise((resolve) => setTimeout(resolve, 0));

  serverFavorite = !serverFavorite;
  d4.resolve({ id: 'photo-1', is_favorite: serverFavorite });
  await p4;

  assert.equal(queryClient.getQueryData(folderKey).pages[0][0].is_favorite, false);
  assert.equal(queryClient.getQueryData(detailKey).is_favorite, false);
});

test('TC-IDX-21.5: updates is_favorite in filtered view without breaking navigation and invalidates favorite-filtered queries on success', async () => {
  const queryClient = new QueryClient();
  const favFilterKey = ['photos', null, '', { is_favorite: true }];
  const allKey = ['photos', null, '', {}];

  queryClient.setQueryData(favFilterKey, { pages: [[makePhotoSummary('photo-1', true), makePhotoSummary('photo-2', true)]], pageParams: [0] });
  queryClient.setQueryData(allKey, { pages: [[makePhotoSummary('photo-1', true), makePhotoSummary('photo-2', true)]], pageParams: [0] });

  await executeFavoriteMutation(
    queryClient,
    async () => ({ id: 'photo-1', is_favorite: false }),
    'photo-1',
  );

  // Item remains in list cache with updated flag (preserving arrow navigation) while favFilterKey is invalidated for refetch.
  assert.equal(queryClient.getQueryData(favFilterKey).pages[0].length, 2);
  assert.equal(queryClient.getQueryData(favFilterKey).pages[0][0].is_favorite, false);
  assert.equal(queryClient.getQueryState(favFilterKey)?.isInvalidated, true);
  assert.equal(queryClient.getQueryState(allKey)?.isInvalidated, false);
});

test('TC-IDX-21.6: does not cancel an initial pending photoDetail fetch and invalidates it on success', async () => {
  const queryClient = new QueryClient();
  const folderKey = ['photos', '/Trip', '', {}];
  const detailKey = ['photoDetail', 'photo-1'];
  const detailFetchDeferred = createDeferred();
  let detailCancelled = false;

  queryClient.setQueryData(folderKey, { pages: [[makePhotoSummary('photo-1', false)]], pageParams: [0] });

  // Start an initial pending photoDetail fetch (data is still undefined).
  const detailFetchPromise = queryClient.fetchQuery({
    queryKey: detailKey,
    queryFn: async ({ signal }) => {
      signal.addEventListener('abort', () => {
        detailCancelled = true;
      });
      return await detailFetchDeferred.promise;
    },
  });

  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(queryClient.getQueryState(detailKey)?.fetchStatus, 'fetching');
  assert.equal(queryClient.getQueryData(detailKey), undefined);

  await executeFavoriteMutation(
    queryClient,
    async () => ({ id: 'photo-1', is_favorite: true }),
    'photo-1',
  );

  // Initial pending fetch must NOT have been cancelled!
  assert.equal(detailCancelled, false);
  assert.equal(queryClient.getQueryState(detailKey)?.isInvalidated, true);

  detailFetchDeferred.resolve(makePhotoDetail('photo-1', false));
  await detailFetchPromise;
});
