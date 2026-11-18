import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { QueryClient } from '@tanstack/react-query';
import { extractResponseErrorMessage } from '../../src/utils/apiError.ts';
import {
  fetchPhotosRequest,
  postJsonRequest,
  searchPhotosRequest,
} from '../../src/utils/searchRequest.ts';

function createAbortAwareFetchStub(capturedCalls) {
  return (url, init) => {
    capturedCalls.push({ url, init });
    const signal = init?.signal;

    return new Promise((resolve, reject) => {
      if (signal?.aborted) {
        reject(new DOMException('The operation was aborted.', 'AbortError'));
        return;
      }

      const onAbort = () => {
        reject(new DOMException('The operation was aborted.', 'AbortError'));
      };
      signal?.addEventListener('abort', onAbort, { once: true });

      if (!signal) {
        resolve(new Response(JSON.stringify([]), { status: 200 }));
      }
    });
  };
}

test('TC-SRC-17.1: fetchPhotosRequest, postJsonRequest, and searchPhotosRequest forward signal and preserve legacy calls without signal', async () => {
  const capturedCalls = [];
  const fetchStub = async (url, init) => {
    capturedCalls.push({ url, init, argCount: init === undefined ? 1 : 2 });
    return new Response(JSON.stringify([{ id: 'p1', file_name: 'a.jpg', file_path: '/a.jpg', is_favorite: false }]), {
      status: 200,
    });
  };

  await fetchPhotosRequest({
    baseUrl: 'http://127.0.0.1:8123',
    limit: 50,
    offset: 0,
    folder: '/Trip/Seoul',
    fetchImpl: fetchStub,
  });
  assert.equal(capturedCalls[0].url, 'http://127.0.0.1:8123/api/photos?limit=50&offset=0&parent_dir=%2FTrip%2FSeoul');
  assert.equal(capturedCalls[0].argCount, 1);

  const controller = new AbortController();
  await fetchPhotosRequest({
    baseUrl: 'http://127.0.0.1:8123',
    limit: 50,
    offset: 50,
    folder: null,
    signal: controller.signal,
    fetchImpl: fetchStub,
  });
  assert.equal(capturedCalls[1].init.signal, controller.signal);

  await searchPhotosRequest({
    baseUrl: 'http://127.0.0.1:8123',
    query: 'sunset',
    filters: { is_favorite: true },
    limit: 50,
    offset: 0,
    folder: '/Trip',
    signal: controller.signal,
    fetchImpl: fetchStub,
  });
  assert.equal(capturedCalls[2].url, 'http://127.0.0.1:8123/api/search');
  assert.equal(capturedCalls[2].init.signal, controller.signal);

  await searchPhotosRequest({
    baseUrl: 'http://127.0.0.1:8123',
    query: 'similar:photo-99',
    filters: undefined,
    limit: 20,
    offset: 0,
    signal: controller.signal,
    fetchImpl: fetchStub,
  });
  assert.equal(capturedCalls[3].url, 'http://127.0.0.1:8123/api/search/similar');
  assert.equal(capturedCalls[3].init.signal, controller.signal);

  await postJsonRequest({
    baseUrl: 'http://127.0.0.1:8123',
    endpoint: '/api/search',
    payload: { query: 'legacy', limit: 10, offset: 0 },
    errorContext: 'Failed',
    fetchImpl: fetchStub,
  });
  assert.equal('signal' in capturedCalls[4].init, false);
});

test('TC-SRC-17.2: aborting AbortController rejects in-flight fetch/search requests with AbortError and preserves AbortError in extractResponseErrorMessage', async () => {
  const capturedCalls = [];
  const fetchStub = createAbortAwareFetchStub(capturedCalls);

  const searchController = new AbortController();
  const pendingSearch = searchPhotosRequest({
    baseUrl: 'http://127.0.0.1:8123',
    query: 'rainy night',
    filters: undefined,
    limit: 50,
    offset: 0,
    signal: searchController.signal,
    fetchImpl: fetchStub,
  });
  searchController.abort();
  await assert.rejects(pendingSearch, (error) => error?.name === 'AbortError');

  const fetchController = new AbortController();
  const pendingFetch = fetchPhotosRequest({
    baseUrl: 'http://127.0.0.1:8123',
    limit: 50,
    offset: 0,
    folder: null,
    signal: fetchController.signal,
    fetchImpl: fetchStub,
  });
  fetchController.abort();
  await assert.rejects(pendingFetch, (error) => error?.name === 'AbortError');

  const abortingErrorResponse = {
    statusText: 'Internal Server Error',
    json: async () => {
      throw new DOMException('Body read aborted', 'AbortError');
    },
  };
  await assert.rejects(
    extractResponseErrorMessage(abortingErrorResponse, 'Failed to search photos'),
    (error) => error?.name === 'AbortError',
  );
});

test('TC-SRC-17.3: TanStack QueryClient cancelQueries aborts queryFn signal and prevents stale fetch completion', async () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const observedSignals = [];
  const startedRequests = [];

  const controlledFetch = (url, init) => {
    observedSignals.push(init?.signal ?? null);
    const bodyText = String(init?.body ?? '');
    if (bodyText.includes('"query":"first"')) {
      return new Promise((_, reject) => {
        startedRequests.push('first');
        init.signal.addEventListener(
          'abort',
          () => reject(new DOMException('Query cancelled', 'AbortError')),
          { once: true },
        );
      });
    }
    startedRequests.push('second');
    return Promise.resolve(
      new Response(JSON.stringify([{ id: 'second-1', file_name: 's.jpg', file_path: '/s.jpg', is_favorite: false }]), {
        status: 200,
      }),
    );
  };

  try {
    const firstQueryKey = ['photos', null, 'first', {}];
    const firstPromise = queryClient.fetchInfiniteQuery({
      queryKey: firstQueryKey,
      initialPageParam: 0,
      queryFn: ({ pageParam = 0, signal }) =>
        searchPhotosRequest({
          baseUrl: 'http://127.0.0.1:8123',
          query: 'first',
          filters: {},
          limit: 50,
          offset: Number(pageParam) * 50,
          folder: null,
          signal,
          fetchImpl: controlledFetch,
        }),
    });

    await new Promise((resolve) => setTimeout(resolve, 10));
    assert.deepEqual(startedRequests, ['first']);
    assert.equal(observedSignals[0]?.aborted, false);

    await queryClient.cancelQueries({ queryKey: firstQueryKey });
    assert.equal(observedSignals[0]?.aborted, true);
    await assert.rejects(firstPromise);

    const secondData = await queryClient.fetchInfiniteQuery({
      queryKey: ['photos', null, 'second', {}],
      initialPageParam: 0,
      queryFn: ({ pageParam = 0, signal }) =>
        searchPhotosRequest({
          baseUrl: 'http://127.0.0.1:8123',
          query: 'second',
          filters: {},
          limit: 50,
          offset: Number(pageParam) * 50,
          folder: null,
          signal,
          fetchImpl: controlledFetch,
        }),
    });
    assert.equal(secondData.pages[0][0].id, 'second-1');
  } finally {
    queryClient.clear();
  }
});

test('TC-SRC-17.4: PhotoGallery and ApiClient wire AbortSignal through queryFn, searchPhotos, postJson, and fetchPhotos', () => {
  const gallerySource = fs.readFileSync(path.resolve(process.cwd(), 'src/components/PhotoGallery.tsx'), 'utf8');
  const apiSource = fs.readFileSync(path.resolve(process.cwd(), 'src/services/api.ts'), 'utf8');

  assert.equal(/queryFn:\s*async\s*\(\{\s*pageParam\s*=\s*0,\s*signal\s*\}\)/.test(gallerySource), true);
  assert.equal(/api\.searchPhotos\([\s\S]*?signal,?\s*\)/.test(gallerySource), true);
  assert.equal(/api\.fetchPhotos\([\s\S]*?signal,?\s*\)/.test(gallerySource), true);

  assert.equal(/async fetchPhotos\([\s\S]*?signal\?: AbortSignal/.test(apiSource), true);
  assert.equal(/private async postJson<T>\([\s\S]*?signal\?: AbortSignal/.test(apiSource), true);
  assert.equal(/async searchPhotos\([\s\S]*?signal\?: AbortSignal/.test(apiSource), true);
});
