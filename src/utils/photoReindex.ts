import type { PhotoDetail } from '../types/photo';

export interface ReindexQueryClient {
  cancelQueries: (filters: { queryKey: readonly unknown[] }) => Promise<void>;
  setQueryData: (queryKey: readonly unknown[], data: PhotoDetail) => unknown;
  invalidateQueries: (filters: { queryKey: readonly unknown[] }) => Promise<void> | void;
}

export interface ReindexExecutorDeps {
  targetId: string | null;
  inFlightIds: Set<string>;
  requestSeqByPhoto: Map<string, number>;
  reindexPhoto: (photoId: string) => Promise<PhotoDetail>;
  queryClient: ReindexQueryClient;
  getSelectedPhotoId: () => string | null;
  isMounted: () => boolean;
  onStart: (targetId: string) => void;
  onSuccessActive: (updatedPhoto: PhotoDetail) => void;
  onError: (targetId: string, errorMessage: string) => void;
  onFinish: (targetId: string) => void;
}

const DEFAULT_REINDEX_ERROR_MESSAGE = '사진 재분석 도중 오류가 발생했습니다.';
const REINDEX_API_ERROR_PREFIX = 'Failed to reindex photo:';

export function addReindexingPhotoId(currentIds: ReadonlySet<string>, photoId: string): Set<string> {
  if (currentIds.has(photoId)) {
    return currentIds as Set<string>;
  }
  const nextIds = new Set(currentIds);
  nextIds.add(photoId);
  return nextIds;
}

export function removeReindexingPhotoId(currentIds: ReadonlySet<string>, photoId: string): Set<string> {
  if (!currentIds.has(photoId)) {
    return currentIds as Set<string>;
  }
  const nextIds = new Set(currentIds);
  nextIds.delete(photoId);
  return nextIds;
}

export function setPhotoReindexError(
  currentErrors: Readonly<Record<string, string>>,
  photoId: string,
  errorMessage: string,
): Record<string, string> {
  if (currentErrors[photoId] === errorMessage) {
    return currentErrors as Record<string, string>;
  }
  return { ...currentErrors, [photoId]: errorMessage };
}

export function clearPhotoReindexError(
  currentErrors: Readonly<Record<string, string>>,
  photoId: string,
): Record<string, string> {
  if (!Object.prototype.hasOwnProperty.call(currentErrors, photoId)) {
    return currentErrors as Record<string, string>;
  }
  const nextErrors: Record<string, string> = { ...currentErrors };
  delete nextErrors[photoId];
  return nextErrors;
}

export function formatReindexErrorMessage(caughtError: unknown): string {
  if (!(caughtError instanceof Error)) {
    return DEFAULT_REINDEX_ERROR_MESSAGE;
  }
  const trimmedMessage = caughtError.message.trim();
  if (!trimmedMessage) {
    return DEFAULT_REINDEX_ERROR_MESSAGE;
  }
  if (trimmedMessage.startsWith(REINDEX_API_ERROR_PREFIX)) {
    const detail = trimmedMessage.slice(REINDEX_API_ERROR_PREFIX.length).trim();
    return detail ? `재분석 실패: ${detail}` : DEFAULT_REINDEX_ERROR_MESSAGE;
  }
  return trimmedMessage.startsWith('재분석 실패') ? trimmedMessage : `재분석 실패: ${trimmedMessage}`;
}

export function shouldSyncPhotoEditFields(
  photoId: string,
  lastSyncedPhotoId: string | null,
  isEditing: boolean,
): boolean {
  return lastSyncedPhotoId !== photoId || !isEditing;
}

async function applyReindexSuccess(
  deps: ReindexExecutorDeps,
  targetId: string,
  requestSequence: number,
  updatedPhoto: PhotoDetail,
): Promise<void> {
  if (deps.requestSeqByPhoto.get(targetId) !== requestSequence) {
    return;
  }
  // Cancel in-flight photoDetail GETs so stale responses cannot overwrite the fresh reindex payload.
  await deps.queryClient.cancelQueries({ queryKey: ['photoDetail', targetId] });
  if (deps.requestSeqByPhoto.get(targetId) !== requestSequence) {
    return;
  }
  deps.queryClient.setQueryData(['photoDetail', targetId], updatedPhoto);
  await Promise.all([
    Promise.resolve(deps.queryClient.invalidateQueries({ queryKey: ['photos'] })),
    Promise.resolve(deps.queryClient.invalidateQueries({ queryKey: ['analyticsStats'] })),
    Promise.resolve(deps.queryClient.invalidateQueries({ queryKey: ['critiques'] })),
  ]);
  if (deps.isMounted() && deps.getSelectedPhotoId() === targetId) {
    deps.onSuccessActive(updatedPhoto);
  }
}

export async function executePhotoReindex(deps: ReindexExecutorDeps): Promise<boolean> {
  const { targetId, inFlightIds, requestSeqByPhoto } = deps;
  if (!targetId || inFlightIds.has(targetId)) {
    return false;
  }

  const requestSequence = (requestSeqByPhoto.get(targetId) ?? 0) + 1;
  requestSeqByPhoto.set(targetId, requestSequence);
  inFlightIds.add(targetId);
  deps.onStart(targetId);

  try {
    const updatedPhoto = await deps.reindexPhoto(targetId);
    await applyReindexSuccess(deps, targetId, requestSequence, updatedPhoto);
    return true;
  } catch (caughtError: unknown) {
    console.error('Failed to reindex photo:', caughtError);
    if (deps.isMounted()) {
      deps.onError(targetId, formatReindexErrorMessage(caughtError));
    }
    return false;
  } finally {
    if (requestSeqByPhoto.get(targetId) === requestSequence) {
      inFlightIds.delete(targetId);
    }
    if (deps.isMounted()) {
      deps.onFinish(targetId);
    }
  }
}
