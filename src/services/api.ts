import { useAppStore } from '../store/useAppStore';
import { PhotoDetail, PhotoSummary, SearchFilters, UpdateMetadataResponse } from '../types/photo';
import {
  CritiqueCancelResponse,
  CritiqueDeleteResponse,
  CritiqueItem,
  CritiqueResponse,
  CritiqueStatus,
  CritiqueSummaryResponse,
} from '../types/critique';
import { GearStatItem, GearStats } from '../types/analytics';
import {
  ApiMessageResponse,
  FolderResponse,
  HealthCheckResponse,
  IndexingStatusResponse,
  ModelDownloadStatusResponse,
  TriggerModelDownloadResponse,
} from '../types/system';
import { ExportResult, parseExportSseStream } from '../utils/exportStream';
import { extractResponseErrorMessage } from '../utils/apiError';
import {
  buildSearchRequestSpec,
  fetchPhotosRequest,
  postJsonRequest,
} from '../utils/searchRequest';

export type {
  CritiqueCancelResponse,
  CritiqueDeleteResponse,
  CritiqueItem,
  CritiqueResponse,
  CritiqueStatus,
  CritiqueSummaryResponse,
};
export type { PhotoDetail, PhotoSummary, SearchFilters, UpdateMetadataResponse };
export type { GearStatItem, GearStats };
export type {
  ApiMessageResponse,
  FolderResponse,
  HealthCheckResponse,
  IndexingStatusResponse,
  ModelDownloadStatusResponse,
  TriggerModelDownloadResponse,
};
export type { ExportResult };


export class ApiHttpError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = 'ApiHttpError';
  }
}

class ApiClient {
  private get baseUrl(): string {
    const port = useAppStore.getState().apiPort;
    if (!port) {
      throw new Error("Backend port not initialized yet.");
    }
    return `http://127.0.0.1:${port}`;
  }

  private async parseError(response: Response, defaultMessage: string): Promise<string> {
    return extractResponseErrorMessage(response, defaultMessage);
  }

  async healthCheck(): Promise<HealthCheckResponse> {
    const res = await fetch(`${this.baseUrl}/api/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
    return res.json();
  }

  async fetchPhotos(
    limit: number,
    offset: number,
    folder: string | null,
    signal?: AbortSignal,
  ): Promise<PhotoSummary[]> {
    return fetchPhotosRequest({
      baseUrl: this.baseUrl,
      limit,
      offset,
      folder,
      signal,
    });
  }

  private async postJson<T>(
    endpoint: string,
    payload: Record<string, unknown>,
    errorContext: string,
    signal?: AbortSignal,
  ): Promise<T> {
    return postJsonRequest<T>({
      baseUrl: this.baseUrl,
      endpoint,
      payload,
      errorContext,
      signal,
    });
  }

  async searchPhotos(
    query: string | undefined,
    filters: SearchFilters | undefined,
    limit: number,
    offset: number,
    folder?: string | null,
    signal?: AbortSignal,
  ): Promise<PhotoSummary[]> {
    const spec = buildSearchRequestSpec(query, filters, limit, offset, folder);
    return this.postJson<PhotoSummary[]>(
      spec.endpoint,
      spec.payload,
      spec.errorContext,
      signal,
    );
  }

  async getPhotoDetail(id: string): Promise<PhotoDetail> {
    const res = await fetch(`${this.baseUrl}/api/photos/${id}`);
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to fetch photo detail");
      throw new Error(err);
    }
    return res.json();
  }

  async updatePhotoMetadata(id: string, caption: string, tags: string[]): Promise<UpdateMetadataResponse> {
    const res = await fetch(`${this.baseUrl}/api/photos/${id}/metadata`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ caption, tags })
    });
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to update photo metadata");
      throw new Error(err);
    }
    return res.json();
  }

  async exportPhotos(
    photoIds: string[],
    destinationFolder: string,
    signal?: AbortSignal,
  ): Promise<ExportResult> {
    const uniquePhotoIds = Array.from(new Set(photoIds));
    const response = await fetch(`${this.baseUrl}/api/photos/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        photo_ids: uniquePhotoIds,
        destination_folder: destinationFolder,
      }),
      signal,
    });

    if (!response.ok) {
      const errorDetail = await this.parseError(response, 'Failed to export photos');
      throw new Error(errorDetail);
    }
    if (!response.body) {
      throw new Error('No response body');
    }

    return parseExportSseStream(response.body, signal);
  }

  async fetchFolders(): Promise<FolderResponse[]> {
    const res = await fetch(`${this.baseUrl}/api/folders`);
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to fetch folders");
      throw new Error(err);
    }
    return res.json();
  }

  async removeFolder(path: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/folders?path=${encodeURIComponent(path)}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to remove folder");
      throw new ApiHttpError(err, res.status);
    }
  }

  async startIndexing(folderPaths: string[]): Promise<ApiMessageResponse> {
    const res = await fetch(`${this.baseUrl}/api/index/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_paths: folderPaths })
    });
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to start indexing");
      throw new Error(`Failed to start indexing: ${err}`);
    }
    return res.json();
  }

  async syncDatabase(): Promise<ApiMessageResponse> {
    const res = await fetch(`${this.baseUrl}/api/index/sync`, { method: 'POST' });
    if (!res.ok) {
      const err = await this.parseError(res, "Sync failed");
      throw new Error(`Sync failed: ${err}`);
    }
    return res.json();
  }

  async pauseIndexing(): Promise<ApiMessageResponse> {
    const res = await fetch(`${this.baseUrl}/api/index/pause`, { method: 'POST' });
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to pause indexing");
      throw new Error(`Failed to pause indexing: ${err}`);
    }
    return res.json();
  }

  async resumeIndexing(): Promise<ApiMessageResponse> {
    const res = await fetch(`${this.baseUrl}/api/index/resume`, { method: 'POST' });
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to resume indexing");
      throw new Error(`Failed to resume indexing: ${err}`);
    }
    return res.json();
  }

  async cancelIndexing(): Promise<ApiMessageResponse> {
    const res = await fetch(`${this.baseUrl}/api/index/cancel`, { method: 'POST' });
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to cancel indexing");
      throw new Error(`Failed to cancel indexing: ${err}`);
    }
    return res.json();
  }

  async getIndexingStatus(): Promise<IndexingStatusResponse> {
    const res = await fetch(`${this.baseUrl}/api/index/status`);
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to fetch indexing status");
      throw new Error(err);
    }
    return res.json();
  }

  async getPhotoCritique(photoId: string, signal?: AbortSignal): Promise<CritiqueResponse> {
    const res = await fetch(`${this.baseUrl}/api/chat/critique`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ photo_id: photoId }),
      signal
    });
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to get photo critique");
      throw new Error(err);
    }
    return res.json();
  }

  async cancelCritique(photoId: string): Promise<CritiqueCancelResponse> {
    const res = await fetch(`${this.baseUrl}/api/chat/critique/cancel/${encodeURIComponent(photoId)}`, {
      method: 'POST'
    });
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to cancel photo critique");
      throw new Error(err);
    }
    return res.json();
  }

  async getCritiques(sortBy?: 'recent' | 'overall_score' | 'iaa_score'): Promise<CritiqueItem[]> {
    const url = sortBy ? `${this.baseUrl}/api/chat/critiques?sort_by=${sortBy}` : `${this.baseUrl}/api/chat/critiques`;
    const res = await fetch(url);
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to fetch critiques");
      throw new Error(err);
    }
    return res.json();
  }

  async deleteCritique(photoId: string): Promise<CritiqueDeleteResponse> {
    const res = await fetch(`${this.baseUrl}/api/chat/critique/${encodeURIComponent(photoId)}`, {
      method: 'DELETE'
    });
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to delete critique");
      throw new Error(err);
    }
    return res.json();
  }

  async getCritiqueSummary(photoIds?: string[]): Promise<CritiqueSummaryResponse> {
    const res = await fetch(`${this.baseUrl}/api/chat/critique-summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ photo_ids: photoIds || null })
    });
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to generate critique summary");
      throw new Error(err);
    }
    return res.json();
  }

  async getCritiqueStatus(photoId: string): Promise<CritiqueStatus> {
    const res = await fetch(`${this.baseUrl}/api/chat/critique/status/${photoId}`);
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to fetch critique status");
      throw new Error(err);
    }
    return res.json();
  }


  async reindexPhoto(id: string): Promise<PhotoDetail> {
    const res = await fetch(`${this.baseUrl}/api/photos/${id}/reindex`, {
      method: 'POST'
    });
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to reindex photo");
      throw new Error(`Failed to reindex photo: ${err}`);
    }
    return res.json();
  }

  async toggleFavorite(id: string): Promise<{ id: string, is_favorite: boolean }> {
    const res = await fetch(`${this.baseUrl}/api/photos/${id}/favorite`, {
      method: 'POST'
    });
    if (!res.ok) {
      const err = await this.parseError(res, "Failed to toggle favorite");
      throw new Error(`Failed to toggle favorite: ${err}`);
    }
    return res.json();
  }

  getPhotoThumbnailUrl(id: string): string {
    return `${this.baseUrl}/api/photos/${id}/thumbnail`;
  }

  getPhotoOriginalUrl(id: string): string {
    return `${this.baseUrl}/api/photos/${id}/original`;
  }

  async getAnalyticsStats(): Promise<GearStats> {
    const res = await fetch(`${this.baseUrl}/api/analytics/stats`);
    if (!res.ok) throw new Error("Failed to fetch analytics stats");
    return res.json();
  }

  async getModelDownloadStatus(): Promise<ModelDownloadStatusResponse> {
    const res = await fetch(`${this.baseUrl}/api/system/models/status`);
    if (!res.ok) throw new Error("Failed to fetch model download status");
    return res.json();
  }

  async triggerModelDownload(): Promise<TriggerModelDownloadResponse> {
    const res = await fetch(`${this.baseUrl}/api/system/models/download`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error("Failed to trigger model download");
    return res.json();
  }
}

export const api = new ApiClient();
