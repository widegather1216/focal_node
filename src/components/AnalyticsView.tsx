import { useState } from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend
} from 'recharts';
import { Camera, Focus, Aperture, Image as ImageIcon, BarChart3 } from 'lucide-react';
import { motion } from 'framer-motion';
import { useAnalyticsQuery } from '../hooks/useAnalyticsQuery';

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
  const [use35mmMode, setUse35mmMode] = useState(true);

  if (isLoading) {
    return (
      <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#a1a1aa', height: '100vh', backgroundColor: '#09090b' }}>
        장비 메타데이터 및 분석 통계를 계산하는 중입니다...
      </div>
    );
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
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
        <motion.div
          whileHover={{ y: -2 }}
          style={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '12px', padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}
        >
          <div style={{ background: 'rgba(56, 189, 248, 0.15)', padding: '12px', borderRadius: '10px', color: '#38bdf8' }}>
            <ImageIcon size={24} />
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.05em' }}>총 수집 사진</div>
            <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '2px' }}>{stats.total_photos.toLocaleString()}</div>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -2 }}
          style={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '12px', padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}
        >
          <div style={{ background: 'rgba(129, 140, 248, 0.15)', padding: '12px', borderRadius: '10px', color: '#818cf8' }}>
            <Camera size={24} />
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.05em' }}>사용 카메라 바디</div>
            <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '2px' }}>{stats.cameras.length}종</div>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -2 }}
          style={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '12px', padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}
        >
          <div style={{ background: 'rgba(192, 132, 252, 0.15)', padding: '12px', borderRadius: '10px', color: '#c084fc' }}>
            <Focus size={24} />
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.05em' }}>사용 렌즈 라인업</div>
            <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '2px' }}>{stats.lenses.length}종</div>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -2 }}
          style={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '12px', padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}
        >
          <div style={{ background: 'rgba(74, 222, 128, 0.15)', padding: '12px', borderRadius: '10px', color: '#4ade80' }}>
            <Aperture size={24} />
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.05em' }}>최다 활용 조리개</div>
            <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px' }}>
              {stats.apertures[0]?.name || 'N/A'}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px', marginBottom: '40px' }}>
        {/* Camera Donut Chart */}
        <div style={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Camera size={18} color="#38bdf8" /> 카메라 바디 사용 점유율
          </h3>
          <div style={{ width: '100%', height: '320px' }}>
            {stats.cameras.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                  <Pie
                    data={stats.cameras}
                    cx="50%"
                    cy="42%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={4}
                    dataKey="count"
                  >
                    {stats.cameras.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend
                    layout="horizontal"
                    verticalAlign="bottom"
                    align="center"
                    formatter={(value: string) => value.length > 18 ? `${value.substring(0, 18)}...` : value}
                    wrapperStyle={{ fontSize: '12px', paddingTop: '16px', color: '#a1a1aa' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#71717a' }}>
                카메라 메타데이터가 존재하지 않습니다.
              </div>
            )}
          </div>
        </div>

        {/* Lens Donut Chart */}
        <div style={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Focus size={18} color="#c084fc" /> 렌즈 모델 점유율
          </h3>
          <div style={{ width: '100%', height: '320px' }}>
            {stats.lenses.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                  <Pie
                    data={stats.lenses}
                    cx="50%"
                    cy="42%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={4}
                    dataKey="count"
                  >
                    {stats.lenses.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[(index + 2) % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend
                    layout="horizontal"
                    verticalAlign="bottom"
                    align="center"
                    formatter={(value: string) => value.length > 18 ? `${value.substring(0, 18)}...` : value}
                    wrapperStyle={{ fontSize: '12px', paddingTop: '16px', color: '#a1a1aa' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#71717a' }}>
                렌즈 메타데이터가 존재하지 않습니다.
              </div>
            )}
          </div>
        </div>

        {/* Focal Length Bar Chart */}
        <div style={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Focus size={18} color="#818cf8" /> 화각 (Focal Length) 선호도
            </h3>
            <div style={{ display: 'flex', gap: '4px', background: '#09090b', padding: '3px', borderRadius: '6px', border: '1px solid #27272a' }}>
              <button
                onClick={() => setUse35mmMode(true)}
                style={{
                  background: use35mmMode ? '#27272a' : 'transparent',
                  color: use35mmMode ? '#38bdf8' : '#a1a1aa',
                  border: 'none',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                35mm 환산
              </button>
              <button
                onClick={() => setUse35mmMode(false)}
                style={{
                  background: !use35mmMode ? '#27272a' : 'transparent',
                  color: !use35mmMode ? '#38bdf8' : '#a1a1aa',
                  border: 'none',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                실제 화각
              </button>
            </div>
          </div>
          <div style={{ width: '100%', height: '280px' }}>
            {((use35mmMode && stats.focal_lengths_35mm?.length > 0) ? stats.focal_lengths_35mm : stats.focal_lengths).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={(use35mmMode && stats.focal_lengths_35mm?.length > 0) ? stats.focal_lengths_35mm : stats.focal_lengths}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="name" stroke="#a1a1aa" fontSize={12} />
                  <YAxis stroke="#a1a1aa" fontSize={12} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" fill="#818cf8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#71717a' }}>
                화각 데이터가 존재하지 않습니다.
              </div>
            )}
          </div>
        </div>

        {/* Aperture Bar Chart */}
        <div style={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 20px 0', fontSize: '16px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Aperture size={18} color="#4ade80" /> 조리개 (Aperture) 사용 분포
          </h3>
          <div style={{ width: '100%', height: '280px' }}>
            {stats.apertures.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.apertures}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="name" stroke="#a1a1aa" fontSize={12} />
                  <YAxis stroke="#a1a1aa" fontSize={12} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" fill="#4ade80" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#71717a' }}>
                조리개 데이터가 존재하지 않습니다.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
