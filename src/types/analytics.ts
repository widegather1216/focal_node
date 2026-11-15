export interface GearStatItem {
  name: string;
  count: number;
}

export interface GearStats {
  total_photos: number;
  cameras: GearStatItem[];
  lenses: GearStatItem[];
  focal_lengths: GearStatItem[];
  focal_lengths_35mm: GearStatItem[];
  apertures: GearStatItem[];
}

export interface ChartTooltipPayloadItem {
  name?: string;
  value?: number | string;
  color?: string;
}

export interface ChartTooltipProps {
  active?: boolean;
  payload?: ChartTooltipPayloadItem[];
  label?: string | number;
}
