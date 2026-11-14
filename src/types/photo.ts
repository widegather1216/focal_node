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

export interface PhotoMetadata {
  width?: number | null;
  height?: number | null;
  color_space?: string | null;
  capture_date?: string | null;
  camera_make?: string | null;
  camera_model?: string | null;
  lens_make?: string | null;
  lens_model?: string | null;
  focal_length?: number | null;
  focal_length_35mm?: number | null;
  crop_factor?: number | null;
  sensor_format?: string | null;
  f_number?: number | null;
  shutter_speed?: string | null;
  iso?: number | null;
  exposure_bias?: number | null;
  flash?: string | null;
  orientation?: number | null;
  gps_latitude?: number | null;
  gps_longitude?: number | null;
  gps_altitude?: number | null;
}

export interface Photo {
  id: string;
  file_path: string;
  file_name: string;
  file_size: number;
  created_at: string;
  caption?: string | null;
  tags?: string[] | null;
  is_favorite: boolean;
  metadata?: PhotoMetadata | null;
}

export interface PhotosResponse {
  photos: Photo[];
  total: number;
}

export interface PhotoDetail {
  id: string;
  file_name: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  is_favorite: boolean;
  metadata: {
    width: number | null;
    height: number | null;
    color_space: string;
    camera_model: string | null;
    lens_model: string | null;
    f_number: number | null;
    focal_length: number | null;
    focal_length_35mm: number | null;
    crop_factor: number | null;
    sensor_format: string | null;
    shutter_speed: string | null;
    iso: number | null;
    capture_date: string | null;
  };
  ai_analysis: {
    caption: string | null;
    tags: string[];
    aesthetic_tags?: string[];
    is_user_edited: boolean;
    critique?: string | null;
    critique_en?: string | null;
    overall_score?: number | null;
    iaa_score?: number | null;
    iqa_score?: number | null;
    ista_score?: number | null;
    critique_updated_at?: string | null;
  };
}

export interface UpdateMetadataResponse {
  status: string;
  id: string;
  ai_analysis: PhotoDetail['ai_analysis'];
}
