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
      <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', gap: '8px' }}>
          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
            <Focus size={16} color="var(--accent-focal)" style={{ flexShrink: 0 }} />
            <span style={{ whiteSpace: 'nowrap' }}>화각 선호도</span>
          </h3>
          <div style={{ display: 'flex', gap: '2px', backgroundColor: 'var(--bg-canvas)', padding: '2px', borderRadius: '6px', border: '1px solid var(--border-subtle)', flexShrink: 0 }}>
            <button
              onClick={() => setUse35mmMode(true)}
              style={{
                backgroundColor: use35mmMode ? 'var(--bg-elevated)' : 'transparent',
                color: use35mmMode ? 'var(--text-primary)' : 'var(--text-secondary)',
                border: 'none',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              35mm 환산
            </button>
            <button
              onClick={() => setUse35mmMode(false)}
              style={{
                backgroundColor: !use35mmMode ? 'var(--bg-elevated)' : 'transparent',
                color: !use35mmMode ? 'var(--text-primary)' : 'var(--text-secondary)',
                border: 'none',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              실제 화각
            </button>
          </div>
        </div>
        <div style={{ width: '100%', height: '300px' }}>
          {activeFocalLengths && activeFocalLengths.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={activeFocalLengths} margin={{ top: 10, right: 10, bottom: 20, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" fill="var(--accent-focal)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              화각 메타데이터가 존재하지 않습니다.
            </div>
          )}
        </div>
      </div>

      {/* Aperture Bar Chart */}
      <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ margin: '0 0 18px 0', fontSize: '14px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
          <Aperture size={16} color="var(--accent-focal)" style={{ flexShrink: 0 }} />
          <span style={{ whiteSpace: 'nowrap' }}>조리개 사용 분포</span>
        </h3>
        <div style={{ width: '100%', height: '300px' }}>
          {apertures && apertures.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={apertures} margin={{ top: 10, right: 10, bottom: 20, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" fill="var(--text-secondary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              조리개 메타데이터가 존재하지 않습니다.
            </div>
          )}
        </div>
      </div>
    </>
  );
};
