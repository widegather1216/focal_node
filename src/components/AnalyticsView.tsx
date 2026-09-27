import { BarChart3 } from 'lucide-react';
import { useAnalyticsQuery } from '../hooks/useAnalyticsQuery';
import { LoadingSpinner } from './common/LoadingSpinner';
import { AnalyticsKpiGrid } from './analytics/AnalyticsKpiGrid';
import { GearDonutCharts } from './analytics/GearDonutCharts';
import { ExifBarCharts } from './analytics/ExifBarCharts';

const MONOCHROME_ACCENT_COLORS = [
  '#e11d48', '#f43f5e', '#fb7185', '#e4e4e7', '#d4d4d8',
  '#a1a1aa', '#71717a', '#52525b', '#3f3f46', '#27272a'
];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const item = payload[0];
    return (
      <div style={{
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '6px',
        padding: '8px 12px',
        color: 'var(--text-primary)',
        boxShadow: '0 12px 28px rgba(0,0,0,0.7)',
        fontSize: '12px'
      }}>
        <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '3px' }}>
          {label || item.name}
        </div>
        <div style={{ color: item.color || 'var(--accent-focal)', display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span className="font-mono" style={{ fontSize: '13px', fontWeight: 700 }}>{item.value}</span>
          <span style={{ color: 'var(--text-muted)' }}>장의 사진</span>
        </div>
      </div>
    );
  }
  return null;
};

export function AnalyticsView() {
  const { data: stats, isLoading, isError } = useAnalyticsQuery();

  if (isLoading) {
    return <LoadingSpinner fullScreen message="장비 메타데이터 및 분석 통계를 집계하는 중입니다..." />;
  }

  if (isError || !stats) {
    return (
      <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'var(--accent-focal)', height: '100vh', backgroundColor: 'var(--bg-canvas)' }}>
        통계 데이터를 불러오는 도중 오류가 발생했습니다.
      </div>
    );
  }

  return (
    <div style={{
      flex: 1,
      height: '100vh',
      overflowY: 'auto',
      backgroundColor: 'var(--bg-canvas)',
      color: 'var(--text-primary)',
      padding: '24px 32px',
      boxSizing: 'border-box'
    }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ margin: '0 0 6px 0', fontSize: '20px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px', letterSpacing: '-0.02em' }}>
          <BarChart3 size={22} color="var(--accent-focal)" /> 장비 사용 통계 & 인사이트
        </h1>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '13px' }}>
          수집된 메타데이터를 기반으로 촬영 습관, 선호하는 카메라 바디/렌즈 및 조리개·화각 분포를 시각화합니다.
        </p>
      </div>

      {/* Summary KPI Cards */}
      <AnalyticsKpiGrid stats={stats} />

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', marginBottom: '32px' }}>
        <GearDonutCharts
          cameras={stats.cameras}
          lenses={stats.lenses}
          colors={MONOCHROME_ACCENT_COLORS}
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
