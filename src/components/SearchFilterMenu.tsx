import { useState } from 'react';
import { useAppStore, SearchFilters } from '../store/useAppStore';
import { SlidersHorizontal, X } from 'lucide-react';
import { motion } from 'framer-motion';

export function SearchFilterMenu() {
  const { searchFilters, setSearchFilters, clearSearchFilters } = useAppStore();
  const [isOpen, setIsOpen] = useState(false);

  const [localFilters, setLocalFilters] = useState<SearchFilters>(searchFilters);

  const handleApply = () => {
    const cleaned: SearchFilters = {};
    if (localFilters.camera_model) cleaned.camera_model = localFilters.camera_model;
    if (localFilters.lens_model) cleaned.lens_model = localFilters.lens_model;
    if (localFilters.iso_min) cleaned.iso_min = Number(localFilters.iso_min);
    if (localFilters.iso_max) cleaned.iso_max = Number(localFilters.iso_max);
    if (localFilters.f_number_min) cleaned.f_number_min = Number(localFilters.f_number_min);
    if (localFilters.f_number_max) cleaned.f_number_max = Number(localFilters.f_number_max);
    if (localFilters.focal_length_min) cleaned.focal_length_min = Number(localFilters.focal_length_min);
    if (localFilters.focal_length_max) cleaned.focal_length_max = Number(localFilters.focal_length_max);
    if (localFilters.date_from) cleaned.date_from = localFilters.date_from;
    if (localFilters.date_to) cleaned.date_to = localFilters.date_to;

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
        whileHover={{ 
          scale: 1.08, 
          y: -1,
          backgroundColor: activeFilterCount > 0 ? 'rgba(74, 222, 128, 0.25)' : 'rgba(255, 255, 255, 0.08)' 
        }}
        whileTap={{ scale: 0.9 }}
        transition={{ type: "spring", stiffness: 500, damping: 15 }}
        style={{
          backgroundColor: activeFilterCount > 0 ? 'rgba(74, 222, 128, 0.2)' : 'rgba(255, 255, 255, 0.05)',
          border: `1px solid ${activeFilterCount > 0 ? '#4ade80' : 'rgba(255, 255, 255, 0.2)'}`,
          boxShadow: activeFilterCount > 0 ? '0 0 10px rgba(74, 222, 128, 0.35)' : 'none',
          borderRadius: '8px',
          padding: '8px',
          color: activeFilterCount > 0 ? '#4ade80' : '#aaa',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '34px',
          width: '34px',
          outline: 'none',
        }}
        title="Filter"
      >
        <SlidersHorizontal size={16} />
      </motion.button>

      {isOpen && (
        <>
          <div 
            onClick={() => setIsOpen(false)}
            style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 99 }}
          />
          <div style={{
            position: 'absolute',
            top: '40px',
            left: 0,
            width: '240px',
            backgroundColor: '#222',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '8px',
            padding: '16px',
            zIndex: 100,
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#fff' }}>Filters</span>
              <motion.button 
                onClick={() => setIsOpen(false)} 
                whileHover={{ scale: 1.15, color: '#fff' }}
                whileTap={{ scale: 0.9 }}
                transition={{ type: "spring", stiffness: 500, damping: 15 }}
                style={{ background: 'none', border: 'none', color: '#aaa', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <X size={16} />
              </motion.button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '12px', color: '#aaa' }}>Camera Model</label>
              <input type="text" value={localFilters.camera_model || ''} onChange={e => setLocalFilters({...localFilters, camera_model: e.target.value})} style={inputStyle} placeholder="e.g. ILCE-7RM3" />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '12px', color: '#aaa' }}>Lens Model</label>
              <input type="text" value={localFilters.lens_model || ''} onChange={e => setLocalFilters({...localFilters, lens_model: e.target.value})} style={inputStyle} placeholder="e.g. FE 50mm F1.2 GM" />
            </div>

            <div style={{ display: 'flex', flexDirection: 'row', gap: '8px' }}>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', color: '#aaa' }}>ISO Min</label>
                <input type="number" value={localFilters.iso_min || ''} onChange={e => setLocalFilters({...localFilters, iso_min: parseInt(e.target.value) || undefined})} style={inputStyle} />
              </div>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', color: '#aaa' }}>ISO Max</label>
                <input type="number" value={localFilters.iso_max || ''} onChange={e => setLocalFilters({...localFilters, iso_max: parseInt(e.target.value) || undefined})} style={inputStyle} />
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'row', gap: '8px' }}>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', color: '#aaa' }}>f/ Min</label>
                <input type="number" step="0.1" value={localFilters.f_number_min || ''} onChange={e => setLocalFilters({...localFilters, f_number_min: parseFloat(e.target.value) || undefined})} style={inputStyle} />
              </div>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', color: '#aaa' }}>f/ Max</label>
                <input type="number" step="0.1" value={localFilters.f_number_max || ''} onChange={e => setLocalFilters({...localFilters, f_number_max: parseFloat(e.target.value) || undefined})} style={inputStyle} />
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'row', gap: '8px' }}>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', color: '#aaa' }}>Focal Length Min (mm)</label>
                <input type="number" step="0.1" value={localFilters.focal_length_min || ''} onChange={e => setLocalFilters({...localFilters, focal_length_min: parseFloat(e.target.value) || undefined})} style={inputStyle} />
              </div>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', color: '#aaa' }}>Focal Length Max (mm)</label>
                <input type="number" step="0.1" value={localFilters.focal_length_max || ''} onChange={e => setLocalFilters({...localFilters, focal_length_max: parseFloat(e.target.value) || undefined})} style={inputStyle} />
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '12px', color: '#aaa' }}>From Date</label>
              <input type="date" value={localFilters.date_from || ''} onChange={e => setLocalFilters({...localFilters, date_from: e.target.value})} style={inputStyle} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '12px', color: '#aaa' }}>To Date</label>
              <input type="date" value={localFilters.date_to || ''} onChange={e => setLocalFilters({...localFilters, date_to: e.target.value})} style={inputStyle} />
            </div>

            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              <motion.button 
                onClick={handleClear} 
                whileHover={{ backgroundColor: 'rgba(255, 255, 255, 0.08)', borderColor: '#fff', color: '#fff' }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: "spring", stiffness: 400, damping: 15 }}
                style={{ flex: 1, padding: '8px', borderRadius: '6px', backgroundColor: 'transparent', border: '1px solid #aaa', color: '#ccc', cursor: 'pointer' }}
              >
                Clear
              </motion.button>
              <motion.button 
                onClick={handleApply} 
                whileHover={{ scale: 1.02, backgroundColor: '#f0f0f0', boxShadow: '0 0 8px rgba(255, 255, 255, 0.25)' }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: "spring", stiffness: 400, damping: 15 }}
                style={{ flex: 1, padding: '8px', borderRadius: '6px', backgroundColor: '#fff', border: 'none', color: '#000', cursor: 'pointer', fontWeight: 'bold' }}
              >
                Apply
              </motion.button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

const inputStyle = {
  backgroundColor: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid rgba(255, 255, 255, 0.2)',
  borderRadius: '4px',
  padding: '6px',
  color: '#fff',
  fontSize: '12px',
  outline: 'none',
  width: '100%',
  boxSizing: 'border-box' as const
};
