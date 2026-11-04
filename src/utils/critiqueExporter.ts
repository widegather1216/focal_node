import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import { PhotoDetail } from '../hooks/usePhotoDetail';

export interface CritiqueScores {
  overall: number | null;
  iaa: number | null;
  iqa: number | null;
  ista: number | null;
}

export interface ExportProgressState {
  active: boolean;
  type: 'pdf' | 'md';
  title: string;
  step: string;
  detail: string;
  percent: number;
  savedPath?: string | null;
}

/**
 * Fetches an image URL and converts it to a Base64 data URL for safe offline canvas rendering.
 */
export async function fetchImageAsDataUrl(url: string): Promise<string> {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const blob = await response.blob();
    return await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        if (typeof reader.result === 'string') {
          resolve(reader.result);
        } else {
          reject(new Error('FileReader result is not a string'));
        }
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  } catch (err) {
    console.warn('Failed to fetch image as data URL, fallback to raw url:', err);
    return url;
  }
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
  return `
  <div class="focal-pdf-report-container">
    <style>
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
      .focal-pdf-report-container * {
        box-sizing: border-box;
      }
      .focal-pdf-report-container .report-container {
        width: 100%;
        margin: 0 auto;
      }
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
      .focal-pdf-report-container .date {
        font-size: 11px;
        color: #6b7280;
      }
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
      .focal-pdf-report-container .exif-item {
        display: flex;
        flex-direction: column;
      }
      .focal-pdf-report-container .exif-label {
        font-size: 10px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        margin-bottom: 2px;
      }
      .focal-pdf-report-container .exif-value {
        font-size: 12px;
        font-weight: 600;
        color: #111827;
      }
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
      .focal-pdf-report-container .score-card.primary {
        background: #fff1f2;
        border-color: #fecdd3;
      }
      .focal-pdf-report-container .score-label {
        font-size: 10px;
        color: #6b7280;
        text-transform: uppercase;
        margin-bottom: 4px;
        font-weight: 600;
      }
      .focal-pdf-report-container .score-card.primary .score-label {
        color: #be123c;
      }
      .focal-pdf-report-container .score-val {
        font-size: 20px;
        font-weight: 800;
        color: #111827;
      }
      .focal-pdf-report-container .score-card.primary .score-val {
        color: #e11d48;
      }
      .focal-pdf-report-container .critique-body {
        font-size: 13.5px;
        line-height: 1.7;
        color: #374151;
      }
      .focal-pdf-report-container .critique-body h1,
      .focal-pdf-report-container .critique-body h2,
      .focal-pdf-report-container .critique-body h3 {
        color: #111827;
        margin-top: 20px;
        margin-bottom: 8px;
        font-weight: 700;
        letter-spacing: -0.01em;
      }
      .focal-pdf-report-container .critique-body h2 {
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 6px;
      }
      .focal-pdf-report-container .critique-body p {
        margin: 0 0 12px 0;
      }
      .focal-pdf-report-container .critique-body blockquote {
        margin: 12px 0;
        padding: 8px 16px;
        background: #fdf2f4;
        border-left: 3px solid #e11d48;
        font-style: italic;
        color: #4b5563;
        border-radius: 0 6px 6px 0;
      }
      .focal-pdf-report-container .critique-body ul,
      .focal-pdf-report-container .critique-body ol {
        margin: 0 0 12px 0;
        padding-left: 20px;
      }
      .focal-pdf-report-container .critique-body li {
        margin-bottom: 4px;
      }
      .focal-pdf-report-container .report-footer {
        margin-top: 36px;
        padding-top: 14px;
        border-top: 1px solid #e5e7eb;
        display: flex;
        justify-content: space-between;
        font-size: 10px;
        color: #9ca3af;
      }
    </style>

    <div class="report-container">
      <div class="header">
        <div>
          <div class="subtitle">AI Photo Critique & Aesthetic Analysis Report</div>
          <h1 class="title">${photo?.file_name || '사진 비평 리포트'}</h1>
        </div>
        ${formattedDate ? `<div class="date">${formattedDate}</div>` : ''}
      </div>

      <div class="photo-card">
        <img src="${imageUrl}" alt="${photo?.file_name || '사진'}" />
      </div>

      <div class="exif-grid">
        <div class="exif-item">
          <span class="exif-label">Camera</span>
          <span class="exif-value">${meta?.camera_model || '정보 없음'}</span>
        </div>
        <div class="exif-item">
          <span class="exif-label">Lens</span>
          <span class="exif-value">${meta?.lens_model || '정보 없음'}</span>
        </div>
        <div class="exif-item">
          <span class="exif-label">Focal & Aperture</span>
          <span class="exif-value">${[meta?.focal_length ? `${meta.focal_length}mm` : null, meta?.f_number ? `f/${meta.f_number}` : null].filter(Boolean).join(' · ') || '정보 없음'}</span>
        </div>
        <div class="exif-item">
          <span class="exif-label">Exposure & ISO</span>
          <span class="exif-value">${[meta?.shutter_speed ? `${meta.shutter_speed}s` : null, meta?.iso ? `ISO ${meta.iso}` : null].filter(Boolean).join(' · ') || '정보 없음'}</span>
        </div>
      </div>

      ${scores ? `
      <div class="scores-summary">
        ${scores.overall !== null ? `
        <div class="score-card primary">
          <div class="score-label">종합 지각 평점</div>
          <div class="score-val">${scores.overall} / 100</div>
        </div>` : ''}
        ${scores.iaa !== null ? `
        <div class="score-card">
          <div class="score-label">IAA (미학 & 구도)</div>
          <div class="score-val">${scores.iaa}</div>
        </div>` : ''}
        ${scores.iqa !== null ? `
        <div class="score-card">
          <div class="score-label">IQA (화질 & 광학)</div>
          <div class="score-val">${scores.iqa}</div>
        </div>` : ''}
        ${scores.ista !== null ? `
        <div class="score-card">
          <div class="score-label">ISTA (구조 & 질감)</div>
          <div class="score-val">${scores.ista}</div>
        </div>` : ''}
      </div>` : ''}

      <div class="critique-body">
        ${critiqueContentHtml}
      </div>

      <div class="report-footer">
        <span>On-device AI Local Photo Search & Aesthetic Curator</span>
        <span>Focal Node</span>
      </div>
    </div>
  </div>`;
}

/**
 * Builds and downloads or saves a markdown critique report.
 */
export async function exportCritiqueToMarkdown(
  photo: PhotoDetail | null | undefined,
  critiqueText: string,
  formattedDate: string | null,
  scores?: CritiqueScores | null
): Promise<{ success: boolean; savedPath: string | null; cancelled?: boolean }> {
  const meta = photo?.metadata;
  const baseName = photo?.file_name ? photo.file_name.replace(/\.[^/.]+$/, '') : 'photo';
  const defaultFileName = `${baseName}_AI비평.md`;

  const exposureParts = [
    meta?.focal_length ? `${meta.focal_length}mm` : null,
    meta?.f_number ? `f/${meta.f_number}` : null,
    meta?.shutter_speed ? `${meta.shutter_speed}s` : null,
    meta?.iso ? `ISO ${meta.iso}` : null
  ].filter(Boolean).join(' | ');

  const scoreLines = scores ? [
    scores.overall !== null ? `> **종합 평가 점수:** ${scores.overall} / 100  ` : null,
    (scores.iaa !== null || scores.iqa !== null || scores.ista !== null)
      ? `> **세부 평가 지수:** ${[
          scores.iaa !== null ? `IAA(미학/구도) ${scores.iaa}` : null,
          scores.iqa !== null ? `IQA(화질/광학) ${scores.iqa}` : null,
          scores.ista !== null ? `ISTA(구조/질감) ${scores.ista}` : null
        ].filter(Boolean).join('  ·  ')}  `
      : null
  ].filter(Boolean) as string[] : [];

  const markdownDocument = [
    `# ${photo?.file_name || '사진'}`,
    ``,
    `> **Focal Node · AI Photo Critique Report**  `,
    formattedDate ? `> **분석 일시:** ${formattedDate}  ` : '',
    meta?.camera_model ? `> **카메라:** ${meta.camera_model}  ` : '',
    meta?.lens_model ? `> **렌즈:** ${meta.lens_model}  ` : '',
    exposureParts ? `> **노출 설정:** ${exposureParts}  ` : '',
    photo?.ai_analysis?.caption ? `> **캡션:** *"${photo.ai_analysis.caption}"*  ` : '',
    ...scoreLines,
    ``,
    `---`,
    ``,
    critiqueText
  ].filter(line => line !== null).join('\n');

  let selectedPath: string | null = null;
  try {
    const { save } = await import('@tauri-apps/plugin-dialog');
    selectedPath = await save({
      defaultPath: defaultFileName,
      filters: [{ name: 'Markdown 문서 (*.md)', extensions: ['md'] }]
    });
  } catch (dialogErr) {
    console.warn('Tauri dialog save is unavailable, will fallback to browser download:', dialogErr);
  }

  // 사용자가 파일 저장 창에서 "취소"를 누른 경우
  if (selectedPath === null && typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
    return { success: false, savedPath: null, cancelled: true };
  }

  const encoder = new TextEncoder();
  const uint8Array = encoder.encode(markdownDocument);

  if (selectedPath) {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('save_binary_file', {
      path: selectedPath,
      data: Array.from(uint8Array)
    });
    return { success: true, savedPath: selectedPath };
  } else {
    // 브라우저 fallback 다운로드
    const blob = new Blob([markdownDocument], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = defaultFileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    return { success: true, savedPath: null };
  }
}

/**
 * Builds and saves an A4 PDF critique report.
 */
export async function exportCritiqueToPdf(
  photo: PhotoDetail | null | undefined,
  critiqueText: string,
  imageUrl: string,
  thumbUrl: string,
  formattedDate: string | null,
  scores: CritiqueScores | null | undefined,
  onProgress: (state: ExportProgressState) => void
): Promise<{ success: boolean; savedPath: string | null; cancelled?: boolean }> {
  const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
  let container: HTMLDivElement | null = null;

  try {
    // 1) 사진 에셋 준비 (15%)
    onProgress({
      active: true,
      type: 'pdf',
      title: 'A4 비평 리포트 PDF 생성 중',
      step: '사진 및 그래픽 에셋 준비 중...',
      detail: '고해상도 인쇄를 위해 사진 이미지를 인라인으로 준비하고 있습니다.',
      percent: 15,
      savedPath: null
    });
    await delay(80);

    let embeddedImageUrl = await fetchImageAsDataUrl(imageUrl);
    if (!embeddedImageUrl.startsWith('data:') && imageUrl !== thumbUrl) {
      embeddedImageUrl = await fetchImageAsDataUrl(thumbUrl);
    }

    // 2) A4 리포트 레이아웃 구성 (35%)
    onProgress({
      active: true,
      type: 'pdf',
      title: 'A4 비평 리포트 PDF 생성 중',
      step: 'A4 리포트 레이아웃 렌더링 중...',
      detail: 'EXIF 메타데이터와 종합 평가 지수 그리드를 배치하고 있습니다.',
      percent: 35,
      savedPath: null
    });
    await delay(80);

    const paperElem = document.getElementById('critique-rendered-body');
    const contentHtml = paperElem ? paperElem.innerHTML : critiqueText;

    const printHtml = generatePrintHtml(
      photo,
      contentHtml,
      embeddedImageUrl,
      formattedDate,
      scores
    );

    container = document.createElement('div');
    container.id = 'pdf-render-temp-container';
    container.style.position = 'fixed';
    container.style.left = '0';
    container.style.top = '0';
    container.style.width = '794px'; // 210mm at 96 DPI
    container.style.backgroundColor = '#ffffff';
    container.style.color = '#1f2937';
    container.style.zIndex = '-9999';
    container.style.opacity = '1';
    container.style.pointerEvents = 'none';
    container.innerHTML = printHtml;
    document.body.appendChild(container);

    // 내부 이미지 로드 및 디코딩 완료 대기
    const imgElements = Array.from(container.querySelectorAll('img'));
    await Promise.all(
      imgElements.map(
        (img) =>
          new Promise<void>((resolve) => {
            if (img.complete && img.naturalWidth > 0) {
              if ('decode' in img) {
                img.decode().then(() => resolve()).catch(() => resolve());
              } else {
                resolve();
              }
            } else {
              img.onload = () => {
                if ('decode' in img) {
                  img.decode().then(() => resolve()).catch(() => resolve());
                } else {
                  resolve();
                }
              };
              img.onerror = () => resolve();
            }
          })
      )
    );

    // 브라우저 DOM 렌더링 파이프라인(Layout/Paint) 완료 대기
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => resolve());
      });
    });

    // 3) 초고해상도 캔버스 캡처 (65%)
    onProgress({
      active: true,
      type: 'pdf',
      title: 'A4 비평 리포트 PDF 생성 중',
      step: '초고해상도(Retina 2x) 벡터 캔버스 캡처 중...',
      detail: '텍스트와 이미지를 선명한 픽셀로 정밀 렌더링하고 있습니다.',
      percent: 65,
      savedPath: null
    });
    await delay(100);

    const canvas = await html2canvas(container, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#ffffff',
      logging: false,
      x: 0,
      y: 0,
      scrollX: 0,
      scrollY: 0,
      width: 794,
      windowWidth: 794
    });

    if (!canvas || canvas.width <= 0 || canvas.height <= 0) {
      throw new Error('Canvas capture resulted in invalid dimensions');
    }

    // 4) A4 페이지 슬라이스 및 PDF 조립 (85%)
    onProgress({
      active: true,
      type: 'pdf',
      title: 'A4 비평 리포트 PDF 생성 중',
      step: 'A4 페이지 슬라이스 및 PDF 조립 중...',
      detail: '인쇄 규격에 맞춰 페이지를 분할하고 최종 문서를 조립하고 있습니다.',
      percent: 85,
      savedPath: null
    });
    await delay(80);

    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4',
      compress: true
    });

    const pageWidthMm = 210;
    const pageHeightMm = 297;
    const pageHeightPx = Math.floor(canvas.width * (pageHeightMm / pageWidthMm));
    if (pageHeightPx <= 0) {
      throw new Error('Page height calculation resulted in 0');
    }

    let renderedHeight = 0;
    let pageIndex = 0;

    while (renderedHeight < canvas.height) {
      if (pageIndex > 0) {
        pdf.addPage();
      }

      const sliceHeightPx = Math.min(pageHeightPx, canvas.height - renderedHeight);
      const pageCanvas = document.createElement('canvas');
      pageCanvas.width = canvas.width;
      pageCanvas.height = pageHeightPx;

      const ctx = pageCanvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);
        ctx.drawImage(
          canvas,
          0,
          renderedHeight,
          canvas.width,
          sliceHeightPx,
          0,
          0,
          canvas.width,
          sliceHeightPx
        );
      }

      const pageDataUrl = pageCanvas.toDataURL('image/jpeg', 0.95);
      pdf.addImage(pageDataUrl, 'JPEG', 0, 0, pageWidthMm, pageHeightMm, undefined, 'FAST');

      renderedHeight += pageHeightPx;
      pageIndex++;
    }

    // 5) 파일 저장 경로 확인 (95%)
    onProgress({
      active: true,
      type: 'pdf',
      title: 'A4 비평 리포트 PDF 생성 중',
      step: '저장 경로 확인 및 파일 기록 중...',
      detail: '원하는 저장 위치와 파일명을 선택해 주세요.',
      percent: 95,
      savedPath: null
    });

    const baseName = photo?.file_name ? photo.file_name.replace(/\.[^/.]+$/, '') : 'photo';
    const defaultFileName = `${baseName}_AI비평_리포트.pdf`;

    let selectedPath: string | null = null;
    try {
      const { save } = await import('@tauri-apps/plugin-dialog');
      selectedPath = await save({
        defaultPath: defaultFileName,
        filters: [{ name: 'PDF 문서 (*.pdf)', extensions: ['pdf'] }]
      });
    } catch (dialogErr) {
      console.warn('Tauri dialog save is unavailable, will fallback to browser download:', dialogErr);
    }

    if (selectedPath === null && typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
      return { success: false, savedPath: null, cancelled: true };
    }

    const pdfArrayBuffer = pdf.output('arraybuffer');
    const uint8Array = new Uint8Array(pdfArrayBuffer);

    if (selectedPath) {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('save_binary_file', {
        path: selectedPath,
        data: Array.from(uint8Array)
      });
      return { success: true, savedPath: selectedPath };
    } else {
      pdf.save(defaultFileName);
      return { success: true, savedPath: null };
    }
  } finally {
    if (container && container.parentNode) {
      container.parentNode.removeChild(container);
    }
  }
}

/**
 * Reveals a saved file in OS file manager (Finder / File Explorer).
 */
export async function revealSavedFile(path: string): Promise<void> {
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('reveal_in_finder', { path });
  } catch (e) {
    console.warn('Failed to reveal file in finder:', e);
  }
}
