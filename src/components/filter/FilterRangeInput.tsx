import React from 'react';

interface FilterRangeInputProps {
  label: string;
  minPlaceholder?: string;
  maxPlaceholder?: string;
  minValue?: number | string;
  maxValue?: number | string;
  onMinChange: (val: string) => void;
  onMaxChange: (val: string) => void;
}

export const FilterRangeInput: React.FC<FilterRangeInputProps> = ({
  label,
  minPlaceholder = '최소',
  maxPlaceholder = '최대',
  minValue = '',
  maxValue = '',
  onMinChange,
  onMaxChange
}) => {
  return (
    <div>
      <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '3px' }}>
        {label}
      </label>
      <div style={{ display: 'flex', gap: '6px' }}>
        <input 
          type="number" 
          placeholder={minPlaceholder}
          value={minValue}
          onChange={(e) => onMinChange(e.target.value)}
          className="font-mono"
          style={{
            flex: 1,
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            padding: '5px 8px',
            color: 'var(--text-primary)',
            fontSize: '11px',
            width: '100%',
            boxSizing: 'border-box'
          }}
        />
        <input 
          type="number" 
          placeholder={maxPlaceholder}
          value={maxValue}
          onChange={(e) => onMaxChange(e.target.value)}
          className="font-mono"
          style={{
            flex: 1,
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            padding: '5px 8px',
            color: 'var(--text-primary)',
            fontSize: '11px',
            width: '100%',
            boxSizing: 'border-box'
          }}
        />
      </div>
    </div>
  );
};
