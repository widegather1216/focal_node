import React from 'react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';
import { Camera, Focus } from 'lucide-react';

interface GearDonutChartsProps {
  cameras: any[];
  lenses: any[];
  colors: string[];
  customTooltip: React.ComponentType<any>;
}

export const GearDonutCharts: React.FC<GearDonutChartsProps> = ({
  cameras,
  lenses,
  colors,
  customTooltip: CustomTooltip
}) => {
  return (
    <>
      {/* Camera Donut Chart */}
      <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '14px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
          <Camera size={16} color="var(--accent-focal)" style={{ flexShrink: 0 }} />
          <span style={{ whiteSpace: 'nowrap' }}>카메라 바디 사용 점유율</span>
        </h3>
        <div style={{ width: '100%', height: '300px' }}>
          {cameras.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                <Pie
                  data={cameras}
                  cx="50%"
                  cy="42%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="count"
                >
                  {cameras.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  layout="horizontal"
                  verticalAlign="bottom"
                  align="center"
                  formatter={(value: string) => value.length > 18 ? `${value.substring(0, 18)}...` : value}
                  wrapperStyle={{ fontSize: '11px', paddingTop: '16px', color: 'var(--text-secondary)' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              카메라 메타데이터가 존재하지 않습니다.
            </div>
          )}
        </div>
      </div>

      {/* Lens Donut Chart */}
      <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '14px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
          <Focus size={16} color="var(--accent-focal)" style={{ flexShrink: 0 }} />
          <span style={{ whiteSpace: 'nowrap' }}>렌즈 모델 점유율</span>
        </h3>
        <div style={{ width: '100%', height: '300px' }}>
          {lenses.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                <Pie
                  data={lenses}
                  cx="50%"
                  cy="42%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="count"
                >
                  {lenses.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  layout="horizontal"
                  verticalAlign="bottom"
                  align="center"
                  formatter={(value: string) => value.length > 18 ? `${value.substring(0, 18)}...` : value}
                  wrapperStyle={{ fontSize: '11px', paddingTop: '16px', color: 'var(--text-secondary)' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              렌즈 메타데이터가 존재하지 않습니다.
            </div>
          )}
        </div>
      </div>
    </>
  );
};
