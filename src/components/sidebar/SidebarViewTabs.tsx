import React from 'react';
import { BarChart3, Image as ImageIcon, Sparkles } from 'lucide-react';

export type SidebarTabId = 'gallery' | 'analytics' | 'critique';

interface SidebarViewTabsProps {
  activeTab: SidebarTabId;
  onSelectTab: (tab: SidebarTabId) => void;
}

const VIEW_TAB_ITEMS: Array<{
  id: SidebarTabId;
  label: string;
  Icon: React.ComponentType<{ size?: number; style?: React.CSSProperties }>;
}> = [
  { id: 'gallery', label: '갤러리', Icon: ImageIcon },
  { id: 'analytics', label: '장비 분석', Icon: BarChart3 },
  { id: 'critique', label: 'AI 비평', Icon: Sparkles },
];

export function SidebarViewTabs({ activeTab, onSelectTab }: SidebarViewTabsProps) {
  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
        <div
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: 'var(--accent-focal)',
            boxShadow: '0 0 10px rgba(225, 29, 72, 0.7)',
          }}
        />
        <h2
          style={{
            fontSize: '15px',
            fontWeight: 600,
            margin: 0,
            color: 'var(--text-primary)',
            letterSpacing: '-0.02em',
          }}
        >
          Focal Node
        </h2>
      </div>

      <div
        style={{
          display: 'flex',
          gap: '2px',
          marginBottom: '14px',
          background: 'var(--bg-canvas)',
          padding: '3px',
          borderRadius: '8px',
          border: '1px solid var(--border-subtle)',
        }}
      >
        {VIEW_TAB_ITEMS.map(({ id, label, Icon }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => onSelectTab(id)}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px',
                background: isActive ? 'var(--bg-elevated)' : 'transparent',
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                border: isActive ? '1px solid rgba(255, 255, 255, 0.08)' : '1px solid transparent',
                padding: '6px 2px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 500,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                flexShrink: 0,
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={13} style={{ flexShrink: 0 }} />
              <span style={{ whiteSpace: 'nowrap' }}>{label}</span>
            </button>
          );
        })}
      </div>
    </>
  );
}
