export type ExportStatus = 'success' | 'partial' | 'failed';
export type ExportOutcomeKind = 'success' | 'partial' | 'error';

export interface ExportResult {
  status: ExportStatus;
  exported_count: number;
  failed_count: number;
  total_count: number;
  exported_ids: string[];
  failed_ids: string[];
  errors: string[] | null;
}

export interface ExportFeedback {
  kind: ExportOutcomeKind;
  message: string;
  detail?: string;
}

export interface SseByteStream {
  getReader(): {
    read(): Promise<{ value?: Uint8Array; done: boolean }>;
    releaseLock(): void;
    cancel(reason?: unknown): Promise<unknown>;
  };
}

interface SseParserState {
  buffer: string;
  eventType: string;
  dataLines: string[];
  finalResult: ExportResult | null;
  streamError: string | null;
}

function isPlainRecord(candidate: unknown): candidate is Record<string, unknown> {
  return typeof candidate === 'object' && candidate !== null && !Array.isArray(candidate);
}

function parseStringArray(rawValue: unknown): string[] {
  if (!Array.isArray(rawValue)) return [];
  return rawValue.filter((entry): entry is string => typeof entry === 'string' && entry.length > 0);
}

function toNonNegativeInt(rawValue: unknown, fallback: number): number {
  if (typeof rawValue !== 'number' || !Number.isFinite(rawValue)) {
    return fallback;
  }
  return Math.max(0, Math.trunc(rawValue));
}

export function extractSseErrorMessage(rawPayload: string): string {
  const trimmedPayload = rawPayload.trim();
  if (!trimmedPayload) {
    return '내보내기 스트림 오류가 발생했습니다.';
  }

  try {
    const parsedPayload: unknown = JSON.parse(trimmedPayload);
    if (typeof parsedPayload === 'string' && parsedPayload.trim()) {
      return parsedPayload.trim();
    }
    if (isPlainRecord(parsedPayload)) {
      const candidateMessage = parsedPayload.detail ?? parsedPayload.message ?? parsedPayload.error;
      if (typeof candidateMessage === 'string' && candidateMessage.trim()) {
        return candidateMessage.trim();
      }
    }
  } catch {
    // SSE error frames may carry plain-text diagnostics rather than JSON.
  }

  return trimmedPayload;
}

export function normalizeExportResult(rawPayload: string): ExportResult {
  let parsedPayload: unknown;
  try {
    parsedPayload = JSON.parse(rawPayload);
  } catch {
    throw new Error('잘못된 내보내기 응답 형식입니다.');
  }

  if (!isPlainRecord(parsedPayload)) {
    throw new Error('잘못된 내보내기 응답 형식입니다.');
  }

  const errorsList = parseStringArray(parsedPayload.errors);
  const exportedIds = parseStringArray(parsedPayload.exported_ids);
  const failedIds = parseStringArray(parsedPayload.failed_ids);
  const exportedCount = toNonNegativeInt(parsedPayload.exported_count, 0);
  const failedCount = toNonNegativeInt(
    parsedPayload.failed_count,
    Math.max(errorsList.length, failedIds.length),
  );
  const totalCount = toNonNegativeInt(parsedPayload.total_count, exportedCount + failedCount);

  let normalizedStatus: ExportStatus;
  if (parsedPayload.status === 'failed' || exportedCount === 0) {
    normalizedStatus = 'failed';
  } else if (parsedPayload.status === 'partial' || failedCount > 0 || errorsList.length > 0) {
    normalizedStatus = 'partial';
  } else {
    normalizedStatus = 'success';
  }

  return {
    status: normalizedStatus,
    exported_count: exportedCount,
    failed_count: failedCount,
    total_count: totalCount,
    exported_ids: exportedIds,
    failed_ids: failedIds,
    errors: errorsList.length > 0 ? errorsList : null,
  };
}

function consumeCompleteLines(state: SseParserState, isFinalFlush: boolean): string[] {
  const lines: string[] = [];
  let lineStart = 0;
  let cursor = 0;

  while (cursor < state.buffer.length) {
    const currentChar = state.buffer[cursor];
    if (currentChar === '\r') {
      // Hold back a trailing CR because LF may arrive at the start of the next chunk.
      if (!isFinalFlush && cursor + 1 === state.buffer.length) {
        break;
      }
      lines.push(state.buffer.slice(lineStart, cursor));
      cursor += state.buffer[cursor + 1] === '\n' ? 2 : 1;
      lineStart = cursor;
      continue;
    }
    if (currentChar === '\n') {
      lines.push(state.buffer.slice(lineStart, cursor));
      cursor += 1;
      lineStart = cursor;
      continue;
    }
    cursor += 1;
  }

  state.buffer = state.buffer.slice(lineStart);
  if (isFinalFlush && state.buffer.length > 0) {
    lines.push(state.buffer);
    state.buffer = '';
  }
  return lines;
}

function dispatchSseEvent(state: SseParserState): void {
  const eventName = state.eventType || 'message';
  const payloadText = state.dataLines.join('\n');
  state.eventType = 'message';
  state.dataLines = [];

  if (eventName === 'error') {
    state.streamError = extractSseErrorMessage(payloadText);
    return;
  }
  if (!payloadText) {
    return;
  }
  if (eventName === 'done') {
    state.finalResult = normalizeExportResult(payloadText);
  }
}

function processSseLine(state: SseParserState, sseLine: string): void {
  if (sseLine === '') {
    dispatchSseEvent(state);
    return;
  }
  if (sseLine.startsWith(':')) {
    return;
  }

  const colonIndex = sseLine.indexOf(':');
  const fieldName = colonIndex === -1 ? sseLine : sseLine.slice(0, colonIndex);
  const rawFieldValue = colonIndex === -1 ? '' : sseLine.slice(colonIndex + 1);
  const fieldValue = rawFieldValue.startsWith(' ') ? rawFieldValue.slice(1) : rawFieldValue;

  if (fieldName === 'event') {
    state.eventType = fieldValue;
  } else if (fieldName === 'data') {
    state.dataLines.push(fieldValue);
  }
}

function processChunkLines(state: SseParserState, isFinalFlush: boolean): void {
  const completeLines = consumeCompleteLines(state, isFinalFlush);
  for (let lineIdx = 0; lineIdx < completeLines.length; lineIdx += 1) {
    processSseLine(state, completeLines[lineIdx]);
    if (state.streamError || state.finalResult) {
      return;
    }
  }
  if (isFinalFlush && (state.dataLines.length > 0 || state.eventType === 'error')) {
    dispatchSseEvent(state);
  }
}

export async function parseExportSseStream(stream: SseByteStream): Promise<ExportResult> {
  const reader = stream.getReader();
  const decoder = new TextDecoder('utf-8');
  const parserState: SseParserState = {
    buffer: '',
    eventType: 'message',
    dataLines: [],
    finalResult: null,
    streamError: null,
  };
  let streamCompleted = false;

  try {
    while (true) {
      const chunkResult = await reader.read();
      if (chunkResult.done) {
        streamCompleted = true;
        parserState.buffer += decoder.decode();
        processChunkLines(parserState, true);
        break;
      }
      if (chunkResult.value) {
        parserState.buffer += decoder.decode(chunkResult.value, { stream: true });
        processChunkLines(parserState, false);
        if (parserState.streamError || parserState.finalResult) {
          break;
        }
      }
    }
  } finally {
    if (!streamCompleted) {
      try {
        await reader.cancel();
      } catch (cancelErr) {
        console.warn('SSE reader cancel ignored:', cancelErr);
      }
    }
    reader.releaseLock();
  }

  if (parserState.streamError) {
    throw new Error(parserState.streamError);
  }
  if (!parserState.finalResult) {
    throw new Error('Export stream ended without final data');
  }
  return parserState.finalResult;
}

export function evaluateExportOutcome(exportResult: ExportResult, requestedCount: number): ExportFeedback {
  const exportedCount = Math.max(0, exportResult.exported_count);
  const errorList = (exportResult.errors ?? []).filter((msg) => msg.trim().length > 0);
  const expectedCount = Math.max(requestedCount, exportResult.total_count);
  const missingCount = Math.max(0, expectedCount - exportedCount);
  const failedCount = Math.max(exportResult.failed_count, errorList.length, missingCount);

  if (exportResult.status === 'failed' || exportedCount === 0) {
    const firstReason = errorList[0] ?? '파일을 내보내지 못했습니다.';
    return {
      kind: 'error',
      message: `내보내기 실패: ${firstReason}`,
      detail: errorList.length > 0 ? errorList.join('\n') : undefined,
    };
  }

  if (exportResult.status === 'partial' || failedCount > 0 || errorList.length > 0) {
    return {
      kind: 'partial',
      message: `${exportedCount}장 내보내기 완료 (${failedCount}장 실패)`,
      detail: errorList.length > 0 ? errorList.join('\n') : undefined,
    };
  }

  return {
    kind: 'success',
    message: `${exportedCount}장의 사진 내보내기 완료`,
  };
}

export function isAbortError(caughtErr: unknown): boolean {
  return caughtErr instanceof Error && caughtErr.name === 'AbortError';
}
