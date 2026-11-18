import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {
  Virtualizer,
  elementScroll,
  observeElementOffset,
} from '@tanstack/virtual-core';
import {
  DEFAULT_GALLERY_COLUMNS,
  bindGalleryContainerResize,
  buildGalleryQueryContextKey,
  computeGalleryColumnCount,
  createSafeObserveElementOffset,
  observeGalleryElementOffset,
  resetVirtualizerScrollPosition,
  syncVirtualizerOnContainerMount,
} from '../../src/utils/galleryLayout.ts';

function createFakeResizeObserverHarness() {
  const observerRecords = [];

  const factory = (onResize) => {
    const record = {
      observedTarget: null,
      disconnected: false,
      triggerResize: () => {
        if (!record.disconnected && record.observedTarget) {
          onResize();
        }
      },
      simulateExternalResizeIgnoringDisconnect: () => {
        onResize();
      },
    };
    observerRecords.push(record);

    return {
      observe: (target) => {
        record.observedTarget = target;
      },
      disconnect: () => {
        record.disconnected = true;
      },
    };
  };

  return { observerRecords, factory };
}

test('TC-SRC-13.1: computeGalleryColumnCount computes clamped columns and preserves fallback for invalid widths', () => {
  assert.equal(DEFAULT_GALLERY_COLUMNS, 4);
  assert.equal(computeGalleryColumnCount(300), 2);
  assert.equal(computeGalleryColumnCount(460), 2);
  assert.equal(computeGalleryColumnCount(690), 3);
  assert.equal(computeGalleryColumnCount(920), 4);
  assert.equal(computeGalleryColumnCount(1200), 5);
  assert.equal(computeGalleryColumnCount(1840), 8);
  assert.equal(computeGalleryColumnCount(3200), 8);

  assert.equal(computeGalleryColumnCount(0), 4);
  assert.equal(computeGalleryColumnCount(0, 6), 6);
  assert.equal(computeGalleryColumnCount(-50, 5), 5);
  assert.equal(computeGalleryColumnCount(Number.NaN, 3), 3);
  assert.equal(computeGalleryColumnCount(Number.POSITIVE_INFINITY, 7), 7);
});

test('TC-SRC-13.2: bindGalleryContainerResize skips ResizeObserver creation when container is null (pending/empty)', () => {
  const harness = createFakeResizeObserverHarness();
  const observedColumns = [];

  const cleanup = bindGalleryContainerResize(
    null,
    (nextColumns) => observedColumns.push(nextColumns),
    harness.factory,
  );

  assert.equal(harness.observerRecords.length, 0);
  assert.deepEqual(observedColumns, []);
  cleanup();
});

test('TC-SRC-13.3: pending -> success -> resize -> pending/empty -> success -> resize -> unmount rebinds ResizeObserver cleanly', () => {
  const harness = createFakeResizeObserverHarness();
  let columnCount = DEFAULT_GALLERY_COLUMNS;
  const setColumnCount = (nextColumns) => {
    columnCount = nextColumns;
  };

  // Phase 1: Initial mount in status === 'pending' (container is null)
  let cleanup = bindGalleryContainerResize(null, setColumnCount, harness.factory);
  assert.equal(harness.observerRecords.length, 0);
  assert.equal(columnCount, 4);

  // Phase 2: Query resolves (status === 'success', first container mounts at 1200px)
  cleanup();
  const firstContainer = { clientWidth: 1200 };
  cleanup = bindGalleryContainerResize(firstContainer, setColumnCount, harness.factory);
  assert.equal(harness.observerRecords.length, 1);
  assert.equal(harness.observerRecords[0].observedTarget, firstContainer);
  assert.equal(harness.observerRecords[0].disconnected, false);
  assert.equal(columnCount, 5);

  // Phase 3: Viewport widens to 1650px
  firstContainer.clientWidth = 1650;
  harness.observerRecords[0].triggerResize();
  assert.equal(columnCount, 7);

  // Phase 4: Query enters pending/empty state (container unmounts -> null)
  cleanup();
  assert.equal(harness.observerRecords[0].disconnected, true);
  cleanup = bindGalleryContainerResize(null, setColumnCount, harness.factory);
  assert.equal(harness.observerRecords.length, 1);

  // Stale resize on detached firstContainer must not update columnCount
  firstContainer.clientWidth = 500;
  harness.observerRecords[0].triggerResize();
  assert.equal(columnCount, 7);

  // Phase 5: Query resolves again with a newly mounted container at 600px
  cleanup();
  const secondContainer = { clientWidth: 600 };
  cleanup = bindGalleryContainerResize(secondContainer, setColumnCount, harness.factory);
  assert.equal(harness.observerRecords.length, 2);
  assert.equal(harness.observerRecords[1].observedTarget, secondContainer);
  assert.equal(harness.observerRecords[1].disconnected, false);
  assert.equal(columnCount, 2);

  // Phase 6: Resize newly mounted container to 1400px
  secondContainer.clientWidth = 1400;
  harness.observerRecords[1].triggerResize();
  assert.equal(columnCount, 6);

  // Phase 7: Component unmount disconnects active observer
  cleanup();
  assert.equal(harness.observerRecords[1].disconnected, true);
});

test('TC-SRC-13.4: zero-width measurement keeps existing columnCount until positive width arrives and handles missing ResizeObserver', () => {
  const harness = createFakeResizeObserverHarness();
  let columnCount = 5;
  const setColumnCount = (nextColumns) => {
    columnCount = nextColumns;
  };

  const container = { clientWidth: 0 };
  const cleanup = bindGalleryContainerResize(container, setColumnCount, harness.factory);
  assert.equal(columnCount, 5);

  container.clientWidth = 1850;
  harness.observerRecords[0].triggerResize();
  assert.equal(columnCount, 8);
  cleanup();

  // Missing global ResizeObserver degrades with warning instead of throwing
  const warnings = [];
  const originalWarn = console.warn;
  console.warn = (message) => warnings.push(message);
  try {
    const fallbackCleanup = bindGalleryContainerResize({ clientWidth: 960 }, setColumnCount);
    assert.equal(columnCount, 4);
    assert.equal(warnings.length, 1);
    fallbackCleanup();
  } finally {
    console.warn = originalWarn;
  }
});

test('TC-SRC-13.5: PhotoGallery wires callback ref and scrollContainer-dependent ResizeObserver without empty-deps mount bug', () => {
  const gallerySourcePath = path.resolve(process.cwd(), 'src/components/PhotoGallery.tsx');
  const sourceText = fs.readFileSync(gallerySourcePath, 'utf8');

  assert.equal(sourceText.includes('bindGalleryContainerResize(scrollContainer, setColumnCount)'), true);
  assert.equal(sourceText.includes('[scrollContainer]'), true);
  assert.equal(sourceText.includes('ref={handleScrollContainerRef}'), true);
  assert.equal(sourceText.includes('getScrollElement: () => scrollElementRef.current'), true);
  assert.equal(/useEffect\(\(\)\s*=>\s*\{[\s\S]*ResizeObserver[\s\S]*\},\s*\[\s*\]\s*\)/.test(sourceText), false);
});

function createFakeVirtualScrollContainer(initialRowCount = 50, clientHeight = 800) {
  const scrollListeners = new Set();
  let totalHeight = initialRowCount * 220;
  const scrollToCalls = [];

  const container = {
    clientWidth: 1000,
    clientHeight,
    scrollTop: 0,
    get scrollHeight() {
      return totalHeight;
    },
    setRowCount(rowCount) {
      totalHeight = rowCount * 220;
    },
    scrollToCalls,
    ownerDocument: { defaultView: globalThis },
    addEventListener(eventName, listener) {
      if (eventName === 'scroll') {
        scrollListeners.add(listener);
      }
    },
    removeEventListener(eventName, listener) {
      if (eventName === 'scroll') {
        scrollListeners.delete(listener);
      }
    },
    emitScroll(nextTop) {
      container.scrollTop = nextTop;
      for (const listener of scrollListeners) {
        listener();
      }
    },
    scrollTo(options) {
      const targetTop = options?.top ?? 0;
      scrollToCalls.push(targetTop);
      const maxTop = Math.max(0, totalHeight - container.clientHeight);
      container.scrollTop = Math.max(0, Math.min(maxTop, targetTop));
    },
  };

  return container;
}

function createRealVirtualizerHarness(initialRowCount = 50) {
  let activeContainer = createFakeVirtualScrollContainer(initialRowCount);

  const virtualizer = new Virtualizer({
    count: initialRowCount,
    getScrollElement: () => activeContainer,
    estimateSize: () => 220,
    overscan: 3,
    observeElementRect: (_instance, onRectChange) => {
      onRectChange({ width: 1000, height: 800 });
      return () => {};
    },
    observeElementOffset,
    scrollToFn: elementScroll,
  });

  const unmountDidMount = virtualizer._didMount();
  virtualizer._willUpdate();

  return {
    virtualizer,
    getContainer: () => activeContainer,
    setContainer: (nextContainer) => {
      activeContainer = nextContainer;
    },
    updateCount: (nextCount) => {
      virtualizer.setOptions({ ...virtualizer.options, count: nextCount });
    },
    cleanup: () => {
      unmountDidMount();
    },
  };
}

test('TC-SRC-18.1: demonstrates @tanstack/virtual-core root cause and verifies pending -> 5 rows remount resets scrollOffset to include row 0', () => {
  // Baseline bug reproduction (without reset): 50 rows -> scroll(5000) -> pending -> 5 rows omits row 0 and scrolls new container to 5000
  const unfixed = createRealVirtualizerHarness(50);
  unfixed.getContainer().emitScroll(5000);
  assert.equal(unfixed.virtualizer.scrollOffset, 5000);

  unfixed.setContainer(null);
  unfixed.updateCount(0);
  unfixed.virtualizer._willUpdate();
  assert.equal(unfixed.virtualizer.scrollElement, null);
  assert.equal(unfixed.virtualizer.scrollOffset, 5000);

  const unfixedRemounted = createFakeVirtualScrollContainer(5);
  unfixed.setContainer(unfixedRemounted);
  unfixed.updateCount(5);
  assert.deepEqual(
    unfixed.virtualizer.getVirtualItems().map((item) => item.index),
    [1, 2, 3, 4],
  );
  unfixed.virtualizer._willUpdate();
  assert.deepEqual(unfixedRemounted.scrollToCalls, [5000]);
  unfixed.cleanup();

  // Fixed behavior: unmount/remount sync clears stale scrollOffset before render and _willUpdate
  const fixed = createRealVirtualizerHarness(50);
  fixed.getContainer().emitScroll(5000);

  fixed.setContainer(null);
  syncVirtualizerOnContainerMount(fixed.virtualizer, null);
  fixed.updateCount(0);
  fixed.virtualizer._willUpdate();
  assert.equal(fixed.virtualizer.scrollOffset, 0);

  const fixedRemounted = createFakeVirtualScrollContainer(5);
  fixed.setContainer(fixedRemounted);
  fixed.updateCount(5);
  assert.deepEqual(
    fixed.virtualizer.getVirtualItems().map((item) => item.index),
    [0, 1, 2, 3, 4],
  );
  syncVirtualizerOnContainerMount(fixed.virtualizer, fixedRemounted);
  fixed.virtualizer._willUpdate();
  assert.deepEqual(fixedRemounted.scrollToCalls, [0]);
  assert.equal(fixedRemounted.scrollTop, 0);
  fixed.cleanup();
});

test('TC-SRC-18.2: cached query switch (50 rows -> scroll(5000) -> cached 5 rows without unmount) resets scrollOffset and scrollTop before render', () => {
  // Baseline bug reproduction (without reset): cached 5 rows omits row 0 and retains scrollTop = 5000
  const unfixed = createRealVirtualizerHarness(50);
  unfixed.getContainer().emitScroll(5000);
  unfixed.getContainer().setRowCount(5);
  unfixed.updateCount(5);
  assert.deepEqual(
    unfixed.virtualizer.getVirtualItems().map((item) => item.index),
    [1, 2, 3, 4],
  );
  assert.equal(unfixed.getContainer().scrollTop, 5000);
  unfixed.cleanup();

  // Fixed behavior: query context change resets virtualizer before getVirtualItems() and resets scrollTop on commit
  const fixed = createRealVirtualizerHarness(50);
  const container = fixed.getContainer();
  container.emitScroll(5000);

  const prevContextKey = buildGalleryQueryContextKey('/photos/a', '', {});
  const nextContextKey = buildGalleryQueryContextKey('/photos/b', '', {});
  assert.notEqual(prevContextKey, nextContextKey);

  container.setRowCount(5);
  fixed.updateCount(5);
  resetVirtualizerScrollPosition(fixed.virtualizer, null);
  assert.deepEqual(
    fixed.virtualizer.getVirtualItems().map((item) => item.index),
    [0, 1, 2, 3, 4],
  );
  fixed.virtualizer._willUpdate();
  resetVirtualizerScrollPosition(fixed.virtualizer, container);
  assert.equal(container.scrollTop, 0);
  assert.equal(fixed.virtualizer.scrollOffset, 0);
  fixed.cleanup();
});

test('TC-SRC-18.3: fetchNextPage infinite scroll (50 -> 100 rows under same query context) preserves scrollOffset and scrollTop', () => {
  const harness = createRealVirtualizerHarness(50);
  const container = harness.getContainer();
  container.emitScroll(5000);

  const initialKey = buildGalleryQueryContextKey('/photos/a', 'sunset', { is_favorite: true });
  const nextPageKey = buildGalleryQueryContextKey('/photos/a', 'sunset', { is_favorite: true });
  assert.equal(initialKey, nextPageKey);

  container.setRowCount(100);
  harness.updateCount(100);
  const itemsAfterAppend = harness.virtualizer.getVirtualItems().map((item) => item.index);
  harness.virtualizer._willUpdate();

  assert.equal(harness.virtualizer.scrollOffset, 5000);
  assert.equal(container.scrollTop, 5000);
  assert.equal(itemsAfterAppend.includes(0), false);
  assert.equal(itemsAfterAppend.includes(22), true);
  harness.cleanup();
});

test('TC-SRC-18.4: buildGalleryQueryContextKey normalizes filter ordering/empties and detects folder, query, and filter transitions', () => {
  const baseKey = buildGalleryQueryContextKey('/photos', 'beach', {
    iso_min: 100,
    is_favorite: true,
    camera_model: '   ',
    lens_model: undefined,
  });
  const reorderedKey = buildGalleryQueryContextKey('/photos', 'beach', {
    is_favorite: true,
    iso_min: 100,
  });
  assert.equal(baseKey, reorderedKey);

  assert.notEqual(
    baseKey,
    buildGalleryQueryContextKey('/photos/sub', 'beach', { is_favorite: true, iso_min: 100 }),
  );
  assert.notEqual(
    baseKey,
    buildGalleryQueryContextKey('/photos', 'forest', { is_favorite: true, iso_min: 100 }),
  );
  assert.notEqual(
    baseKey,
    buildGalleryQueryContextKey('/photos', 'beach', { is_favorite: true, iso_min: 200 }),
  );
});

test('TC-SRC-18.5: PhotoGallery wires queryContextKey, pre-render virtualizer reset, layout commit reset, and container mount sync', () => {
  const gallerySourcePath = path.resolve(process.cwd(), 'src/components/PhotoGallery.tsx');
  const sourceText = fs.readFileSync(gallerySourcePath, 'utf8');

  assert.equal(sourceText.includes('buildGalleryQueryContextKey('), true);
  assert.equal(sourceText.includes('resetVirtualizerScrollPosition('), true);
  assert.equal(sourceText.includes('syncVirtualizerOnContainerMount('), true);
  assert.equal(sourceText.includes('useLayoutEffect('), true);
});

function createFakeTimerWindow() {
  let currentTimeMs = 0;
  let nextTimerId = 1;
  const scheduledTimers = new Map();

  return {
    setTimeout(callback, delayMs = 0) {
      const timerId = nextTimerId++;
      scheduledTimers.set(timerId, {
        fireAtMs: currentTimeMs + delayMs,
        callback,
      });
      return timerId;
    },
    clearTimeout(timerId) {
      scheduledTimers.delete(timerId);
    },
    getPendingTimerCount() {
      return scheduledTimers.size;
    },
    advanceBy(deltaMs) {
      const targetTimeMs = currentTimeMs + deltaMs;
      while (true) {
        let earliestTimerId = null;
        let earliestTimer = null;
        for (const [timerId, timerEntry] of scheduledTimers.entries()) {
          if (
            timerEntry.fireAtMs <= targetTimeMs &&
            (!earliestTimer || timerEntry.fireAtMs < earliestTimer.fireAtMs)
          ) {
            earliestTimerId = timerId;
            earliestTimer = timerEntry;
          }
        }
        if (!earliestTimer || earliestTimerId === null) {
          break;
        }
        scheduledTimers.delete(earliestTimerId);
        currentTimeMs = earliestTimer.fireAtMs;
        earliestTimer.callback();
      }
      currentTimeMs = targetTimeMs;
    },
  };
}

function createTimedVirtualScrollContainer(fakeWindow, initialRowCount = 50) {
  const container = createFakeVirtualScrollContainer(initialRowCount);
  container.ownerDocument = { defaultView: fakeWindow };
  return container;
}

function createTimedVirtualizerHarness(fakeWindow, offsetObserver, initialRowCount = 50) {
  let activeContainer = createTimedVirtualScrollContainer(fakeWindow, initialRowCount);

  const virtualizer = new Virtualizer({
    count: initialRowCount,
    getScrollElement: () => activeContainer,
    estimateSize: () => 220,
    overscan: 3,
    observeElementRect: (_instance, onRectChange) => {
      onRectChange({ width: 1000, height: 800 });
      return () => {};
    },
    observeElementOffset: offsetObserver,
    scrollToFn: elementScroll,
  });

  const unmountDidMount = virtualizer._didMount();
  virtualizer._willUpdate();

  return {
    virtualizer,
    getContainer: () => activeContainer,
    setContainer: (nextContainer) => {
      activeContainer = nextContainer;
    },
    updateCount: (nextCount) => {
      virtualizer.setOptions({ ...virtualizer.options, count: nextCount });
    },
    cleanup: () => {
      unmountDidMount();
    },
  };
}

test('TC-SRC-19.1: blocks stale 150ms fallback debounce timer after <150ms unmount/remount while reproducing unfixed Red failure', () => {
  // Red baseline with raw observeElementOffset:
  // t=0ms scroll(3000) -> t=30ms unmount/cleanup -> t=60ms remount(scrollTop=0) -> t=150ms stale timer resurrects scrollOffset=3000
  const unfixedWindow = createFakeTimerWindow();
  const unfixed = createTimedVirtualizerHarness(unfixedWindow, observeElementOffset, 50);
  unfixed.getContainer().emitScroll(3000);
  assert.equal(unfixed.virtualizer.scrollOffset, 3000);

  unfixedWindow.advanceBy(30);
  unfixed.setContainer(null);
  syncVirtualizerOnContainerMount(unfixed.virtualizer, null);
  unfixed.updateCount(0);
  unfixed.virtualizer._willUpdate();
  assert.equal(unfixed.virtualizer.scrollOffset, 0);

  unfixedWindow.advanceBy(30);
  const unfixedRemounted = createTimedVirtualScrollContainer(unfixedWindow, 5);
  unfixed.setContainer(unfixedRemounted);
  unfixed.updateCount(5);
  unfixed.virtualizer._willUpdate();
  assert.deepEqual(
    unfixed.virtualizer.getVirtualItems().map((item) => item.index),
    [0, 1, 2, 3, 4],
  );

  unfixedWindow.advanceBy(90);
  assert.equal(unfixed.virtualizer.scrollOffset, 3000);
  assert.deepEqual(
    unfixed.virtualizer.getVirtualItems().map((item) => item.index),
    [1, 2, 3, 4],
  );
  unfixed.cleanup();

  // Green fix with observeGalleryElementOffset:
  // Stale timer at t=150ms is blocked by isDisposed guard; scrollOffset=0 and row 0 stay intact
  const fixedWindow = createFakeTimerWindow();
  const fixed = createTimedVirtualizerHarness(fixedWindow, observeGalleryElementOffset, 50);
  fixed.getContainer().emitScroll(3000);
  assert.equal(fixed.virtualizer.scrollOffset, 3000);
  assert.equal(fixed.virtualizer.isScrolling, true);

  fixedWindow.advanceBy(30);
  fixed.setContainer(null);
  syncVirtualizerOnContainerMount(fixed.virtualizer, null);
  fixed.updateCount(0);
  fixed.virtualizer._willUpdate();
  assert.equal(fixed.virtualizer.scrollOffset, 0);

  fixedWindow.advanceBy(30);
  const fixedRemounted = createTimedVirtualScrollContainer(fixedWindow, 5);
  fixed.setContainer(fixedRemounted);
  fixed.updateCount(5);
  fixed.virtualizer._willUpdate();
  syncVirtualizerOnContainerMount(fixed.virtualizer, fixedRemounted);
  assert.deepEqual(
    fixed.virtualizer.getVirtualItems().map((item) => item.index),
    [0, 1, 2, 3, 4],
  );

  fixedWindow.advanceBy(90);
  assert.equal(fixed.virtualizer.scrollOffset, 0);
  assert.equal(fixed.virtualizer.isScrolling, false);
  assert.equal(fixedRemounted.scrollTop, 0);
  assert.deepEqual(
    fixed.virtualizer.getVirtualItems().map((item) => item.index),
    [0, 1, 2, 3, 4],
  );
  fixed.cleanup();
});

test('TC-SRC-19.2: preserves post-remount scrolling/debounce completion and safely handles missing cleanup or repeated dispose', () => {
  const fakeWindow = createFakeTimerWindow();
  const harness = createTimedVirtualizerHarness(fakeWindow, observeGalleryElementOffset, 50);

  harness.getContainer().emitScroll(3000);
  fakeWindow.advanceBy(30);
  harness.setContainer(null);
  syncVirtualizerOnContainerMount(harness.virtualizer, null);
  harness.updateCount(0);
  harness.virtualizer._willUpdate();

  fakeWindow.advanceBy(30);
  const remountedContainer = createTimedVirtualScrollContainer(fakeWindow, 50);
  harness.setContainer(remountedContainer);
  harness.updateCount(50);
  harness.virtualizer._willUpdate();

  // Wait past old t=150ms timer, then scroll the newly mounted container
  fakeWindow.advanceBy(100);
  assert.equal(harness.virtualizer.scrollOffset, 0);

  remountedContainer.emitScroll(1540);
  assert.equal(harness.virtualizer.scrollOffset, 1540);
  assert.equal(harness.virtualizer.isScrolling, true);

  fakeWindow.advanceBy(150);
  assert.equal(harness.virtualizer.scrollOffset, 1540);
  assert.equal(harness.virtualizer.isScrolling, false);
  harness.cleanup();

  // Base observer returning undefined (e.g., null scrollElement) and double-cleanup idempotency
  const emittedEvents = [];
  let lateCallback = null;
  let baseCleanupCalls = 0;

  const noCleanupObserver = createSafeObserveElementOffset((_instance, onOffsetChange) => {
    lateCallback = onOffsetChange;
    return undefined;
  });
  const missingCleanup = noCleanupObserver({}, (offset, isScrolling) => {
    emittedEvents.push([offset, isScrolling]);
  });
  assert.equal(missingCleanup, undefined);
  lateCallback?.(999, false);
  assert.deepEqual(emittedEvents, []);

  const normalObserver = createSafeObserveElementOffset((_instance, onOffsetChange) => {
    onOffsetChange(120, true);
    lateCallback = onOffsetChange;
    return () => {
      baseCleanupCalls += 1;
    };
  });
  const dispose = normalObserver({}, (offset, isScrolling) => {
    emittedEvents.push([offset, isScrolling]);
  });
  assert.equal(typeof dispose, 'function');
  dispose?.();
  dispose?.();
  lateCallback?.(240, false);
  assert.equal(baseCleanupCalls, 1);
  assert.deepEqual(emittedEvents, [[120, true]]);
});

test('TC-SRC-19.3: PhotoGallery passes observeGalleryElementOffset to useVirtualizer', () => {
  const gallerySourcePath = path.resolve(process.cwd(), 'src/components/PhotoGallery.tsx');
  const sourceText = fs.readFileSync(gallerySourcePath, 'utf8');

  assert.equal(sourceText.includes('observeGalleryElementOffset'), true);
  assert.equal(
    /observeElementOffset\s*:\s*observeGalleryElementOffset/.test(sourceText),
    true,
  );
});
