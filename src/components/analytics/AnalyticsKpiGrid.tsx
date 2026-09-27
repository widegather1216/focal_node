import React from 'react';
import { motion } from 'framer-motion';
import { Camera, Focus, Aperture, Image as ImageIcon } from 'lucide-react';

interface AnalyticsKpiGridProps {
  stats: {
    total_photos: number;
    cameras: any[];
    lenses: any[];
    apertures: any[];
  };
}

export const AnalyticsKpiGrid: React.FC<AnalyticsKpiGridProps> = ({ stats }) => {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px', marginBottom: '28px' }}>
      <motion.div
        whileHover={{ y: -2 }}
        style={kpiCardStyle}
      >
        <div style={iconBoxStyle}>
          <ImageIcon size={18} color="var(--accent-focal)" style={{ flexShrink: 0 }} />
        </div>
        <div style={{ minWidth: 0, overflow: 'hidden' }}>
          <div style={kpiLabelStyle}>총 사진 수</div>
          <div className="font-mono" style={kpiValueStyle}>{stats.total_photos.toLocaleString()}</div>
        </div>
      </motion.div>

      <motion.div
        whileHover={{ y: -2 }}
        style={kpiCardStyle}
      >
        <div style={iconBoxStyle}>
          <Camera size={18} color="var(--text-secondary)" style={{ flexShrink: 0 }} />
        </div>
        <div style={{ minWidth: 0, overflow: 'hidden' }}>
          <div style={kpiLabelStyle}>카메라 기종</div>
          <div className="font-mono" style={kpiValueStyle}>{stats.cameras.length}종</div>
        </div>
      </motion.div>

      <motion.div
        whileHover={{ y: -2 }}
        style={kpiCardStyle}
      >
        <div style={iconBoxStyle}>
          <Focus size={18} color="var(--text-secondary)" style={{ flexShrink: 0 }} />
        </div>
        <div style={{ minWidth: 0, overflow: 'hidden' }}>
          <div style={kpiLabelStyle}>렌즈 라인업</div>
          <div className="font-mono" style={kpiValueStyle}>{stats.lenses.length}종</div>
        </div>
      </motion.div>

      <motion.div
        whileHover={{ y: -2 }}
        style={kpiCardStyle}
      >
        <div style={iconBoxStyle}>
          <Aperture size={18} color="var(--accent-focal)" style={{ flexShrink: 0 }} />
        </div>
        <div style={{ minWidth: 0, overflow: 'hidden' }}>
          <div style={kpiLabelStyle}>최다 활용 조리개</div>
          <div className="font-mono" style={{ ...kpiValueStyle, fontSize: '18px' }}>
            {stats.apertures[0]?.name || 'N/A'}
          </div>
        </div>
      </motion.div>
    </div>
  );
};

const kpiCardStyle = {
  backgroundColor: 'var(--bg-card)',
  border: '1px solid var(--border-subtle)',
  borderRadius: '8px',
  padding: '14px 16px',
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  transition: 'border-color 0.15s ease'
};

const iconBoxStyle = {
  backgroundColor: 'var(--bg-surface)',
  border: '1px solid var(--border-subtle)',
  padding: '9px',
  borderRadius: '6px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0
};

const kpiLabelStyle = {
  fontSize: '11px',
  color: 'var(--text-muted)',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.04em',
  fontWeight: 600,
  whiteSpace: 'nowrap' as const,
  overflow: 'hidden',
  textOverflow: 'ellipsis'
};

const kpiValueStyle = {
  fontSize: '18px',
  fontWeight: 700,
  marginTop: '2px',
  color: 'var(--text-primary)',
  whiteSpace: 'nowrap' as const
};
