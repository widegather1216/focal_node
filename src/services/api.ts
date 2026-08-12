import { useAppStore } from '../store/useAppStore';
import { SearchFilters } from '../types/photo';
import { CritiqueItem, CritiqueSummaryResponse } from '../types/critique';

export type { CritiqueItem, CritiqueSummaryResponse };
export type { SearchFilters };


class ApiClient {
  private get baseUrl(): string {
    const port = useAppStore.getState().apiPort;
    if (!port) {
      throw new Error("Backend port not initialized yet.");
    }
    return `http://127.0.0.1:${port}`;
  }

  async healthCheck(): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
    return res.json();
  }

  async fetchPhotos(limit: number, offset: number, folder: string | null): Promise<any[]> {
    let url = `${this.baseUrl}/api/photos?limit=${limit}&offset=${offset}`;
    if (folder) {
      url += `&parent_dir=${encodeURIComponent(folder)}`;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch photos");
    return res.json();
  }

  async searchPhotos(query: string | undefined, filters: SearchFilters | undefined, limit: number, offset: number): Promise<any[]> {
    let cleanQuery = query ? query.trim() : undefined;
    
    // Check if it's a similar search
    if (cleanQuery && cleanQuery.startsWith('similar:')) {
      const photoId = cleanQuery.replace('similar:', '');
      const res = await fetch(`${this.baseUrl}/api/search/similar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          photo_id: photoId,
          filters: filters,
          limit,
          offset
        })
      });
      if (!res.ok) throw new Error("Failed to search similar photos");
      return res.json();
    }

    // Normal semantic search
    const res = await fetch(`${this.baseUrl}/api/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: cleanQuery,
        filters: filters,
        limit,
        offset
      })
    });
    if (!res.ok) throw new Error("Failed to search photos");
    return res.json();
  }

  async getPhotoDetail(id: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/photos/${id}`);
    if (!res.ok) throw new Error("Failed to fetch photo detail");
    return res.json();
  }

  async updatePhotoMetadata(id: string, caption: string, tags: string[]): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/photos/${id}/metadata`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ caption, tags })
    });
    if (!res.ok) throw new Error("Failed to update photo metadata");
    return res.json();
  }

  async exportPhotos(photoIds: string[], destinationFolder: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/photos/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        photo_ids: photoIds,
        destination_folder: destinationFolder
      })
    });
    
    if (!res.ok) throw new Error("Failed to export photos");
    if (!res.body) throw new Error("No response body");

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let finalData = null;
    let buffer = "";

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || "";
        
        for (const part of parts) {
          if (part.startsWith('event: done')) {
            const dataMatch = part.match(/data: (.*)/);
            if (dataMatch) {
              finalData = JSON.parse(dataMatch[1]);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
    
    if (!finalData) throw new Error("Export stream ended without final data");
    return finalData;
  }

  async fetchFolders(): Promise<any[]> {
    const res = await fetch(`${this.baseUrl}/api/folders`);
    if (!res.ok) throw new Error("Failed to fetch folders");
    return res.json();
  }

  async removeFolder(path: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/folders?path=${encodeURIComponent(path)}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error("Failed to remove folder");
  }

  async startIndexing(folderPaths: string[]): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/index/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_paths: folderPaths })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(`Failed to start indexing: ${err.detail}`);
    }
    return res.json();
  }

  async syncDatabase(): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/index/sync`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(`Sync failed: ${err.detail}`);
    }
    return res.json();
  }

  async pauseIndexing(): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/index/pause`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(`Failed to pause indexing: ${err.detail}`);
    }
    return res.json();
  }

  async resumeIndexing(): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/index/resume`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(`Failed to resume indexing: ${err.detail}`);
    }
    return res.json();
  }

  async cancelIndexing(): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/index/cancel`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(`Failed to cancel indexing: ${err.detail}`);
    }
    return res.json();
  }

  async getIndexingStatus(): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/index/status`);
    if (!res.ok) throw new Error("Failed to fetch indexing status");
    return res.json();
  }

  async getPhotoCritique(photoId: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/chat/critique`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ photo_id: photoId })
    });
    if (!res.ok) throw new Error("Failed to get photo critique");
    return res.json();
  }

  async getCritiques(): Promise<any[]> {
    const res = await fetch(`${this.baseUrl}/api/chat/critiques`);
    if (!res.ok) throw new Error("Failed to fetch critiques");
    return res.json();
  }

  async deleteCritique(photoId: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/chat/critique/${encodeURIComponent(photoId)}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error("Failed to delete critique");
    return res.json();
  }

  async getCritiqueSummary(photoIds?: string[]): Promise<CritiqueSummaryResponse> {
    const res = await fetch(`${this.baseUrl}/api/chat/critique-summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ photo_ids: photoIds || null })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(err.detail || "Failed to generate critique summary");
    }
    return res.json();
  }

  async getCritiqueStatus(photoId: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/chat/critique/status/${photoId}`);
    if (!res.ok) throw new Error("Failed to fetch critique status");
    return res.json();
  }


  async reindexPhoto(id: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/photos/${id}/reindex`, {
      method: 'POST'
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(`Failed to reindex photo: ${err.detail}`);
    }
    return res.json();
  }

  async toggleFavorite(id: string): Promise<{ id: string, is_favorite: boolean }> {
    const res = await fetch(`${this.baseUrl}/api/photos/${id}/favorite`, {
      method: 'POST'
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(`Failed to toggle favorite: ${err.detail}`);
    }
    return res.json();
  }

  getPhotoThumbnailUrl(id: string): string {
    return `${this.baseUrl}/api/photos/${id}/thumbnail`;
  }

  getPhotoOriginalUrl(id: string): string {
    return `${this.baseUrl}/api/photos/${id}/original`;
  }

  async getAnalyticsStats(): Promise<{
    total_photos: number;
    cameras: { name: string; count: number }[];
    lenses: { name: string; count: number }[];
    focal_lengths: { name: string; count: number }[];
    focal_lengths_35mm: { name: string; count: number }[];
    apertures: { name: string; count: number }[];
  }> {
    const res = await fetch(`${this.baseUrl}/api/analytics/stats`);
    if (!res.ok) throw new Error("Failed to fetch analytics stats");
    return res.json();
  }

  async getModelDownloadStatus(): Promise<{
    statuses: Record<string, {
      repo_id: string;
      label: string;
      status: 'cached' | 'downloading' | 'completed' | 'error';
      progress?: number;
      downloaded_bytes?: number;
      total_bytes?: number;
      step?: number;
      total_steps?: number;
      error_message: string | null;
      updated_at: number;
    }>;
    overall?: {
      progress: number;
      downloaded_bytes: number;
      total_bytes: number;
      current_label: string;
      step: number;
      total_steps: number;
      is_all_done: boolean;
    };
  }> {
    const res = await fetch(`${this.baseUrl}/api/system/models/status`);
    if (!res.ok) throw new Error("Failed to fetch model download status");
    return res.json();
  }

  async triggerModelDownload(): Promise<{
    started: boolean;
    statuses: Record<string, any>;
    overall: any;
  }> {
    const res = await fetch(`${this.baseUrl}/api/system/models/download`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error("Failed to trigger model download");
    return res.json();
  }
}

export const api = new ApiClient();
