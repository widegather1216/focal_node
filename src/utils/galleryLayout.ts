export const DEFAULT_GALLERY_COLUMNS = 4;
export const MIN_GALLERY_COLUMNS = 2;
export const MAX_GALLERY_COLUMNS = 8;
export const GALLERY_CARD_TARGET_WIDTH_PX = 230;

export interface ResizableContainerElement {
  readonly clientWidth: number;
}

export interface ContainerResizeObserver {
  observe: (target: ResizableContainerElement) => void;
  disconnect: () => void;
}

export type ResizeObserverFactory = (
  onResize: () => void,
) => ContainerResizeObserver;

function defaultResizeObserverFactory(
  onResize: () => void,
): ContainerResizeObserver {
  if (typeof ResizeObserver === 'undefined') {
    console.warn('ResizeObserver is unavailable; falling back to default gallery column count.');
    return {
      observe: () => {},
      disconnect: () => {},
    };
  }
  const nativeObserver = new ResizeObserver(onResize);
  return {
    observe: (target) => {
      // PhotoGallery mounts an HTMLDivElement at runtime; fake containers in tests only expose clientWidth.
      nativeObserver.observe(target as unknown as Element);
    },
    disconnect: () => {
      nativeObserver.disconnect();
    },
  };
}

/**
 * Computes responsive grid column count targeting ~230px cards, clamped to [2, 8].
 */
export function computeGalleryColumnCount(
  containerWidth: number,
  fallbackColumns = DEFAULT_GALLERY_COLUMNS,
): number {
  if (!Number.isFinite(containerWidth) || containerWidth <= 0) {
    return fallbackColumns;
  }
  const rawColumns = Math.floor(containerWidth / GALLERY_CARD_TARGET_WIDTH_PX);
  return Math.max(MIN_GALLERY_COLUMNS, Math.min(MAX_GALLERY_COLUMNS, rawColumns));
}

/**
 * Measures a newly mounted scroll container and attaches a ResizeObserver until cleanup.
 */
export function bindGalleryContainerResize(
  containerElement: ResizableContainerElement | null,
  onColumnCountChange: (nextColumns: number) => void,
  createObserver: ResizeObserverFactory = defaultResizeObserverFactory,
): () => void {
  if (!containerElement) {
    return () => {};
  }

  let isDisposed = false;
  const syncColumnCount = () => {
    if (isDisposed) {
      return;
    }
    const measuredWidth = containerElement.clientWidth;
    if (Number.isFinite(measuredWidth) && measuredWidth > 0) {
      onColumnCountChange(computeGalleryColumnCount(measuredWidth));
    }
  };

  syncColumnCount();
  const observer = createObserver(syncColumnCount);
  observer.observe(containerElement);

  return () => {
    isDisposed = true;
    observer.disconnect();
  };
}
