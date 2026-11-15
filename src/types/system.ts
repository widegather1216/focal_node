export interface HealthCheckResponse {
  status: string;
}

export interface ApiMessageResponse {
  message: string;
}

export interface FolderResponse {
  path: string;
  created_at: string;
}

export type IndexingLifecycleState = 'idle' | 'processing' | 'paused' | 'cancelled' | 'error';

export interface IndexingStatusResponse {
  status: IndexingLifecycleState;
  total_files: number;
  processed_files: number;
  current_file: string;
  error_message: string | null;
  run_id: number;
}

export type ModelDownloadItemStatus = 'pending' | 'cached' | 'downloading' | 'completed' | 'error';

export interface ModelDownloadEntry {
  repo_id: string;
  label: string;
  status: ModelDownloadItemStatus;
  progress?: number;
  downloaded_bytes?: number;
  total_bytes?: number;
  step?: number;
  total_steps?: number;
  error_message: string | null;
  updated_at: number;
}

export interface ModelDownloadOverall {
  progress: number;
  downloaded_bytes: number;
  total_bytes: number;
  current_label: string;
  step?: number;
  total_steps?: number;
  is_all_done: boolean;
}

export interface ModelDownloadStatusResponse {
  statuses: Record<string, ModelDownloadEntry>;
  overall?: ModelDownloadOverall;
}

export interface TriggerModelDownloadResponse {
  started: boolean;
  statuses: Record<string, ModelDownloadEntry>;
  overall: ModelDownloadOverall;
}
