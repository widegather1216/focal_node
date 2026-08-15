/**
 * Formatting utilities for EXIF camera metadata (aperture, shutter speed, ISO, focal length).
 */

export function formatAperture(fNumber?: number | string | null): string {
  if (fNumber === undefined || fNumber === null || fNumber === '') return '';
  const num = typeof fNumber === 'number' ? fNumber : parseFloat(String(fNumber));
  if (isNaN(num)) return `f/${fNumber}`;
  const rounded = Math.round(num * 10) / 10;
  return `f/${rounded % 1 === 0 ? rounded.toFixed(1) : rounded}`;
}

export function formatShutterSpeed(shutterSpeed?: string | number | null): string {
  if (shutterSpeed === undefined || shutterSpeed === null || shutterSpeed === '') return '';
  
  if (typeof shutterSpeed === 'string') {
    const trimmed = shutterSpeed.trim();
    if (trimmed.includes('/')) {
      return trimmed.endsWith('s') ? trimmed : `${trimmed}s`;
    }
    const parsed = parseFloat(trimmed);
    if (!isNaN(parsed)) {
      return formatNumericShutterSpeed(parsed);
    }
    return trimmed.endsWith('s') ? trimmed : `${trimmed}s`;
  }

  return formatNumericShutterSpeed(shutterSpeed);
}

function formatNumericShutterSpeed(seconds: number): string {
  if (seconds <= 0) return '';
  if (seconds >= 1) {
    const rounded = Math.round(seconds * 10) / 10;
    return `${rounded}s`;
  }
  // Convert decimals < 1 into standard photo fractions like 1/250s, 1/1000s
  const denominator = Math.round(1 / seconds);
  return `1/${denominator}s`;
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
  const parts: string[] = [];
  if (metadata.f_number) parts.push(formatAperture(metadata.f_number));
  if (metadata.shutter_speed) parts.push(formatShutterSpeed(metadata.shutter_speed));
  if (metadata.iso) parts.push(formatIso(metadata.iso));
  if (metadata.focal_length) parts.push(`${metadata.focal_length}mm`);
  return parts.join(' · ');
}
