import React from 'react';
import { 
  Sparkles, 
  Camera, 
  Layers, 
  AlertTriangle, 
  Lightbulb, 
  Quote 
} from 'lucide-react';
import { MarkdownBlock, renderInlineMarkdown } from '../../utils/critiqueParser';
import { ExecutiveSummaryCard } from './ExecutiveSummaryCard';

interface CritiqueBlockItemProps {
  block: MarkdownBlock;
  index: number;
  isCompact: boolean;
}

export const CritiqueBlockItem: React.FC<CritiqueBlockItemProps> = ({ block, index, isCompact }) => {
  switch (block.type) {
    case 'executive_summary':
      return <ExecutiveSummaryCard key={index} summary={block.summary} isCompact={isCompact} />;

    case 'section': {
      const getTheme = () => {
        const subtleBorder = 'var(--border-subtle)';
        const headerBg = 'rgba(255, 255, 255, 0.03)';
        const titleColor = 'var(--text-primary)';

        switch (block.themeType) {
          case 'aesthetic':
            return { icon: <Sparkles size={isCompact ? 14 : 17} color="var(--accent-focal-hover)" />, border: 'rgba(225, 29, 72, 0.3)', bg: headerBg, color: titleColor, badge: '미학 진단' };
          case 'camera':
            return { icon: <Camera size={isCompact ? 14 : 17} color="var(--accent-focal)" />, border: 'rgba(225, 29, 72, 0.3)', bg: headerBg, color: titleColor, badge: '화질/광학' };
          case 'structure':
            return { icon: <Layers size={isCompact ? 14 : 17} color="var(--accent-focal-deep)" />, border: 'rgba(225, 29, 72, 0.3)', bg: headerBg, color: titleColor, badge: '구조/질감' };
          case 'defect':
            return { icon: <AlertTriangle size={isCompact ? 14 : 17} color="var(--accent-focal-hover)" />, border: 'rgba(225, 29, 72, 0.3)', bg: headerBg, color: titleColor, badge: '보완 포인트' };
          case 'advice':
            return { icon: <Lightbulb size={isCompact ? 14 : 17} color="var(--accent-focal)" />, border: 'rgba(225, 29, 72, 0.3)', bg: headerBg, color: titleColor, badge: '실전 솔루션' };
          default:
            return { icon: <Layers size={isCompact ? 14 : 17} color="var(--text-muted)" />, border: subtleBorder, bg: headerBg, color: titleColor, badge: '분석 노트' };
        }
      };
      const theme = getTheme();

      if (isCompact) {
        return (
          <div
            key={index}
            style={{
              borderLeft: `2px solid ${theme.border}`,
              paddingLeft: '10px',
              paddingTop: '2px',
              paddingBottom: '2px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {theme.icon}
              <span style={{ fontSize: '13px', fontWeight: 600, color: theme.color }}>
                {block.numberPrefix ? `${block.numberPrefix} ` : ''}{block.title}
              </span>
            </div>
            {block.children.map((child, cIdx) => (
              <CritiqueBlockItem key={cIdx} block={child} index={cIdx} isCompact={true} />
            ))}
          </div>
        );
      }

      return (
        <section
          key={index}
          style={{
            paddingTop: '24px',
            marginTop: '12px',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="font-mono" style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent-focal)' }}>
              {block.numberPrefix ?? '•'}
            </span>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#f4f4f5', letterSpacing: '-0.01em' }}>
              {block.title}
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {block.children.map((child, cIdx) => (
              <CritiqueBlockItem key={cIdx} block={child} index={cIdx} isCompact={false} />
            ))}
          </div>
        </section>
      );
    }

    case 'paragraph':
      return (
        <p
          key={index}
          style={{
            margin: 0,
            color: '#d4d4d8',
            fontSize: isCompact ? '12.5px' : '14.5px',
            lineHeight: isCompact ? '1.6' : '1.75',
            letterSpacing: '-0.01em'
          }}
        >
          {renderInlineMarkdown(block.text)}
        </p>
      );

    case 'bullet_list':
      return (
        <div key={index} style={{ display: 'flex', flexDirection: 'column', gap: isCompact ? '5px' : '8px' }}>
          {block.items.map((item, bIdx) => (
            <div key={bIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', paddingLeft: '4px' }}>
              <span style={{ color: 'var(--accent-focal)', marginTop: isCompact ? '3px' : '5px', fontSize: '10px' }}>●</span>
              <span style={{ flex: 1, color: '#e4e4e7', fontSize: isCompact ? '12.5px' : '14px', lineHeight: '1.65' }}>
                {renderInlineMarkdown(item)}
              </span>
            </div>
          ))}
        </div>
      );

    case 'ordered_list':
      return (
        <div key={index} style={{ display: 'flex', flexDirection: 'column', gap: isCompact ? '5px' : '8px' }}>
          {block.items.map((item, oIdx) => (
            <div key={oIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', paddingLeft: '4px' }}>
              <span style={{ color: 'var(--accent-focal-hover)', fontSize: '11px', fontWeight: 700, marginTop: '2px', minWidth: '16px' }} className="font-mono">{oIdx + 1}.</span>
              <span style={{ flex: 1, color: '#e4e4e7', fontSize: isCompact ? '12.5px' : '14px', lineHeight: '1.65' }}>
                {renderInlineMarkdown(item)}
              </span>
            </div>
          ))}
        </div>
      );

    case 'blockquote':
      return (
        <div
          key={index}
          style={{
            borderLeft: '3px solid var(--accent-focal)',
            backgroundColor: 'var(--accent-focal-subtle)',
            borderRadius: '0 8px 8px 0',
            padding: isCompact ? '8px 12px' : '12px 16px',
            color: '#e4e4e7',
            fontSize: isCompact ? '12.5px' : '14px',
            lineHeight: '1.65',
            fontStyle: 'italic',
            display: 'flex',
            gap: '8px'
          }}
        >
          <Quote size={14} color="var(--accent-focal)" style={{ flexShrink: 0, marginTop: '3px' }} />
          <span>{renderInlineMarkdown(block.text)}</span>
        </div>
      );

    case 'table':
      return (
        <div key={index} style={{ overflowX: 'auto', margin: '6px 0' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: isCompact ? '11.5px' : '13px', textAlign: 'left' }}>
            <thead>
              <tr style={{ backgroundColor: 'rgba(255, 255, 255, 0.06)', borderBottom: '1px solid rgba(255, 255, 255, 0.12)' }}>
                {block.headers.map((h, hIdx) => (
                  <th key={hIdx} style={{ padding: '8px 12px', color: '#fff', fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, rIdx) => (
                <tr key={rIdx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', backgroundColor: rIdx % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.02)' }}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} style={{ padding: '8px 12px', color: '#d4d4d8' }}>{renderInlineMarkdown(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

    case 'code_block':
      return (
        <div key={index} style={{ backgroundColor: '#09090b', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '12px', overflowX: 'auto', fontSize: '12px', fontFamily: 'monospace', color: 'var(--accent-focal-hover)' }}>
          <pre style={{ margin: 0 }}>{block.code}</pre>
        </div>
      );

    case 'divider':
      return <div key={index} style={{ height: '1px', background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent)', margin: isCompact ? '8px 0' : '14px 0' }} />;

    default:
      return null;
  }
};
