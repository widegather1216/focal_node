import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface FullscreenNavigationProps {
  isVisible: boolean;
  onPrevPhoto: () => void;
  onNextPhoto: () => void;
}

const navButtonBaseStyle: React.CSSProperties = {
  position: 'absolute',
  top: '50%',
  transform: 'translateY(-50%)',
  background: 'rgba(24, 24, 27, 0.6)',
  backdropFilter: 'blur(8px)',
  border: '1px solid rgba(63, 63, 70, 0.6)',
  color: '#fff',
  borderRadius: '50%',
  padding: '14px',
  cursor: 'pointer',
  zIndex: 130,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  boxShadow: '0 8px 25px rgba(0,0,0,0.5)',
  transition: 'opacity 0.2s, background-color 0.2s',
};

export const FullscreenNavigation: React.FC<FullscreenNavigationProps> = ({
  isVisible,
  onPrevPhoto,
  onNextPhoto,
}) => {
  return (
    <AnimatePresence>
      {isVisible && (
        <>
          <motion.button
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 0.8, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            whileHover={{ scale: 1.15, opacity: 1, backgroundColor: 'rgba(24, 24, 27, 0.95)' }}
            whileTap={{ scale: 0.9 }}
            onClick={(event) => {
              event.stopPropagation();
              onPrevPhoto();
            }}
            style={{ ...navButtonBaseStyle, left: '24px' }}
            title="이전 사진 (←)"
          >
            <ChevronLeft size={24} />
          </motion.button>

          <motion.button
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 0.8, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            whileHover={{ scale: 1.15, opacity: 1, backgroundColor: 'rgba(24, 24, 27, 0.95)' }}
            whileTap={{ scale: 0.9 }}
            onClick={(event) => {
              event.stopPropagation();
              onNextPhoto();
            }}
            style={{ ...navButtonBaseStyle, right: '24px' }}
            title="다음 사진 (→)"
          >
            <ChevronRight size={24} />
          </motion.button>
        </>
      )}
    </AnimatePresence>
  );
};
