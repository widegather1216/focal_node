import { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { SearchFilters } from '../types/photo';
import { SlidersHorizontal, X } from 'lucide-react';
import { motion } from 'framer-motion';
import { FilterRangeInput } from './filter/FilterRangeInput';

function parseNumericValue(val: string): number | undefined {
  const trimmed = val.trim();
  if (trimmed === '') return undefined;
  const num = Number(trimmed);
  return isNaN(num) ? undefined : num;
}

export function SearchFilterMenu() {
  const { searchFilters, setSearchFilters, clearSearchFilters } = useAppStore();
  const [isOpen, setIsOpen] = useState(false);
  const [localFilters, setLocalFilters] = useState<SearchFilters>(searchFilters);

  const handleApply = () => {
    const cleaned: SearchFilters = Object.fromEntries(
      Object.entries(localFilters).filter(([_, v]) => v !== undefined && v !== '' && !Number.isNaN(v))
    );
    setSearchFilters(cleaned);
    setIsOpen(false);
  };

  const handleClear = () => {
    setLocalFilters({});
    clearSearchFilters();
    setIsOpen(false);
  };

  const activeFilterCount = Object.keys(searchFilters).length;

  return (
    <div style={{ position: 'relative' }}>
      <motion.button
        onClick={() => {
          setLocalFilters(searchFilters);
          setIsOpen(!isOpen);
        }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.92 }}
        transition={{ type: "spring", stiffness: 500, damping: 15 }}
        style={{
          backgroundColor: activeFilterCount > 0 ? 'var(--accent-focal-subtle)' : 'var(--bg-card)',
          border: `1px solid ${activeFilterCount > 0 ? 'var(--accent-focal)' : 'var(--border-subtle)'}`,
          boxShadow: activeFilterCount > 0 ? '0 0 10px rgba(225, 29, 72, 0.35)' : 'none',
          borderRadius: '6px',
          padding: '7px',
          color: activeFilterCount > 0 ? 'var(--accent-focal)' : 'var(--text-secondary)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '32px',
          width: '32px',
          outline: 'none',
          position: 'relative'
        }}
        title="EXIF 하이브리드 필터"
      >
        <SlidersHorizontal size={14} />
        {activeFilterCount > 0 && (
          <span style={{
            position: 'absolute',
            top: '-3px',
            right: '-3px',
            backgroundColor: 'var(--accent-focal)',
            color: '#fff',
            fontSize: '9px',
            fontWeight: 700,
            borderRadius: '50%',
            width: '14px',
            height: '14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: 'var(--font-mono)'
          }}>
            {activeFilterCount}
          </span>
        )}
      </motion.button>

      {isOpen && (
        <>
          <div 
            onClick={() => setIsOpen(false)}
            style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 99 }}
          />
          <div style={{
            position: 'absolute',
            top: '38px',
            left: 0,
            width: '260px',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '8px',
            padding: '14px',
            zIndex: 100,
            boxShadow: '0 16px 36px rgba(0,0,0,0.85)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                EXIF 필터
              </span>
              <motion.button 
                onClick={() => setIsOpen(false)} 
                whileHover={{ scale: 1.15, color: 'var(--text-primary)' }}
                whileTap={{ scale: 0.9 }}
                transition={{ type: "spring", stiffness: 500, damping: 15 }}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px' }}
              >
                <X size={14} />
              </motion.button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>카메라 바디</label>
              <input 
                type="text" 
                value={localFilters.camera_model || ''} 
                onChange={e => setLocalFilters({...localFilters, camera_model: e.target.value})} 
                style={inputStyle} 
                placeholder="예: ILCE-7M4, Canon R5" 
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>렌즈 기종</label>
              <input 
                type="text" 
                value={localFilters.lens_model || ''} 
                onChange={e => setLocalFilters({...localFilters, lens_model: e.target.value})} 
                style={inputStyle} 
                placeholder="예: FE 24-70mm F2.8 GM II" 
              />
            </div>

            <FilterRangeInput
              label="ISO 범위"
              minValue={localFilters.iso_min ?? ''}
              maxValue={localFilters.iso_max ?? ''}
              onMinChange={val => setLocalFilters({...localFilters, iso_min: parseNumericValue(val)})}
              onMaxChange={val => setLocalFilters({...localFilters, iso_max: parseNumericValue(val)})}
            />

            <FilterRangeInput
              label="조리개 (ƒ/)"
              minValue={localFilters.f_number_min ?? ''}
              maxValue={localFilters.f_number_max ?? ''}
              onMinChange={val => setLocalFilters({...localFilters, f_number_min: parseNumericValue(val)})}
              onMaxChange={val => setLocalFilters({...localFilters, f_number_max: parseNumericValue(val)})}
            />

            <FilterRangeInput
              label="화각 (mm)"
              minValue={localFilters.focal_length_min ?? ''}
              maxValue={localFilters.focal_length_max ?? ''}
              onMinChange={val => setLocalFilters({...localFilters, focal_length_min: parseNumericValue(val)})}
              onMaxChange={val => setLocalFilters({...localFilters, focal_length_max: parseNumericValue(val)})}
            />

            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>시작 날짜</label>
              <input type="date" value={localFilters.date_from || ''} onChange={e => setLocalFilters({...localFilters, date_from: e.target.value})} style={inputStyle} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>종료 날짜</label>
              <input type="date" value={localFilters.date_to || ''} onChange={e => setLocalFilters({...localFilters, date_to: e.target.value})} style={inputStyle} />
            </div>

            <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
              <motion.button 
                onClick={handleClear} 
                whileHover={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-primary)' }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: "spring", stiffness: 400, damping: 15 }}
                style={{
                  flex: 1,
                  padding: '7px',
                  borderRadius: '6px',
                  backgroundColor: 'transparent',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                초기화
              </motion.button>
              <motion.button 
                onClick={handleApply} 
                whileHover={{ scale: 1.02, backgroundColor: 'var(--accent-focal-hover)' }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: "spring", stiffness: 400, damping: 15 }}
                style={{
                  flex: 1,
                  padding: '7px',
                  borderRadius: '6px',
                  backgroundColor: 'var(--accent-focal)',
                  border: 'none',
                  color: '#fff',
                  fontSize: '12px',
                  cursor: 'pointer',
                  fontWeight: 600
                }}
              >
                필터 적용
              </motion.button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

const inputStyle = {
  backgroundColor: 'var(--bg-card)',
  border: '1px solid var(--border-subtle)',
  borderRadius: '4px',
  padding: '5px 8px',
  color: 'var(--text-primary)',
  fontSize: '12px',
  outline: 'none',
  width: '100%',
  boxSizing: 'border-box' as const
};
