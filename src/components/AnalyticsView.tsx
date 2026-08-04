import { BarChart3 } from 'lucide-react';
import { useAnalyticsQuery } from '../hooks/useAnalyticsQuery';
import { LoadingSpinner } from './common/LoadingSpinner';
import { AnalyticsKpiGrid } from './analytics/AnalyticsKpiGrid';
import { GearDonutCharts } from './analytics/GearDonutCharts';
import { ExifBarCharts } from './analytics/ExifBarCharts';

const COLORS = [
  '#38bdf8', '#818cf8', '#c084fc', '#f472b6', '#fb7185',
  '#4ade80', '#facc15', '#fb923c', '#a7f3d0', '#93c5fd'
];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const item = payload[0];
    return (
      <div style={{
        backgroundColor: '#18181b',
        border: '1px solid #3f3f46',
        borderRadius: '8px',
        padding: '10px 14px',
        color: '#fff',
        boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
        fontSize: '13px'
      }}>
        <div style={{ fontWeight: 600, color: '#e4e4e7', marginBottom: '4px' }}>
          {label || item.name}
        </div>
        <div style={{ color: item.color || '#38bdf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '15px', fontWeight: 700 }}>{item.value}</span> 장의 사진
        </div>
      </div>
    );
  }
  return null;
};

export function AnalyticsView() {
  const { data: stats, isLoading, isError } = useAnalyticsQuery();

  if (isLoading) {
    return <LoadingSpinner fullScreen message="장비 메타데이터 및 분석 통계를 계산하는 중입니다..." />;
  }

  if (isError || !stats) {
    return (
      <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#ef4444', height: '100vh', backgroundColor: '#09090b' }}>
        통계 데이터를 불러오는 도중 오류가 발생했습니다.
      </div>
    );
  }

  return (
    <div style={{
      flex: 1,
      height: '100vh',
      overflowY: 'auto',
      backgroundColor: '#09090b',
      color: '#f4f4f5',
      padding: '32px 40px',
      boxSizing: 'border-box'
    }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ margin: '0 0 8px 0', fontSize: '26px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <BarChart3 size={28} color="#38bdf8" /> Gear Analytics & Insights
        </h1>
        <p style={{ margin: 0, color: '#a1a1aa', fontSize: '14px' }}>
          수집된 메타데이터를 기반으로 촬영 습관, 선호하는 카메라/렌즈 및 EXIF 세팅 분포를 시각화합니다.
        </p>
      </div>

      {/* Summary KPI Cards */}
      <AnalyticsKpiGrid stats={stats} />

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px', marginBottom: '40px' }}>
        <GearDonutCharts
          cameras={stats.cameras}
          lenses={stats.lenses}
          colors={COLORS}
          customTooltip={CustomTooltip}
        />
        <ExifBarCharts
          focal_lengths={stats.focal_lengths}
          focal_lengths_35mm={stats.focal_lengths_35mm}
          apertures={stats.apertures}
          customTooltip={CustomTooltip}
        />
      </div>
    </div>
  );
}
