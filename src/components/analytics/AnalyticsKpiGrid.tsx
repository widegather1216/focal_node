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
  );
};
