import { PhotoDetail } from '../hooks/usePhotoDetail';

export interface CritiqueScores {
  overall: number | null;
  iaa: number | null;
  iqa: number | null;
  ista: number | null;
}

const PRINT_REPORT_CSS = `
  .focal-pdf-report-container {
    box-sizing: border-box;
    width: 794px;
    background-color: #ffffff !important;
    color: #1f2937 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Apple SD Gothic Neo", "Malgun Gothic", "Pretendard", sans-serif;
    padding: 36px 40px;
    line-height: 1.6;
    font-size: 13px;
    --accent-focal: #e11d48;
    --accent-focal-hover: #be123c;
    --accent-focal-deep: #9f1239;
    --text-primary: #111827;
    --text-secondary: #4b5563;
    --text-muted: #6b7280;
    --border-subtle: #e5e7eb;
  }
  .focal-pdf-report-container * { box-sizing: border-box; }
  .focal-pdf-report-container .report-container { width: 100%; margin: 0 auto; }
  .focal-pdf-report-container .header {
    border-bottom: 2px solid #e11d48;
    padding-bottom: 12px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }
  .focal-pdf-report-container .title {
    font-size: 22px;
    font-weight: 800;
    color: #111827;
    margin: 0 0 4px 0;
    letter-spacing: -0.02em;
  }
  .focal-pdf-report-container .subtitle {
    font-size: 11px;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
  }
  .focal-pdf-report-container .date { font-size: 11px; color: #6b7280; }
  .focal-pdf-report-container .photo-card {
    margin-bottom: 24px;
    text-align: center;
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 16px;
  }
  .focal-pdf-report-container .photo-card img {
    max-width: 100%;
    max-height: 480px;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    object-fit: contain;
  }
  .focal-pdf-report-container .exif-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    background: #f3f4f6;
    padding: 14px 16px;
    border-radius: 8px;
    margin-bottom: 24px;
    border: 1px solid #e5e7eb;
  }
  .focal-pdf-report-container .exif-item { display: flex; flex-direction: column; }
  .focal-pdf-report-container .exif-label {
    font-size: 10px;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
    margin-bottom: 2px;
  }
  .focal-pdf-report-container .exif-value { font-size: 12px; font-weight: 600; color: #111827; }
  .focal-pdf-report-container .scores-summary {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }
  .focal-pdf-report-container .score-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
  }
  .focal-pdf-report-container .score-card.primary { background: #fff1f2; border-color: #fecdd3; }
  .focal-pdf-report-container .score-label {
    font-size: 10px;
    color: #6b7280;
    text-transform: uppercase;
    margin-bottom: 4px;
    font-weight: 600;
  }
  .focal-pdf-report-container .score-card.primary .score-label { color: #be123c; }
  .focal-pdf-report-container .score-val { font-size: 20px; font-weight: 800; color: #111827; }
  .focal-pdf-report-container .score-card.primary .score-val { color: #e11d48; }
  .focal-pdf-report-container .critique-body { font-size: 13.5px; line-height: 1.7; color: #374151 !important; }
  .focal-pdf-report-container .critique-body button,
  .focal-pdf-report-container .critique-body div:has(> button:only-child) { display: none !important; }
  .focal-pdf-report-container .critique-body h1,
  .focal-pdf-report-container .critique-body h2,
  .focal-pdf-report-container .critique-body h3,
  .focal-pdf-report-container .critique-body h4,
  .focal-pdf-report-container .critique-body strong,
  .focal-pdf-report-container .critique-body th { color: #111827 !important; }
  .focal-pdf-report-container .critique-body h1,
  .focal-pdf-report-container .critique-body h2,
  .focal-pdf-report-container .critique-body h3 {
    margin-top: 20px;
    margin-bottom: 8px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  .focal-pdf-report-container .critique-body section h3 { margin-top: 0; margin-bottom: 0; }
  .focal-pdf-report-container .critique-body h2 { border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }
  .focal-pdf-report-container .critique-body p,
  .focal-pdf-report-container .critique-body li,
  .focal-pdf-report-container .critique-body td,
  .focal-pdf-report-container .critique-body em,
  .focal-pdf-report-container .critique-body blockquote,
  .focal-pdf-report-container .critique-body div,
  .focal-pdf-report-container .critique-body span:not(.font-mono) { color: #374151 !important; }
  .focal-pdf-report-container .critique-body section,
  .focal-pdf-report-container .critique-body tr,
  .focal-pdf-report-container .critique-body th,
  .focal-pdf-report-container .critique-body td { border-color: #e5e7eb !important; }
  .focal-pdf-report-container .critique-body code { background: #f3f4f6 !important; color: #be123c !important; }
  .focal-pdf-report-container .critique-body pre { color: #111827 !important; }
  .focal-pdf-report-container .critique-body p { margin: 0 0 12px 0; }
  .focal-pdf-report-container .critique-body blockquote {
    margin: 12px 0;
    padding: 8px 16px;
    background: #fdf2f4 !important;
    border-left: 3px solid #e11d48 !important;
    font-style: italic;
    color: #4b5563 !important;
    border-radius: 0 6px 6px 0;
  }
  .focal-pdf-report-container .critique-body ul,
  .focal-pdf-report-container .critique-body ol { margin: 0 0 12px 0; padding-left: 20px; }
  .focal-pdf-report-container .critique-body li { margin-bottom: 4px; }
  .focal-pdf-report-container .report-footer {
    margin-top: 36px;
    padding-top: 14px;
    border-top: 1px solid #e5e7eb;
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: #9ca3af;
  }
`;

/**
 * Escapes HTML special characters to prevent DOM XSS when interpolating metadata into print templates.
 */
export function escapeHtml(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function buildScoreCardHtml(label: string, value: number | null, suffix = '', isPrimary = false): string {
  if (value === null) return '';
  const cardClass = isPrimary ? 'score-card primary' : 'score-card';
  return `<div class="${cardClass}"><div class="score-label">${label}</div><div class="score-val">${escapeHtml(value)}${suffix}</div></div>`;
}

function buildScoresSummaryHtml(scores?: CritiqueScores | null): string {
  if (!scores) return '';
  const cards = [
    buildScoreCardHtml('종합 지각 평점', scores.overall, ' / 100', true),
    buildScoreCardHtml('IAA (미학 &amp; 구도)', scores.iaa),
    buildScoreCardHtml('IQA (화질 &amp; 광학)', scores.iqa),
    buildScoreCardHtml('ISTA (구조 &amp; 질감)', scores.ista),
  ].join('');
  return `<div class="scores-summary">${cards}</div>`;
}

/**
 * Builds a clean, professional A4 print HTML document with photo, EXIF, scores, and critique.
 */
export function generatePrintHtml(
  photo: PhotoDetail | null | undefined,
  critiqueContentHtml: string,
  imageUrl: string,
  formattedDate: string | null,
  scores?: CritiqueScores | null
): string {
  const meta = photo?.metadata;
  const focalAperture = [
    meta?.focal_length ? `${meta.focal_length}mm` : null,
    meta?.f_number ? `f/${meta.f_number}` : null,
  ].filter(Boolean).join(' · ') || '정보 없음';
  const exposureIso = [
    meta?.shutter_speed ? `${meta.shutter_speed}s` : null,
    meta?.iso ? `ISO ${meta.iso}` : null,
  ].filter(Boolean).join(' · ') || '정보 없음';

  return `
  <div class="focal-pdf-report-container">
    <style>${PRINT_REPORT_CSS}</style>
    <div class="report-container">
      <div class="header">
        <div>
          <div class="subtitle">AI Photo Critique & Aesthetic Analysis Report</div>
          <h1 class="title">${escapeHtml(photo?.file_name || '사진 비평 리포트')}</h1>
        </div>
        ${formattedDate ? `<div class="date">${escapeHtml(formattedDate)}</div>` : ''}
      </div>
      <div class="photo-card">
        <img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(photo?.file_name || '사진')}" />
      </div>
      <div class="exif-grid">
        <div class="exif-item"><span class="exif-label">Camera</span><span class="exif-value">${escapeHtml(meta?.camera_model || '정보 없음')}</span></div>
        <div class="exif-item"><span class="exif-label">Lens</span><span class="exif-value">${escapeHtml(meta?.lens_model || '정보 없음')}</span></div>
        <div class="exif-item"><span class="exif-label">Focal & Aperture</span><span class="exif-value">${escapeHtml(focalAperture)}</span></div>
        <div class="exif-item"><span class="exif-label">Exposure & ISO</span><span class="exif-value">${escapeHtml(exposureIso)}</span></div>
      </div>
      ${buildScoresSummaryHtml(scores)}
      <div class="critique-body">${critiqueContentHtml}</div>
      <div class="report-footer">
        <span>On-device AI Local Photo Search & Aesthetic Curator</span>
        <span>Focal Node</span>
      </div>
    </div>
  </div>`;
}

/**
 * Builds the markdown document string for exporting a photo critique.
 */
export function buildMarkdownReport(
  photo: PhotoDetail | null | undefined,
  critiqueText: string,
  formattedDate: string | null,
  scores?: CritiqueScores | null
): string {
  const meta = photo?.metadata;
  const exposureParts = [
    meta?.focal_length ? `${meta.focal_length}mm` : null,
    meta?.f_number ? `f/${meta.f_number}` : null,
    meta?.shutter_speed ? `${meta.shutter_speed}s` : null,
    meta?.iso ? `ISO ${meta.iso}` : null,
  ].filter(Boolean).join(' | ');

  const subScoreParts = scores ? [
    scores.iaa !== null ? `IAA(미학/구도) ${scores.iaa}` : null,
    scores.iqa !== null ? `IQA(화질/광학) ${scores.iqa}` : null,
    scores.ista !== null ? `ISTA(구조/질감) ${scores.ista}` : null,
  ].filter(Boolean).join('  ·  ') : '';

  const scoreLines = scores ? [
    scores.overall !== null ? `> **종합 평가 점수:** ${scores.overall} / 100  ` : null,
    subScoreParts ? `> **세부 평가 지수:** ${subScoreParts}  ` : null,
  ].filter(Boolean) as string[] : [];

  const englishSection = photo?.ai_analysis?.critique_en
    ? ['', '---', '', '### UniPercept 8B VQA Original Feedback (English)', '', photo.ai_analysis.critique_en]
    : [];

  return [
    `# ${photo?.file_name || '사진'}`,
    '',
    '> **Focal Node · AI Photo Critique Report**  ',
    formattedDate ? `> **분석 일시:** ${formattedDate}  ` : '',
    meta?.camera_model ? `> **카메라:** ${meta.camera_model}  ` : '',
    meta?.lens_model ? `> **렌즈:** ${meta.lens_model}  ` : '',
    exposureParts ? `> **노출 설정:** ${exposureParts}  ` : '',
    photo?.ai_analysis?.caption ? `> **캡션:** *"${photo.ai_analysis.caption}"*  ` : '',
    ...scoreLines,
    '',
    '---',
    '',
    critiqueText,
    ...englishSection,
  ].filter((line) => line !== null).join('\n');
}
