export interface CritiqueItem {
  photo_id: string;
  file_name: string;
  file_path: string;
  capture_date?: string | null;
  camera_model?: string | null;
  lens_model?: string | null;
  f_number?: number | null;
  shutter_speed?: string | null;
  iso?: number | null;
  critique: string;
  critique_updated_at?: string | null;
}

export interface CritiqueSummaryResponse {
  summary: string;
  total_critiques_analyzed: number;
  created_at: string;
}

export interface CritiqueStatus {
  photo_id: string;
  step: number;
  total_steps: number;
  message: string;
  progress: number;
  status: 'idle' | 'processing' | 'completed' | 'error';
}

