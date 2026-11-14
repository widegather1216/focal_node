import { motion } from 'framer-motion';
import { Heart, Search } from 'lucide-react';
import { SearchFilters } from '../../types/photo';
import { SearchFilterMenu } from '../SearchFilterMenu';

interface SidebarSearchControlsProps {
  searchQuery: string;
  searchFilters: SearchFilters;
  onSearchQueryChange: (query: string) => void;
  onSearchFiltersChange: (filters: SearchFilters) => void;
}

export function SidebarSearchControls({
  searchQuery,
  searchFilters,
  onSearchQueryChange,
  onSearchFiltersChange,
}: SidebarSearchControlsProps) {
  const isFavoriteActive = Boolean(searchFilters.is_favorite);

  return (
    <div style={{ display: 'flex', gap: '6px', marginBottom: '14px' }}>
      <div style={{ position: 'relative', flex: 1 }}>
        <Search
          size={14}
          style={{
            position: 'absolute',
            left: '10px',
            top: '50%',
            transform: 'translateY(-50%)',
            color: 'var(--text-muted)',
          }}
        />
        <input
          type="text"
          placeholder="자연어 / 무드 검색..."
          value={searchQuery}
          onChange={(event) => onSearchQueryChange(event.target.value)}
          style={{
            width: '100%',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '6px',
            padding: '7px 8px 7px 30px',
            color: 'var(--text-primary)',
            fontSize: '12px',
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
      </div>

      <SearchFilterMenu />

      <motion.button
        onClick={() => {
          onSearchFiltersChange({
            ...searchFilters,
            is_favorite: isFavoriteActive ? undefined : true,
          });
        }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.92 }}
        transition={{ type: 'spring', stiffness: 500, damping: 15 }}
        style={{
          backgroundColor: isFavoriteActive ? 'var(--accent-focal-subtle)' : 'var(--bg-card)',
          border: `1px solid ${isFavoriteActive ? 'var(--accent-focal)' : 'var(--border-subtle)'}`,
          boxShadow: isFavoriteActive ? '0 0 10px rgba(225, 29, 72, 0.35)' : 'none',
          borderRadius: '6px',
          padding: '7px',
          color: isFavoriteActive ? 'var(--accent-focal)' : 'var(--text-secondary)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '32px',
          width: '32px',
          outline: 'none',
        }}
        title="즐겨찾기 필터"
      >
        <motion.div
          key={isFavoriteActive ? 'fav-active' : 'fav-inactive'}
          initial={{ scale: 0.8 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 500, damping: 12 }}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
          <Heart
            size={15}
            fill={isFavoriteActive ? 'var(--accent-focal)' : 'none'}
            color={isFavoriteActive ? 'var(--accent-focal)' : 'currentColor'}
          />
        </motion.div>
      </motion.button>
    </div>
  );
}
