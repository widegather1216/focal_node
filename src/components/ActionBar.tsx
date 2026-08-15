import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, X } from 'lucide-react';
import { open } from '@tauri-apps/plugin-dialog';
import { useAppStore } from '../store/useAppStore';
import { api } from '../services/api';

export function ActionBar() {
  const { apiPort, selectedPhotoIds, clearSelection } = useAppStore();
  const [exporting, setExporting] = useState(false);
  const [exportMessage, setExportMessage] = useState<string | null>(null);

  if (selectedPhotoIds.size === 0) return null;

  const handleExport = async () => {
    if (!apiPort) return;
    
    try {
      const selectedDir = await open({
        directory: true,
        multiple: false,
        title: "사진을 내보낼 대상 폴더를 선택하세요"
      });
      
      if (!selectedDir) return;
      
      const targetFolder = Array.isArray(selectedDir) ? selectedDir[0] : selectedDir;
      if (!targetFolder) return;

      setExporting(true);
      setExportMessage(null);
      
      try {
        const data = await api.exportPhotos(Array.from(selectedPhotoIds), targetFolder);
        setExportMessage(`${data.exported_count}장의 사진 내보내기 완료 ✅`);
        setTimeout(() => {
          clearSelection();
          setExportMessage(null);
        }, 1800);
      } catch (err: any) {
        setExportMessage(`내보내기 실패: ${err.message || '오류'}`);
        setTimeout(() => setExportMessage(null), 3000);
      }
    } catch (err) {
      console.error("Export error:", err);
      setExportMessage("내보내기 도중 오류가 발생했습니다.");
      setTimeout(() => setExportMessage(null), 3000);
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
          backgroundColor: '#1c1917',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          color: '#fff',
          padding: '10px 20px',
          borderRadius: '32px',
          display: 'flex',
          alignItems: 'center',
          gap: '20px',
          boxShadow: '0 12px 36px rgba(0,0,0,0.6)',
          zIndex: 50,
          backdropFilter: 'blur(12px)'
        }}
      >
        <span style={{ fontWeight: 600, fontSize: '13px', color: '#f4f4f5' }}>
          {exportMessage || `${selectedPhotoIds.size}장의 사진 선택됨`}
        </span>
        
        {!exportMessage && (
          <div style={{ display: 'flex', gap: '8px' }}>
            <motion.button
              onClick={handleExport}
              disabled={exporting}
              whileHover={exporting ? {} : { 
                scale: 1.03, 
                backgroundColor: '#22c55e', 
                boxShadow: '0 0 12px rgba(34, 197, 94, 0.4)' 
              }}
              whileTap={exporting ? {} : { scale: 0.97 }}
              transition={{ type: "spring", stiffness: 400, damping: 15 }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: '#16a34a',
                color: '#fff',
                border: 'none',
                padding: '7px 16px',
                borderRadius: '20px',
                cursor: exporting ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: '13px'
              }}
            >
              <Download size={15} />
              {exporting ? '내보내는 중...' : '내보내기 (Export)'}
            </motion.button>
            
            <motion.button
              onClick={clearSelection}
              whileHover={{ scale: 1.1, backgroundColor: '#3f3f46' }}
              whileTap={{ scale: 0.9 }}
              transition={{ type: "spring", stiffness: 500, damping: 15 }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#27272a',
                color: '#a1a1aa',
                border: 'none',
                padding: '7px',
                borderRadius: '50%',
                cursor: 'pointer'
              }}
              title="선택 해제"
            >
              <X size={15} />
            </motion.button>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
