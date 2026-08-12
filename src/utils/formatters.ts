/**
 * Formatting utilities for dates, file sizes, score colors, and UI badges.
 */

export function formatBytes(bytes: number, decimals: number = 1): string {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

export function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '날짜 정보 없음';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateStr;
  }
}

export function getScoreColor(score: number): string {
  if (score >= 80) return '#10b981'; // Emerald Green
  if (score >= 60) return '#3b82f6'; // Bright Blue
  if (score >= 40) return '#f59e0b'; // Amber Yellow
  return '#ef4444'; // Red
}

export function getScoreBadgeStyle(score: number): React.CSSProperties {
  const color = getScoreColor(score);
  return {
    color,
    borderColor: `${color}40`,
    backgroundColor: `${color}15`,
    fontWeight: 600
  };
}
