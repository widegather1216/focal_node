import { create } from 'zustand';

interface IndexingProgress {
  processed: number;
  total: number;
  filePath: string;
}

export interface IndexedFolder {
  path: string;
  created_at: string;
}

export interface SearchFilters {
  is_favorite?: boolean;
  camera_model?: string;
  lens_model?: string;
  iso_min?: number;
  iso_max?: number;
  f_number_min?: number;
  f_number_max?: number;
  focal_length_min?: number;
  focal_length_max?: number;
  date_from?: string;
  date_to?: string;
}

interface AppState {
  apiPort: number | null;
  setApiPort: (port: number | null) => void;
  
  backendStatus: string;
  setBackendStatus: (status: string) => void;
  
  backendError: string | null;
  setBackendError: (error: string | null) => void;

  searchQuery: string;
  setSearchQuery: (query: string) => void;

  searchFilters: SearchFilters;
  setSearchFilters: (filters: SearchFilters) => void;
  clearSearchFilters: () => void;

  isIndexing: boolean;
  indexingProgress: IndexingProgress | null;
  setIndexingProgress: (progress: IndexingProgress | null) => void;
  setIsIndexing: (isIndexing: boolean) => void;

  isDownloadingModel: boolean;
  setIsDownloadingModel: (isDownloading: boolean) => void;
  downloadProgress: number;
  setDownloadProgress: (progress: number) => void;
  downloadModelName: string;
  setDownloadModelName: (name: string) => void;

  isSearching: boolean;
  setIsSearching: (isSearching: boolean) => void;

  selectedPhotoId: string | null;
  setSelectedPhotoId: (id: string | null) => void;

  selectedPhotoIds: Set<string>;
  togglePhotoSelection: (id: string) => void;
  clearSelection: () => void;

  folders: IndexedFolder[];
  setFolders: (folders: IndexedFolder[]) => void;
  fetchFolders: () => Promise<void>;
  removeFolder: (path: string) => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  apiPort: null,
  setApiPort: (port) => set({ apiPort: port }),

  backendStatus: "Loading...",
  setBackendStatus: (status) => set({ backendStatus: status }),

  backendError: null,
  setBackendError: (error) => set({ backendError: error }),

  searchQuery: '',
  setSearchQuery: (query) => set({ searchQuery: query }),

  searchFilters: {},
  setSearchFilters: (filters) => set({ searchFilters: filters }),
  clearSearchFilters: () => set({ searchFilters: {} }),

  isIndexing: false,
  indexingProgress: null,
  setIndexingProgress: (progress) => set({ indexingProgress: progress }),
  setIsIndexing: (isIndexing) => set({ isIndexing }),

  isDownloadingModel: false,
  setIsDownloadingModel: (isDownloadingModel) => set({ isDownloadingModel }),
  downloadProgress: 0,
  setDownloadProgress: (downloadProgress) => set({ downloadProgress }),
  downloadModelName: "AI 모델",
  setDownloadModelName: (downloadModelName) => set({ downloadModelName }),

  isSearching: false,
  setIsSearching: (isSearching) => set({ isSearching }),

  selectedPhotoId: null,
  setSelectedPhotoId: (id) => set({ selectedPhotoId: id }),

  selectedPhotoIds: new Set(),
  togglePhotoSelection: (id) => set((state) => {
    const nextSet = new Set(state.selectedPhotoIds);
    if (nextSet.has(id)) {
      nextSet.delete(id);
    } else {
      nextSet.add(id);
    }
    return { selectedPhotoIds: nextSet };
  }),
  clearSelection: () => set({ selectedPhotoIds: new Set() }),

  folders: [],
  setFolders: (folders) => set({ folders }),
  fetchFolders: async () => {
    const port = get().apiPort;
    if (!port) return;
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/folders`);
      if (response.ok) {
        const folders = await response.json();
        set({ folders });
      }
    } catch (error) {
      console.error('Failed to fetch folders:', error);
    }
  },
  removeFolder: async (path: string) => {
    const port = get().apiPort;
    if (!port) return;
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/folders?path=${encodeURIComponent(path)}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        set((state) => ({ folders: state.folders.filter(f => f.path !== path) }));
      }
    } catch (error) {
      console.error('Failed to remove folder:', error);
    }
  },
}));
