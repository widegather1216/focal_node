import { create } from 'zustand';
import { SearchFilters } from '../types/photo';

export type { SearchFilters };

interface IndexingProgress {
  processed: number;
  total: number;
  filePath: string;
}

export interface IndexedFolder {
  path: string;
  created_at: string;
}

interface AppState {
  activeTab: 'gallery' | 'analytics' | 'critique';
  setActiveTab: (tab: 'gallery' | 'analytics' | 'critique') => void;

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
  indexingState: 'idle' | 'processing' | 'paused' | 'cancelled';
  indexingProgress: IndexingProgress | null;
  setIndexingProgress: (progress: IndexingProgress | null) => void;
  setIsIndexing: (isIndexing: boolean) => void;
  setIndexingState: (state: 'idle' | 'processing' | 'paused' | 'cancelled') => void;

  isDownloadingModel: boolean;
  setIsDownloadingModel: (isDownloading: boolean) => void;
  downloadProgress: number;
  setDownloadProgress: (progress: number) => void;
  downloadedBytes: number;
  totalBytes: number;
  setDownloadBytes: (downloaded: number, total: number) => void;
  downloadModelName: string;
  setDownloadModelName: (name: string) => void;
  downloadError: string | null;
  setDownloadError: (error: string | null) => void;

  isSearching: boolean;
  setIsSearching: (isSearching: boolean) => void;

  selectedPhotoId: string | null;
  setSelectedPhotoId: (id: string | null) => void;

  isFullscreenOpen: boolean;
  fullscreenPhotoId: string | null;
  openFullscreen: (photoId: string) => void;
  closeFullscreen: () => void;

  selectedPhotoIds: Set<string>;
  togglePhotoSelection: (id: string) => void;
  clearSelection: () => void;

  generatingCritiquePhotoIds: Set<string>;
  addGeneratingCritiquePhotoId: (id: string) => void;
  removeGeneratingCritiquePhotoId: (id: string) => void;

  folders: IndexedFolder[];
  setFolders: (folders: IndexedFolder[]) => void;
  fetchFolders: () => Promise<void>;
  removeFolder: (path: string) => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  activeTab: 'gallery',
  setActiveTab: (activeTab) => set({ activeTab }),

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
  indexingState: 'idle',
  indexingProgress: null,
  setIndexingProgress: (progress) => set({ indexingProgress: progress }),
  setIsIndexing: (isIndexing) => set({ isIndexing, indexingState: isIndexing ? 'processing' : 'idle' }),
  setIndexingState: (indexingState) => set({ indexingState, isIndexing: indexingState === 'processing' || indexingState === 'paused' }),

  isDownloadingModel: false,
  setIsDownloadingModel: (isDownloadingModel) => set({ isDownloadingModel }),
  downloadProgress: 0,
  setDownloadProgress: (downloadProgress) => set({ downloadProgress }),
  downloadedBytes: 0,
  totalBytes: 0,
  setDownloadBytes: (downloadedBytes, totalBytes) => set({ downloadedBytes, totalBytes }),
  downloadModelName: "AI 모델",
  setDownloadModelName: (downloadModelName) => set({ downloadModelName }),
  downloadError: null,
  setDownloadError: (downloadError) => set({ downloadError }),

  isSearching: false,
  setIsSearching: (isSearching) => set({ isSearching }),

  selectedPhotoId: null,
  setSelectedPhotoId: (id) => set({ selectedPhotoId: id }),

  isFullscreenOpen: false,
  fullscreenPhotoId: null,
  openFullscreen: (photoId) => set({ isFullscreenOpen: true, fullscreenPhotoId: photoId }),
  closeFullscreen: () => set({ isFullscreenOpen: false, fullscreenPhotoId: null }),

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

  generatingCritiquePhotoIds: new Set(),
  addGeneratingCritiquePhotoId: (id) => set((state) => {
    const nextSet = new Set(state.generatingCritiquePhotoIds);
    nextSet.add(id);
    return { generatingCritiquePhotoIds: nextSet };
  }),
  removeGeneratingCritiquePhotoId: (id) => set((state) => {
    const nextSet = new Set(state.generatingCritiquePhotoIds);
    nextSet.delete(id);
    return { generatingCritiquePhotoIds: nextSet };
  }),

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
        get().fetchFolders();
      }
    } catch (error) {
      console.error('Failed to remove folder:', error);
    }
  },
}));
