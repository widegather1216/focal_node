import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {
  DEFAULT_GALLERY_COLUMNS,
  bindGalleryContainerResize,
  computeGalleryColumnCount,
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
