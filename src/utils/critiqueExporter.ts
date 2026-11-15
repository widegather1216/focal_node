import html2canvas from 'html2canvas';
import { PhotoDetail } from '../hooks/usePhotoDetail';
import {
  CritiqueScores,
  escapeHtml,
  generatePrintHtml,
  buildMarkdownReport,
} from './critiquePrintTemplate';
import {
  fetchImageAsDataUrl,
  pickSaveFilePath,
  saveBinaryFileViaTauri,
  waitForContainerAssets,
  renderCanvasToPdf,
  revealSavedFile,
} from './critiqueExportHelpers';

export type { CritiqueScores };
export { escapeHtml, generatePrintHtml, fetchImageAsDataUrl, revealSavedFile };

export interface ExportProgressState {
  active: boolean;
  type: 'pdf' | 'md';
  title: string;
  step: string;
  detail: string;
  percent: number;
  savedPath?: string | null;
}

export interface ExportResult {
  success: boolean;
  savedPath: string | null;
  cancelled?: boolean;
}

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

function buildOffscreenRenderContainer(printHtml: string): HTMLDivElement {
  const container = document.createElement('div');
  container.id = 'pdf-render-scratch-container';
  container.style.position = 'fixed';
  container.style.left = '0';
  container.style.top = '0';
  container.style.width = '794px';
  container.style.backgroundColor = '#ffffff';
  container.style.color = '#1f2937';
  container.style.zIndex = '-9999';
  container.style.opacity = '1';
  container.style.pointerEvents = 'none';
  container.innerHTML = printHtml;
  document.body.appendChild(container);
  return container;
}

function triggerBrowserMarkdownDownload(markdownDocument: string, defaultFileName: string): void {
  const blob = new Blob([markdownDocument], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = defaultFileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Builds and downloads or saves a markdown critique report.
 */
export async function exportCritiqueToMarkdown(
  photo: PhotoDetail | null | undefined,
  critiqueText: string,
  formattedDate: string | null,
  scores?: CritiqueScores | null
): Promise<ExportResult> {
  const baseName = photo?.file_name ? photo.file_name.replace(/\.[^/.]+$/, '') : 'photo';
  const defaultFileName = `${baseName}_AI비평.md`;
  const markdownDocument = buildMarkdownReport(photo, critiqueText, formattedDate, scores);

  const selection = await pickSaveFilePath(defaultFileName, 'Markdown 문서 (*.md)', ['md']);
  if (selection.cancelled) {
    return { success: false, savedPath: null, cancelled: true };
  }

  if (selection.selectedPath) {
    const uint8Array = new TextEncoder().encode(markdownDocument);
    await saveBinaryFileViaTauri(selection.selectedPath, uint8Array);
    return { success: true, savedPath: selection.selectedPath };
  }

  triggerBrowserMarkdownDownload(markdownDocument, defaultFileName);
  return { success: true, savedPath: null };
}

function emitPdfProgress(
  onProgress: (state: ExportProgressState) => void,
  step: string,
  detail: string,
  percent: number
): void {
  onProgress({
    active: true,
    type: 'pdf',
    title: 'A4 비평 리포트 PDF 생성 중',
    step,
    detail,
    percent,
    savedPath: null,
  });
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
): Promise<ExportResult> {
  let container: HTMLDivElement | null = null;

  try {
    emitPdfProgress(
      onProgress,
      '사진 및 그래픽 에셋 준비 중...',
      '고해상도 인쇄를 위해 사진 이미지를 인라인으로 준비하고 있습니다.',
      15
    );
    await delay(80);

    let embeddedImageUrl = await fetchImageAsDataUrl(imageUrl);
    if (!embeddedImageUrl.startsWith('data:') && imageUrl !== thumbUrl) {
      embeddedImageUrl = await fetchImageAsDataUrl(thumbUrl);
    }

    emitPdfProgress(
      onProgress,
      'A4 리포트 레이아웃 렌더링 중...',
      'EXIF 메타데이터와 종합 평가 지수 그리드를 배치하고 있습니다.',
      35
    );
    await delay(80);

    const paperElem = document.getElementById('critique-rendered-body');
    const contentHtml = paperElem
      ? paperElem.innerHTML
      : `<p>${escapeHtml(critiqueText).replace(/\n/g, '<br />')}</p>`;

    const printHtml = generatePrintHtml(photo, contentHtml, embeddedImageUrl, formattedDate, scores);
    container = buildOffscreenRenderContainer(printHtml);
    await waitForContainerAssets(container);

    emitPdfProgress(
      onProgress,
      '초고해상도(Retina 2x) 벡터 캔버스 캡처 중...',
      '텍스트와 이미지를 선명한 픽셀로 정밀 렌더링하고 있습니다.',
      65
    );
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
      windowWidth: 794,
    });

    if (!canvas || canvas.width <= 0 || canvas.height <= 0) {
      throw new Error('Canvas capture resulted in invalid dimensions');
    }

    emitPdfProgress(
      onProgress,
      'A4 페이지 슬라이스 및 PDF 조립 중...',
      '인쇄 규격에 맞춰 페이지를 분할하고 최종 문서를 조립하고 있습니다.',
      85
    );
    await delay(80);

    const pdf = renderCanvasToPdf(canvas);

    emitPdfProgress(
      onProgress,
      '저장 경로 확인 및 파일 기록 중...',
      '원하는 저장 위치와 파일명을 선택해 주세요.',
      95
    );

    const baseName = photo?.file_name ? photo.file_name.replace(/\.[^/.]+$/, '') : 'photo';
    const defaultFileName = `${baseName}_AI비평_리포트.pdf`;
    const selection = await pickSaveFilePath(defaultFileName, 'PDF 문서 (*.pdf)', ['pdf']);

    if (selection.cancelled) {
      return { success: false, savedPath: null, cancelled: true };
    }

    if (selection.selectedPath) {
      const uint8Array = new Uint8Array(pdf.output('arraybuffer'));
      await saveBinaryFileViaTauri(selection.selectedPath, uint8Array);
      return { success: true, savedPath: selection.selectedPath };
    }

    pdf.save(defaultFileName);
    return { success: true, savedPath: null };
  } finally {
    if (container && container.parentNode) {
      container.parentNode.removeChild(container);
    }
  }
}
