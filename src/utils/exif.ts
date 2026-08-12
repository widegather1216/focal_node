/**
 * Formatting utilities for EXIF camera metadata (aperture, shutter speed, ISO, focal length).
 */

export function formatAperture(fNumber?: number | string | null): string {
  if (fNumber === undefined || fNumber === null || fNumber === '') return '';
  const num = typeof fNumber === 'number' ? fNumber : parseFloat(fNumber);
  if (isNaN(num)) return `f/${fNumber}`;
  const rounded = Math.round(num * 100) / 100;
  return `f/${rounded}`;
}

export function formatShutterSpeed(shutterSpeed?: string | number | null): string {
  if (shutterSpeed === undefined || shutterSpeed === null || shutterSpeed === '') return '';
  const str = String(shutterSpeed);
  return str.endsWith('s') ? str : `${str}s`;
}

export function formatIso(iso?: number | string | null): string {
  if (iso === undefined || iso === null || iso === '') return '';
  return `ISO ${iso}`;
}

export function formatFocalLength(focalLength?: number | null, focal35mm?: number | null): string {
  if (focalLength === undefined || focalLength === null) return '';
  let res = `${focalLength}mm`;
  if (focal35mm && focal35mm !== focalLength) {
    res += ` (35mm 환산 ${focal35mm}mm)`;
  }
  return res;
}

export function formatExifSummary(metadata: any): string {
  if (!metadata) return '';
  const parts = [];
  if (metadata.f_number) parts.push(formatAperture(metadata.f_number));
  if (metadata.shutter_speed) parts.push(formatShutterSpeed(metadata.shutter_speed));
  if (metadata.iso) parts.push(formatIso(metadata.iso));
  if (metadata.focal_length) parts.push(`${metadata.focal_length}mm`);
  return parts.join(' · ');
}
