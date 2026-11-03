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
