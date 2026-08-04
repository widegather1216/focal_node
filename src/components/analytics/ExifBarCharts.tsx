import React, { useState } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { Focus, Aperture } from 'lucide-react';

interface ExifBarChartsProps {
  focal_lengths: any[];
  focal_lengths_35mm: any[];
  apertures: any[];
  customTooltip: React.ComponentType<any>;
}

export const ExifBarCharts: React.FC<ExifBarChartsProps> = ({
  focal_lengths,
  focal_lengths_35mm,
  apertures,
  customTooltip: CustomTooltip
}) => {
  const [use35mmMode, setUse35mmMode] = useState(true);
  const activeFocalLengths = (use35mmMode && focal_lengths_35mm?.length > 0) ? focal_lengths_35mm : focal_lengths;

  return (
    <>
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
          {activeFocalLengths.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={activeFocalLengths}>
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
          {apertures.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={apertures}>
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
    </>
  );
};
