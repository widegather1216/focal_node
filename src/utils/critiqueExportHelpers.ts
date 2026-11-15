import jsPDF from 'jspdf';

export interface SaveDialogSelection {
  selectedPath: string | null;
  cancelled: boolean;
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
 * Opens the Tauri native save dialog when available and distinguishes user cancellation from web fallback.
 */
export async function pickSaveFilePath(
  defaultFileName: string,
  filterName: string,
  extensions: string[]
): Promise<SaveDialogSelection> {
  let selectedPath: string | null = null;
  try {
    const { save } = await import('@tauri-apps/plugin-dialog');
    selectedPath = await save({
      defaultPath: defaultFileName,
      filters: [{ name: filterName, extensions }],
    });
  } catch (dialogErr) {
    console.warn('Tauri dialog save is unavailable, will fallback to browser download:', dialogErr);
    return { selectedPath: null, cancelled: false };
  }

  const isTauriEnv = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
  if (selectedPath === null && isTauriEnv) {
    return { selectedPath: null, cancelled: true };
  }
  return { selectedPath, cancelled: false };
}

/**
 * Writes raw bytes via Tauri IPC when a native path is selected.
 */
export async function saveBinaryFileViaTauri(selectedPath: string, bytes: Uint8Array): Promise<void> {
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('save_binary_file', {
    path: selectedPath,
    data: Array.from(bytes),
  });
}

function waitForImageDecode(img: HTMLImageElement): Promise<void> {
  return new Promise<void>((resolve) => {
    const decodeAndResolve = () => {
      if ('decode' in img) {
        img.decode().then(() => resolve()).catch(() => resolve());
      } else {
        resolve();
      }
    };

    if (img.complete && img.naturalWidth > 0) {
      decodeAndResolve();
      return;
    }
    img.onload = decodeAndResolve;
    img.onerror = () => resolve();
  });
}

/**
 * Waits until all images and two layout/paint frames inside the offscreen render container settle.
 */
export async function waitForContainerAssets(container: HTMLDivElement): Promise<void> {
  const imgElements = Array.from(container.querySelectorAll('img'));
  await Promise.all(imgElements.map(waitForImageDecode));
  await new Promise<void>((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => resolve());
    });
  });
}

/**
 * Slices a tall rendered canvas into A4 portrait pages inside a jsPDF document.
 */
export function renderCanvasToPdf(canvas: HTMLCanvasElement): jsPDF {
  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
    compress: true,
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
      ctx.drawImage(canvas, 0, renderedHeight, canvas.width, sliceHeightPx, 0, 0, canvas.width, sliceHeightPx);
    }

    const pageImageUrl = pageCanvas.toDataURL('image/jpeg', 0.95);
    pdf.addImage(pageImageUrl, 'JPEG', 0, 0, pageWidthMm, pageHeightMm, undefined, 'FAST');

    renderedHeight += pageHeightPx;
    pageIndex++;
  }

  return pdf;
}

/**
 * Reveals a saved file in OS file manager (Finder / File Explorer).
 */
export async function revealSavedFile(path: string): Promise<void> {
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('reveal_in_finder', { path });
  } catch (err) {
    console.warn('Failed to reveal file in finder:', err);
  }
}
