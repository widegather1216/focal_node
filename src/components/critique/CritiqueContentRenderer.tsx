import React, { useState } from 'react';
import { 
  Sparkles, 
  AlertTriangle, 
  Lightbulb, 
  Camera, 
  Layers, 
  Sliders,
  Quote,
  Globe,
  ChevronDown,
  ChevronUp,
  HelpCircle
} from 'lucide-react';
import { ScoringGuideModal } from './ScoringGuideModal';

export interface ParsedScores {
  overall: number | null;
  iaa: number | null;
  iqa: number | null;
  ista: number | null;
}

export interface CritiqueContentRendererProps {
  content: string;
  mode?: 'compact' | 'document';
  hideScoreboard?: boolean;
  hideExecutiveSummary?: boolean;
  overallScore?: number | null;
  iaaScore?: number | null;
  iqaScore?: number | null;
  istaScore?: number | null;
  critiqueEn?: string | null;
  // Aliases for snake_case compatibility
  overall_score?: number | null;
  iaa_score?: number | null;
  iqa_score?: number | null;
  ista_score?: number | null;
  critique_en?: string | null;
}

/**
 * Extracts 6-Way ensemble scoreboard block if present.
 */
export function extractScoreboard(text: string): { scores: ParsedScores | null; remainingText: string } {
  const scoreboardRegex = /\[(?:📊\s*)?6-Way\s*앙상블\s*비평\s*스코어보드\]([\s\S]*?)(?=(?:\n\s*#{1,4}\s*|\n\s*\d+\.\s*\[|\n\s*>\s*|$))/i;
  const match = text.match(scoreboardRegex);

  if (!match) {
    return { scores: null, remainingText: text };
  }

  const scoreBlock = match[1];
  const overallMatch = scoreBlock.match(/최종\s*종합\s*평점:\s*(\d+)/i);
  const iaaMatch = scoreBlock.match(/(?:미학|IAA)[\s\S]*?:\s*(\d+)/i);
  const iqaMatch = scoreBlock.match(/(?:화질|IQA)[\s\S]*?:\s*(\d+)/i);
  const istaMatch = scoreBlock.match(/(?:구조|질감|ISTA)[\s\S]*?:\s*(\d+)/i);

  const scores: ParsedScores = {
    overall: overallMatch ? parseInt(overallMatch[1], 10) : null,
    iaa: iaaMatch ? parseInt(iaaMatch[1], 10) : null,
    iqa: iqaMatch ? parseInt(iqaMatch[1], 10) : null,
    ista: istaMatch ? parseInt(istaMatch[1], 10) : null,
  };

  const remainingText = text.replace(match[0], '').trim();
  return { scores, remainingText };
}

/**
 * Types of Markdown AST Blocks
 */
export type MarkdownBlock =
  | { type: 'executive_summary'; summary: string }
  | { type: 'section'; level: number; numberPrefix?: string; title: string; themeType: 'aesthetic' | 'defect' | 'advice' | 'camera' | 'structure' | 'general'; children: MarkdownBlock[] }
  | { type: 'paragraph'; text: string }
  | { type: 'bullet_list'; items: string[] }
  | { type: 'ordered_list'; items: string[] }
  | { type: 'blockquote'; text: string }
  | { type: 'table'; headers: string[]; rows: string[][] }
  | { type: 'code_block'; language: string; code: string }
  | { type: 'divider' };

export function determineThemeType(text: string): 'aesthetic' | 'defect' | 'advice' | 'camera' | 'structure' | 'general' {
  const lower = text.toLowerCase();
  if (lower.includes('미학') || lower.includes('iaa') || lower.includes('장점') || lower.includes('개성') || text.includes('🎨') || text.includes('🌟')) {
    return 'aesthetic';
  }
  if (lower.includes('화질') || lower.includes('광학') || lower.includes('iqa') || lower.includes('exif') || lower.includes('장비') || lower.includes('카메라') || lower.includes('습관') || text.includes('📷')) {
    return 'camera';
  }
  if (lower.includes('구조') || lower.includes('질감') || lower.includes('ista') || lower.includes('재질') || lower.includes('텍스처')) {
    return 'structure';
  }
  if (lower.includes('결함') || lower.includes('왜곡') || lower.includes('실책') || lower.includes('보완') || lower.includes('취약') || text.includes('🔍') || text.includes('⚠️')) {
    return 'defect';
  }
  if (lower.includes('조언') || lower.includes('가이드라인') || lower.includes('솔루션') || lower.includes('재촬영') || lower.includes('개선') || text.includes('💡') || text.includes('🚀')) {
    return 'advice';
  }
  return 'general';
}

/**
 * Parses markdown text into rich structured blocks.
 */
export function parseMarkdownToBlocks(text: string): MarkdownBlock[] {
  const lines = text.split('\n');
  const rootBlocks: MarkdownBlock[] = [];
  let currentSection: (Extract<MarkdownBlock, { type: 'section' }>) | null = null;

  const pushBlock = (block: MarkdownBlock) => {
    if (block.type === 'section') {
      if (currentSection) {
        rootBlocks.push(currentSection);
      }
      currentSection = block;
    } else if (currentSection) {
      currentSection.children.push(block);
    } else {
      rootBlocks.push(block);
    }
  };

  let i = 0;
  while (i < lines.length) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    if (!trimmed) {
      i++;
      continue;
    }

    // 1. Executive summary blockquote: "> **한 줄 총평**: ..." or "> **포트폴리오 종합 총평**: ..."
    const execSummaryMatch = trimmed.match(/^>\s*(?:[💡🌟]\s*)?(?:\*\*)?(?:한\s*줄\s*총평|포트폴리오\s*종합\s*총평|종합\s*총평|총평)(?:\*\*)?[\s:]*(.*)/i);
    if (execSummaryMatch) {
      let summaryText = execSummaryMatch[1].replace(/^\*\*|\*\*$/g, '').trim();
      // Lookahead for multi-line blockquote
      while (i + 1 < lines.length && lines[i + 1].trim().startsWith('>')) {
        i++;
        summaryText += ' ' + lines[i].trim().replace(/^>\s*/, '');
      }
      rootBlocks.push({ type: 'executive_summary', summary: summaryText.trim() });
      i++;
      continue;
    }

    // 2. Section Heading: "## 1. [제목]" or "1. [제목]:"
    const headingMatch = trimmed.match(/^(#{1,4})\s*(?:(\d+)\.\s*)?([^\n:]+):?$/) || 
                         trimmed.match(/^(\d+)\.\s*(\[?[^\]\n:]+\]?):?$/);
    if (headingMatch) {
      let level = 2;
      let numPrefix: string | undefined;
      let title = '';

      if (headingMatch[1].startsWith('#')) {
        level = headingMatch[1].length;
        numPrefix = headingMatch[2] ? `${headingMatch[2]}.` : undefined;
        title = headingMatch[3].trim().replace(/^\[|\]$/g, '');
      } else {
        // Fallback for "1. [제목]:" format
        level = 2;
        numPrefix = `${headingMatch[1]}.`;
        title = headingMatch[2].trim().replace(/^\[|\]$/g, '');
      }

      pushBlock({
        type: 'section',
        level,
        numberPrefix: numPrefix,
        title,
        themeType: determineThemeType(title),
        children: []
      });
      i++;
      continue;
    }

    // 3. Regular Blockquote ("> ...")
    if (trimmed.startsWith('>')) {
      let quoteText = trimmed.replace(/^>\s*/, '');
      while (i + 1 < lines.length && lines[i + 1].trim().startsWith('>')) {
        i++;
        quoteText += ' ' + lines[i].trim().replace(/^>\s*/, '');
      }
      pushBlock({ type: 'blockquote', text: quoteText });
      i++;
      continue;
    }

    // 4. Horizontal Divider ("---" or "***")
    if (/^(\-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      pushBlock({ type: 'divider' });
      i++;
      continue;
    }

    // 5. Code Block ("```")
    if (trimmed.startsWith('```')) {
      const lang = trimmed.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      pushBlock({ type: 'code_block', language: lang, code: codeLines.join('\n') });
      i++;
      continue;
    }

    // 6. Markdown Table ("| Header | ... |")
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      const tableLines: string[] = [trimmed];
      while (i + 1 < lines.length && lines[i + 1].trim().startsWith('|') && lines[i + 1].trim().endsWith('|')) {
        i++;
        tableLines.push(lines[i].trim());
      }
      if (tableLines.length >= 2) {
        const parseRow = (row: string) => row.slice(1, -1).split('|').map(c => c.trim());
        const headers = parseRow(tableLines[0]);
        const dataRows = tableLines.slice(2).map(parseRow); // Skip divider row
        pushBlock({ type: 'table', headers, rows: dataRows });
        i++;
        continue;
      }
    }

    // 7. Bullet List ("- " or "* ")
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const items: string[] = [];
      while (i < lines.length && (lines[i].trim().startsWith('- ') || lines[i].trim().startsWith('* '))) {
        items.push(lines[i].trim().substring(2));
        i++;
      }
      pushBlock({ type: 'bullet_list', items });
      continue;
    }

    // 8. Ordered List ("1. ", "2. ") - when not a section heading
    const orderedMatch = trimmed.match(/^\d+\.\s+(.*)/);
    if (orderedMatch) {
      const items: string[] = [];
      while (i < lines.length) {
        const m = lines[i].trim().match(/^\d+\.\s+(.*)/);
        if (!m) break;
        items.push(m[1]);
        i++;
      }
      pushBlock({ type: 'ordered_list', items });
      continue;
    }

    // 9. Standard Paragraph
    pushBlock({ type: 'paragraph', text: trimmed });
    i++;
  }

  if (currentSection) {
    rootBlocks.push(currentSection);
  }

  return rootBlocks;
}

/**
 * Renders inline markdown: bold, italic, code, tag badges
 */
function renderInlineMarkdown(text: string) {
  // Regex to split by bold (**text**), inline code (`code`), or tag ([tag])
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);

  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={idx} style={{ color: '#fff', fontWeight: 600 }}>
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code
          key={idx}
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.08)',
            padding: '2px 6px',
            borderRadius: '4px',
            fontSize: '90%',
            color: 'var(--accent-focal-hover)',
            fontFamily: 'monospace'
          }}
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

/**
 * Visual Scoreboard Card Component.
 */
export const CritiqueScoreboardCard: React.FC<{ scores: ParsedScores; isCompact?: boolean }> = ({ 
  scores, 
  isCompact = false 
}) => {
  const [isGuideOpen, setIsGuideOpen] = useState(false);

  return (
    <div
      style={{
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid var(--border-subtle)',
        borderRadius: isCompact ? '8px' : '10px',
        padding: isCompact ? '12px 14px' : '16px 20px',
        marginBottom: isCompact ? '12px' : '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: isCompact ? '10px' : '14px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={isCompact ? 14 : 16} color="var(--accent-focal)" />
          <span style={{ fontSize: isCompact ? '12.5px' : '14px', fontWeight: 600, color: '#f4f4f5', letterSpacing: '-0.01em' }}>
            6-Way 지각 앙상블 평점
          </span>
        </div>
        <button
          type="button"
          onClick={() => setIsGuideOpen(true)}
          title="점수 산출 기준 가이드 열기"
          aria-label="점수 산출 기준 가이드"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            padding: isCompact ? '2px 6px' : '3px 8px',
            color: 'var(--text-secondary)',
            fontSize: isCompact ? '10.5px' : '11.5px',
            cursor: 'pointer',
            transition: 'color 0.15s ease, background-color 0.15s ease, border-color 0.15s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = 'var(--text-primary)';
            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)';
            e.currentTarget.style.borderColor = 'rgba(225, 29, 72, 0.3)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = 'var(--text-secondary)';
            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
            e.currentTarget.style.borderColor = 'var(--border-subtle)';
          }}
        >
          <HelpCircle size={isCompact ? 11 : 13} color="var(--accent-focal)" />
          <span>점수 산출 가이드</span>
        </button>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: isCompact ? '1fr' : '120px 1fr',
        gap: isCompact ? '10px' : '24px',
        alignItems: 'center'
      }}>
        {scores.overall !== null && (
          <div style={{
            display: 'flex',
            flexDirection: isCompact ? 'row' : 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: isCompact ? '8px' : '2px',
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '8px',
            padding: isCompact ? '8px 12px' : '12px 14px'
          }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.06em' }}>
              SCORE
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '3px' }}>
              <span className="font-mono" style={{ fontSize: isCompact ? '20px' : '26px', fontWeight: 700, color: '#fff', letterSpacing: '-0.02em', lineHeight: 1 }}>
                {scores.overall}
              </span>
              <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>/ 100</span>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: isCompact ? '6px' : '8px' }}>
          {scores.iaa !== null && (
            <ScoreBar 
              icon={<Sparkles size={12} color="var(--accent-focal-hover)" style={{ flexShrink: 0 }} />}
              label="미학 & 구도 지수 (IAA)" 
              score={scores.iaa} 
              color="var(--accent-focal-hover)" 
              isCompact={isCompact} 
            />
          )}
          {scores.iqa !== null && (
            <ScoreBar 
              icon={<Camera size={12} color="var(--accent-focal)" style={{ flexShrink: 0 }} />}
              label="화질 & 광학 지수 (IQA)" 
              score={scores.iqa} 
              color="var(--accent-focal)" 
              isCompact={isCompact} 
            />
          )}
          {scores.ista !== null && (
            <ScoreBar 
              icon={<Layers size={12} color="var(--accent-focal-deep)" style={{ flexShrink: 0 }} />}
              label="구조 & 질감 지수 (ISTA)" 
              score={scores.ista} 
              color="var(--accent-focal-deep)" 
              isCompact={isCompact} 
            />
          )}
        </div>
      </div>

      {isGuideOpen && (
        <ScoringGuideModal 
          isOpen={isGuideOpen} 
          onClose={() => setIsGuideOpen(false)} 
        />
      )}
    </div>
  );
};

const ScoreBar: React.FC<{ 
  label: string; 
  score: number; 
  color: string; 
  isCompact: boolean;
  icon?: React.ReactNode;
}> = ({
  label,
  score,
  color,
  isCompact,
  icon
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: isCompact ? '11px' : '12px' }}>
        <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '5px' }}>
          {icon}
          <span>{label}</span>
        </span>
        <span style={{ color: '#fff', fontWeight: 600 }} className="font-mono">{score}</span>
      </div>
      <div style={{
        height: isCompact ? '3px' : '4px',
        backgroundColor: 'rgba(255, 255, 255, 0.06)',
        borderRadius: '2px',
        overflow: 'hidden'
      }}>
        <div
          style={{
            height: '100%',
            width: `${Math.min(100, Math.max(0, score))}%`,
            backgroundColor: color,
            borderRadius: '2px',
            transition: 'width 0.8s ease'
          }}
        />
      </div>
    </div>
  );
};

export const ExecutiveSummaryCard: React.FC<{ summary: string; isCompact?: boolean }> = ({
  summary,
  isCompact = false
}) => {
  return (
    <div
      style={{
        background: 'rgba(255, 255, 255, 0.02)',
        borderLeft: '2.5px solid var(--accent-focal)',
        borderRadius: '0 6px 6px 0',
        padding: isCompact ? '10px 14px' : '14px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Sparkles size={isCompact ? 12 : 13} color="var(--accent-focal)" />
        <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-focal)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          통합 한 줄 총평
        </span>
      </div>
      <p style={{
        margin: 0,
        fontSize: isCompact ? '13px' : '15px',
        fontWeight: 400,
        color: '#f4f4f5',
        lineHeight: isCompact ? '1.6' : '1.7',
        fontStyle: 'italic',
        letterSpacing: '-0.01em'
      }}>
        "{summary}"
      </p>
    </div>
  );
};

/**
 * Renders individual Markdown Blocks into React Elements.
 */
function renderBlock(block: MarkdownBlock, idx: number, isCompact: boolean): React.ReactNode {
  switch (block.type) {
    case 'executive_summary':
      return <ExecutiveSummaryCard key={idx} summary={block.summary} isCompact={isCompact} />;

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
            key={idx}
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
            {block.children.map((child, cIdx) => renderBlock(child, cIdx, true))}
          </div>
        );
      }

      return (
        <section
          key={idx}
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
            {block.children.map((child, cIdx) => renderBlock(child, cIdx, false))}
          </div>
        </section>
      );
    }

    case 'paragraph':
      return (
        <p
          key={idx}
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
        <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: isCompact ? '5px' : '8px' }}>
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
        <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: isCompact ? '5px' : '8px' }}>
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
          key={idx}
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
        <div key={idx} style={{ overflowX: 'auto', margin: '6px 0' }}>
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
        <div key={idx} style={{ backgroundColor: '#09090b', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '12px', overflowX: 'auto', fontSize: '12px', fontFamily: 'monospace', color: 'var(--accent-focal-hover)' }}>
          <pre style={{ margin: 0 }}>{block.code}</pre>
        </div>
      );

    case 'divider':
      return <div key={idx} style={{ height: '1px', background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent)', margin: isCompact ? '8px 0' : '14px 0' }} />;

    default:
      return null;
  }
}

/**
 * Dedicated Card for UniPercept 8B VQA English Original Feedback.
 */
export const OriginalEnglishCritiqueCard: React.FC<{
  critiqueEn: string;
  isCompact?: boolean;
}> = ({ critiqueEn, isCompact = false }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!critiqueEn || !critiqueEn.trim()) return null;

  return (
    <div
      style={{
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid var(--border-subtle)',
        borderRadius: isCompact ? '6px' : '8px',
        overflow: 'hidden',
        marginTop: isCompact ? '6px' : '14px'
      }}
    >
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: isCompact ? '8px 10px' : '10px 14px',
          background: 'rgba(255, 255, 255, 0.03)',
          border: 'none',
          color: 'var(--text-secondary)',
          cursor: 'pointer',
          textAlign: 'left',
          transition: 'background 0.15s ease'
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)')}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Globe size={isCompact ? 13 : 15} color="var(--accent-focal-hover)" />
          <span style={{ fontSize: isCompact ? '12px' : '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
            UniPercept 8B VQA 영문 원문
          </span>
          <span
            className="font-mono"
            style={{
              fontSize: '10px',
              background: 'var(--accent-focal-subtle)',
              color: 'var(--accent-focal-hover)',
              border: '1px solid rgba(225, 29, 72, 0.25)',
              padding: '1px 5px',
              borderRadius: '4px',
              fontWeight: 600
            }}
          >
            RAW EN
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-muted)', fontSize: '11px' }}>
          <span>{isOpen ? '접기' : '원문 보기'}</span>
          {isOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </div>
      </button>

      {isOpen && (
        <div
          style={{
            padding: isCompact ? '10px 12px' : '14px 18px',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: isCompact ? '12px' : '13.5px',
            lineHeight: '1.65',
            color: '#d4d4d8',
            fontFamily: 'var(--font-mono)',
            whiteSpace: 'pre-wrap',
            backgroundColor: 'rgba(0, 0, 0, 0.25)'
          }}
        >
          {critiqueEn.trim()}
        </div>
      )}
    </div>
  );
};

/**
 * Universal Markdown Report Renderer for Critique and AI Documents.
 */
export const CritiqueContentRenderer: React.FC<CritiqueContentRendererProps> = ({
  content,
  mode = 'document',
  hideScoreboard = false,
  hideExecutiveSummary = false,
  overallScore,
  iaaScore,
  iqaScore,
  istaScore,
  critiqueEn,
  overall_score,
  iaa_score,
  iqa_score,
  ista_score,
  critique_en,
}) => {
  if (!content) return null;

  const isCompact = mode === 'compact';
  const { scores: extractedScores, remainingText } = extractScoreboard(content);

  // Normalize scores: prioritize explicit normalized props, fallback to extracted regex scores
  const effOverall = overallScore !== undefined ? overallScore : overall_score;
  const effIaa = iaaScore !== undefined ? iaaScore : iaa_score;
  const effIqa = iqaScore !== undefined ? iqaScore : iqa_score;
  const effIsta = istaScore !== undefined ? istaScore : ista_score;
  const effCritiqueEn = critiqueEn !== undefined ? critiqueEn : critique_en;

  const hasNormalizedScores =
    (effOverall !== undefined && effOverall !== null) ||
    (effIaa !== undefined && effIaa !== null) ||
    (effIqa !== undefined && effIqa !== null) ||
    (effIsta !== undefined && effIsta !== null);

  const scores: ParsedScores | null = hasNormalizedScores
    ? {
        overall: effOverall != null ? Math.round(effOverall) : null,
        iaa: effIaa != null ? Math.round(effIaa) : null,
        iqa: effIqa != null ? Math.round(effIqa) : null,
        ista: effIsta != null ? Math.round(effIsta) : null,
      }
    : extractedScores;

  let blocks = parseMarkdownToBlocks(remainingText);
  if (hideExecutiveSummary) {
    blocks = blocks.filter(b => b.type !== 'executive_summary');
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: isCompact ? '12px' : '18px' }}>
      {/* 1. Scoreboard (prioritizing normalized scores, fallback to regex parsed) */}
      {!hideScoreboard && scores && <CritiqueScoreboardCard scores={scores} isCompact={isCompact} />}

      {/* 2. Structured Markdown Blocks */}
      {blocks.map((block, idx) => renderBlock(block, idx, isCompact))}

      {/* 3. UniPercept 8B VQA English Original Feedback */}
      {effCritiqueEn && (
        <OriginalEnglishCritiqueCard critiqueEn={effCritiqueEn} isCompact={isCompact} />
      )}
    </div>
  );
};
