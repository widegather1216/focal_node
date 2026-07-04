import { useAppStore, SearchFilters } from '../store/useAppStore';

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

  async getPhotoCritique(photoId: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/chat/critique`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ photo_id: photoId })
    });
    if (!res.ok) throw new Error("Failed to get photo critique");
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
}


export const api = new ApiClient();
