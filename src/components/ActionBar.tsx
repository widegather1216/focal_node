import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, X, Loader2, CheckCircle2 } from 'lucide-react';
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
        setExportMessage(`${data.exported_count}장의 사진 내보내기 완료`);
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
          backgroundColor: 'rgba(18, 18, 21, 0.92)',
          border: '1px solid var(--border-subtle)',
          color: 'var(--text-primary)',
          padding: '8px 16px',
          borderRadius: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          boxShadow: '0 16px 36px rgba(0,0,0,0.7)',
          zIndex: 50,
          backdropFilter: 'blur(16px)',
          userSelect: 'none'
        }}
      >
        <span style={{ fontWeight: 500, fontSize: '12px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          {exportMessage ? (
            <>
              <CheckCircle2 size={14} color="var(--accent-focal)" style={{ flexShrink: 0 }} />
              <span>{exportMessage}</span>
            </>
          ) : (
            <>
              <span className="font-mono" style={{ fontWeight: 700, color: 'var(--accent-focal)' }}>
                {selectedPhotoIds.size}
              </span>
              <span style={{ color: 'var(--text-secondary)' }}>장의 사진 선택됨</span>
            </>
          )}
        </span>
        
        {!exportMessage && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <motion.button
              onClick={handleExport}
              disabled={exporting}
              whileHover={exporting ? {} : { 
                scale: 1.02, 
                backgroundColor: 'var(--accent-focal-hover)'
              }}
              whileTap={exporting ? {} : { scale: 0.97 }}
              transition={{ type: "spring", stiffness: 400, damping: 15 }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: 'var(--accent-focal)',
                color: '#fff',
                border: 'none',
                padding: '6px 14px',
                borderRadius: '16px',
                cursor: exporting ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                fontSize: '12px'
              }}
            >
              {exporting ? <Loader2 size={13} className="spin" /> : <Download size={13} />}
              {exporting ? '내보내는 중...' : '내보내기'}
            </motion.button>
            
            <motion.button
              onClick={clearSelection}
              whileHover={{ scale: 1.1, backgroundColor: 'var(--bg-elevated)', color: 'var(--text-primary)' }}
              whileTap={{ scale: 0.9 }}
              transition={{ type: "spring", stiffness: 500, damping: 15 }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'var(--bg-card)',
                color: 'var(--text-muted)',
                border: '1px solid var(--border-subtle)',
                padding: '6px',
                borderRadius: '50%',
                cursor: 'pointer'
              }}
              title="선택 해제"
            >
              <X size={13} />
            </motion.button>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
