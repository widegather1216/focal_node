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
  minPlaceholder = 'Min',
  maxPlaceholder = 'Max',
  minValue = '',
  maxValue = '',
  onMinChange,
  onMaxChange
}) => {
  return (
    <div>
      <label style={{ display: 'block', fontSize: '12px', color: '#aaa', marginBottom: '4px' }}>
        {label}
      </label>
      <div style={{ display: 'flex', gap: '8px' }}>
        <input 
          type="number" 
          placeholder={minPlaceholder}
          value={minValue}
          onChange={(e) => onMinChange(e.target.value)}
          style={{
            flex: 1,
            backgroundColor: '#333',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '4px',
            padding: '6px 8px',
            color: '#fff',
            fontSize: '12px',
            width: '100%',
            boxSizing: 'border-box'
          }}
        />
        <input 
          type="number" 
          placeholder={maxPlaceholder}
          value={maxValue}
          onChange={(e) => onMaxChange(e.target.value)}
          style={{
            flex: 1,
            backgroundColor: '#333',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '4px',
            padding: '6px 8px',
            color: '#fff',
            fontSize: '12px',
            width: '100%',
            boxSizing: 'border-box'
          }}
        />
      </div>
    </div>
  );
};
