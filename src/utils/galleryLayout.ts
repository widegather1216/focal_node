import {
  observeElementOffset,
  type Virtualizer,
} from '@tanstack/react-virtual';
import type { SearchFilters } from '../types/photo.ts';
import { sanitizeSearchFilters } from './searchFilters.ts';

export const DEFAULT_GALLERY_COLUMNS = 4;
export const MIN_GALLERY_COLUMNS = 2;
export const MAX_GALLERY_COLUMNS = 8;
export const GALLERY_CARD_TARGET_WIDTH_PX = 230;

export interface ScrollableContainerElement {
  scrollTop: number;
}

export interface VirtualizerScrollState {
  scrollOffset: number | null;
  scrollDirection: 'forward' | 'backward' | null;
  isScrolling: boolean;
}

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

/**
 * Serializes folder, effective query, and active filters into a deterministic key
 * so query context switches reset scroll position while pagination appends preserve it.
 */
export function buildGalleryQueryContextKey(
  selectedFolder: string | null,
  effectiveSearchQuery: string,
  searchFilters: SearchFilters | null | undefined,
): string {
  const normalizedFilters = sanitizeSearchFilters(searchFilters);
  const sortedFilterEntries = Object.keys(normalizedFilters)
    .sort()
    .map((filterKey) => [
      filterKey,
      normalizedFilters[filterKey as keyof SearchFilters],
    ]);

  return JSON.stringify([
    selectedFolder ?? null,
    effectiveSearchQuery ?? '',
    sortedFilterEntries,
  ]);
}

/**
 * Clears Virtualizer residual scrollOffset (which Virtualizer.cleanup() preserves)
 * and resets the DOM container scrollTop back to the top when provided.
 */
export function resetVirtualizerScrollPosition(
  virtualizer: VirtualizerScrollState | null,
  containerElement: ScrollableContainerElement | null,
): void {
  if (virtualizer) {
    virtualizer.scrollOffset = 0;
    virtualizer.scrollDirection = null;
    virtualizer.isScrolling = false;
  }
  if (containerElement && containerElement.scrollTop !== 0) {
    containerElement.scrollTop = 0;
  }
}

/**
 * Prevents Virtualizer._willUpdate() from scrolling a freshly mounted container
 * (or an unmounted container awaiting remount) back to a stale scrollOffset.
 */
export function syncVirtualizerOnContainerMount(
  virtualizer: VirtualizerScrollState | null,
  containerElement: ScrollableContainerElement | null,
): void {
  if (!containerElement) {
    resetVirtualizerScrollPosition(virtualizer, null);
    return;
  }
  if (
    containerElement.scrollTop === 0 &&
    virtualizer &&
    virtualizer.scrollOffset !== 0
  ) {
    resetVirtualizerScrollPosition(virtualizer, null);
  }
}

export type OffsetObserverCallback = (
  offset: number,
  isScrolling: boolean,
) => void;

export type ElementOffsetObserver<
  TScrollElement extends Element = Element,
  TItemElement extends Element = Element,
> = (
  instance: Virtualizer<TScrollElement, TItemElement>,
  onOffsetChange: OffsetObserverCallback,
) => void | (() => void);

/**
 * Wraps @tanstack/virtual-core's observeElementOffset so any pending 150ms
 * debounce fallback timer cannot resurrect a stale scrollOffset after cleanup.
 */
export function createSafeObserveElementOffset<
  TScrollElement extends Element = Element,
  TItemElement extends Element = Element,
>(
  baseObserver: ElementOffsetObserver<
    TScrollElement,
    TItemElement
  > = observeElementOffset as ElementOffsetObserver<
    TScrollElement,
    TItemElement
  >,
): ElementOffsetObserver<TScrollElement, TItemElement> {
  return (instance, onOffsetChange) => {
    let isDisposed = false;
    const baseCleanup = baseObserver(instance, (offset, isScrolling) => {
      if (isDisposed) return;
      onOffsetChange(offset, isScrolling);
    });
    if (typeof baseCleanup !== 'function') {
      isDisposed = true;
      return undefined;
    }
    return () => {
      if (isDisposed) return;
      isDisposed = true;
      baseCleanup();
    };
  };
}

/**
 * Gallery offset observer preserving RTL/horizontal/scrollend behavior while
 * blocking stale 150ms fallback timer callbacks after container cleanup.
 */
export function observeGalleryElementOffset<
  TScrollElement extends Element,
  TItemElement extends Element = Element,
>(
  instance: Virtualizer<TScrollElement, TItemElement>,
  onOffsetChange: OffsetObserverCallback,
): void | (() => void) {
  return createSafeObserveElementOffset<TScrollElement, TItemElement>()(
    instance,
    onOffsetChange,
  );
}
