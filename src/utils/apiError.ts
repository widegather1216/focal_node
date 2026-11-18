function formatValidationIssue(issue: unknown): string {
  if (typeof issue === 'string') {
    return issue.trim();
  }
  if (!issue || typeof issue !== 'object') {
    return '';
  }

  const issueRecord = issue as Record<string, unknown>;
  const messageText = typeof issueRecord.msg === 'string' ? issueRecord.msg.trim() : '';
  const locationPath = Array.isArray(issueRecord.loc)
    ? issueRecord.loc
        .filter((segment) => typeof segment === 'string' || typeof segment === 'number')
        .map((segment) => String(segment))
        .join('.')
    : '';

  if (locationPath && messageText) {
    return `${locationPath}: ${messageText}`;
  }
  return messageText || locationPath;
}

function formatObjectDetail(detailRecord: Record<string, unknown>): string | null {
  if (typeof detailRecord.msg === 'string' && detailRecord.msg.trim()) {
    return detailRecord.msg.trim();
  }
  if (typeof detailRecord.message === 'string' && detailRecord.message.trim()) {
    return detailRecord.message.trim();
  }
  try {
    const serialized = JSON.stringify(detailRecord);
    return serialized && serialized !== '{}' ? serialized : null;
  } catch (serializeError) {
    console.debug('Failed to serialize object error detail:', serializeError);
    return null;
  }
}

export function formatApiErrorDetail(detail: unknown): string | null {
  if (detail === null || detail === undefined) {
    return null;
  }
  if (typeof detail === 'string') {
    const trimmed = detail.trim();
    return trimmed || null;
  }
  if (Array.isArray(detail)) {
    const formattedIssues = detail
      .map(formatValidationIssue)
      .filter((formatted) => formatted.length > 0);
    return formattedIssues.length > 0 ? formattedIssues.join('; ') : null;
  }
  if (typeof detail === 'object') {
    return formatObjectDetail(detail as Record<string, unknown>);
  }
  return String(detail);
}

export async function extractResponseErrorMessage(
  response: Response,
  defaultMessage: string,
): Promise<string> {
  const fallbackMessage = response.statusText || defaultMessage;
  try {
    const errorBody = (await response.json()) as { detail?: unknown } | null;
    const formattedDetail = formatApiErrorDetail(errorBody?.detail);
    return formattedDetail ?? fallbackMessage;
  } catch (parseException) {
    if (parseException instanceof Error && parseException.name === 'AbortError') {
      throw parseException;
    }
    console.debug('Failed to parse error response as JSON:', parseException);
    return fallbackMessage;
  }
}
