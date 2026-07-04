import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, X } from 'lucide-react';
import { open } from '@tauri-apps/plugin-dialog';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';

export function ActionBar() {
  const { apiPort, selectedPhotoIds, clearSelection } = useAppStore();
  const [exporting, setExporting] = useState(false);

  if (selectedPhotoIds.size === 0) return null;

  const handleExport = async () => {
    if (!apiPort) return;
    
    try {
      const selectedDir = await open({
        directory: true,
        multiple: false,
        title: "Select Destination Folder for Export"
      });
      
      if (!selectedDir) return;
      
      // Ensure selectedDir is string (Tauri API can return string[] if multiple is true, but we set false)
      const targetFolder = Array.isArray(selectedDir) ? selectedDir[0] : selectedDir;
      
      setExporting(true);
      
      try {
        const data = await api.exportPhotos(Array.from(selectedPhotoIds), targetFolder);
        alert(`Successfully exported ${data.exported_count} photos.`);
        clearSelection();
      } catch (err: any) {
        alert(err.message || "Failed to export photos.");
      }
    } catch (err) {
      console.error("Export error:", err);
      alert("Error during export.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ y: 100, opacity: 0, x: '-50%' }}
        animate={{ y: 0, opacity: 1, x: '-50%' }}
        exit={{ y: 100, opacity: 0, x: '-50%' }}
        style={{
          position: 'fixed',
          bottom: '24px',
          left: '50%',
          backgroundColor: '#333',
          color: '#fff',
          padding: '12px 24px',
          borderRadius: '32px',
          display: 'flex',
          alignItems: 'center',
          gap: '24px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          zIndex: 50
        }}
      >
        <span style={{ fontWeight: 500 }}>{selectedPhotoIds.size} items selected</span>
        
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={handleExport}
            disabled={exporting}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: '#4CAF50', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '20px', cursor: 'pointer', fontWeight: 500 }}
          >
            <Download size={16} />
            {exporting ? 'Exporting...' : 'Export'}
          </button>
          
          <button
            onClick={clearSelection}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#555', color: '#fff', border: 'none', padding: '8px', borderRadius: '50%', cursor: 'pointer' }}
          >
            <X size={16} />
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
