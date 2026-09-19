import React from 'react';
import { 
  Sparkles, 
  AlertTriangle, 
  Lightbulb, 
  Camera, 
  Layers, 
  Sliders,
  Quote
} from 'lucide-react';

interface ParsedScores {
  overall: number | null;
  iaa: number | null;
  iqa: number | null;
  ista: number | null;
}

interface CritiqueContentRendererProps {
  content: string;
  mode?: 'compact' | 'document';
}

/**
 * Extracts 6-Way ensemble scoreboard block if present.
 */
function extractScoreboard(text: string): { scores: ParsedScores | null; remainingText: string } {
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
type MarkdownBlock =
  | { type: 'executive_summary'; summary: string }
  | { type: 'section'; level: number; numberPrefix?: string; title: string; themeType: 'aesthetic' | 'defect' | 'advice' | 'camera' | 'structure' | 'general'; children: MarkdownBlock[] }
  | { type: 'paragraph'; text: string }
  | { type: 'bullet_list'; items: string[] }
  | { type: 'ordered_list'; items: string[] }
  | { type: 'blockquote'; text: string }
  | { type: 'table'; headers: string[]; rows: string[][] }
  | { type: 'code_block'; language: string; code: string }
  | { type: 'divider' };

function determineThemeType(text: string): 'aesthetic' | 'defect' | 'advice' | 'camera' | 'structure' | 'general' {
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
function parseMarkdownToBlocks(text: string): MarkdownBlock[] {
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
            color: '#c084fc',
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
  const getGrade = (score: number) => {
    if (score >= 90) return { label: 'S (Masterpiece)', color: '#a855f7', bg: 'rgba(168, 85, 247, 0.15)' };
    if (score >= 80) return { label: 'A (Excellent)', color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.15)' };
    if (score >= 70) return { label: 'B (Good)', color: '#4ade80', bg: 'rgba(74, 222, 128, 0.15)' };
    return { label: 'C (Developing)', color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.15)' };
  };

  const gradeInfo = scores.overall ? getGrade(scores.overall) : null;

  return (
    <div
      style={{
        background: isCompact 
          ? 'linear-gradient(135deg, rgba(24, 24, 27, 0.8) 0%, rgba(18, 18, 20, 0.9) 100%)'
          : 'linear-gradient(135deg, rgba(39, 39, 42, 0.6) 0%, rgba(24, 24, 27, 0.9) 100%)',
        border: '1px solid rgba(168, 85, 247, 0.25)',
        borderRadius: isCompact ? '10px' : '16px',
        padding: isCompact ? '12px 14px' : '18px 22px',
        marginBottom: isCompact ? '12px' : '20px',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)',
        display: 'flex',
        flexDirection: 'column',
        gap: isCompact ? '10px' : '14px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={isCompact ? 15 : 18} color="#c084fc" />
          <span style={{ fontSize: isCompact ? '13px' : '15px', fontWeight: 700, color: '#f4f4f5' }}>
            6-Way 지각 앙상블 평점
          </span>
        </div>
        {gradeInfo && (
          <span
            style={{
              fontSize: isCompact ? '11px' : '12px',
              fontWeight: 700,
              padding: isCompact ? '2px 8px' : '4px 10px',
              borderRadius: '20px',
              background: gradeInfo.bg,
              color: gradeInfo.color,
              border: `1px solid ${gradeInfo.color}40`
            }}
          >
            {gradeInfo.label}
          </span>
        )}
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: isCompact ? '1fr' : '110px 1fr',
        gap: isCompact ? '10px' : '20px',
        alignItems: 'center'
      }}>
        {scores.overall !== null && (
          <div style={{
            display: 'flex',
            flexDirection: isCompact ? 'row' : 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: isCompact ? '10px' : '4px',
            background: 'rgba(168, 85, 247, 0.08)',
            border: '1px solid rgba(168, 85, 247, 0.2)',
            borderRadius: '12px',
            padding: isCompact ? '8px 12px' : '12px'
          }}>
            <span style={{ fontSize: '11px', color: '#a1a1aa', fontWeight: 500 }}>종합 점수</span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '2px' }}>
              <span style={{ fontSize: isCompact ? '22px' : '28px', fontWeight: 800, color: '#fff', letterSpacing: '-0.02em' }}>
                {scores.overall}
              </span>
              <span style={{ fontSize: '11px', color: '#71717a' }}>/100</span>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: isCompact ? '6px' : '10px' }}>
          {scores.iaa !== null && (
            <ScoreBar label="🎨 미학 & 구도 (IAA)" score={scores.iaa} color="#c084fc" isCompact={isCompact} />
          )}
          {scores.iqa !== null && (
            <ScoreBar label="🔍 화질 & 선명도 (IQA)" score={scores.iqa} color="#38bdf8" isCompact={isCompact} />
          )}
          {scores.ista !== null && (
            <ScoreBar label="🧱 구조 & 질감 (ISTA)" score={scores.ista} color="#4ade80" isCompact={isCompact} />
          )}
        </div>
      </div>
    </div>
  );
};

const ScoreBar: React.FC<{ label: string; score: number; color: string; isCompact: boolean }> = ({
  label,
  score,
  color,
  isCompact
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: isCompact ? '11px' : '12px' }}>
        <span style={{ color: '#d4d4d8' }}>{label}</span>
        <span style={{ color: '#fff', fontWeight: 600 }}>{score}점</span>
      </div>
      <div style={{
        height: isCompact ? '4px' : '6px',
        backgroundColor: 'rgba(255, 255, 255, 0.08)',
        borderRadius: '3px',
        overflow: 'hidden'
      }}>
        <div
          style={{
            height: '100%',
            width: `${Math.min(100, Math.max(0, score))}%`,
            backgroundColor: color,
            borderRadius: '3px',
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
        background: isCompact
          ? 'rgba(168, 85, 247, 0.08)'
          : 'linear-gradient(135deg, rgba(168, 85, 247, 0.12) 0%, rgba(99, 102, 241, 0.08) 100%)',
        border: '1px solid rgba(168, 85, 247, 0.3)',
        borderLeft: isCompact ? '3px solid #c084fc' : '4px solid #c084fc',
        borderRadius: isCompact ? '8px' : '14px',
        padding: isCompact ? '10px 14px' : '16px 20px',
        boxShadow: isCompact ? 'none' : '0 4px 20px rgba(168, 85, 247, 0.12)',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Sparkles size={isCompact ? 13 : 16} color="#c084fc" />
        <span style={{ fontSize: isCompact ? '11px' : '12px', fontWeight: 700, color: '#c084fc', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
          통합 한 줄 총평 (Executive Summary)
        </span>
      </div>
      <p style={{
        margin: 0,
        fontSize: isCompact ? '13px' : '15px',
        fontWeight: 500,
        color: '#f4f4f5',
        lineHeight: isCompact ? '1.55' : '1.7',
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
        switch (block.themeType) {
          case 'aesthetic':
            return { icon: <Sparkles size={isCompact ? 14 : 17} color="#c084fc" />, border: 'rgba(168, 85, 247, 0.25)', bg: 'rgba(168, 85, 247, 0.1)', color: '#e9d5ff', badge: '미학 진단' };
          case 'camera':
            return { icon: <Camera size={isCompact ? 14 : 17} color="#38bdf8" />, border: 'rgba(56, 189, 248, 0.25)', bg: 'rgba(56, 189, 248, 0.1)', color: '#bae6fd', badge: '화질/광학' };
          case 'structure':
            return { icon: <Layers size={isCompact ? 14 : 17} color="#818cf8" />, border: 'rgba(129, 140, 248, 0.25)', bg: 'rgba(129, 140, 248, 0.1)', color: '#c7d2fe', badge: '구조/질감' };
          case 'defect':
            return { icon: <AlertTriangle size={isCompact ? 14 : 17} color="#fbbf24" />, border: 'rgba(251, 191, 36, 0.25)', bg: 'rgba(251, 191, 36, 0.1)', color: '#fef08a', badge: '보완 포인트' };
          case 'advice':
            return { icon: <Lightbulb size={isCompact ? 14 : 17} color="#34d399" />, border: 'rgba(52, 211, 153, 0.25)', bg: 'rgba(52, 211, 153, 0.1)', color: '#a7f3d0', badge: '실전 솔루션' };
          default:
            return { icon: <Layers size={isCompact ? 14 : 17} color="#a1a1aa" />, border: 'rgba(255, 255, 255, 0.1)', bg: 'rgba(255, 255, 255, 0.05)', color: '#f4f4f5', badge: '분석 노트' };
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
        <article
          key={idx}
          style={{
            backgroundColor: 'rgba(24, 24, 27, 0.65)',
            border: `1px solid ${theme.border}`,
            borderRadius: '14px',
            overflow: 'hidden',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)'
          }}
        >
          <div
            style={{
              padding: '12px 20px',
              backgroundColor: theme.bg,
              borderBottom: `1px solid ${theme.border}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ padding: '5px', borderRadius: '8px', background: 'rgba(0, 0, 0, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {theme.icon}
              </div>
              <h3 style={{ margin: 0, fontSize: '15.5px', fontWeight: 700, color: theme.color, letterSpacing: '-0.01em' }}>
                {block.numberPrefix ? `${block.numberPrefix} ` : ''}{block.title}
              </h3>
            </div>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#a1a1aa', background: 'rgba(0, 0, 0, 0.3)', padding: '3px 8px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              {theme.badge}
            </span>
          </div>

          <div style={{ padding: '18px 22px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {block.children.map((child, cIdx) => renderBlock(child, cIdx, false))}
          </div>
        </article>
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
              <span style={{ color: '#a855f7', marginTop: isCompact ? '3px' : '5px', fontSize: '10px' }}>●</span>
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
              <span style={{ color: '#c084fc', fontSize: '11px', fontWeight: 700, marginTop: '2px', minWidth: '16px' }}>{oIdx + 1}.</span>
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
            borderLeft: '3px solid #a855f7',
            backgroundColor: 'rgba(168, 85, 247, 0.06)',
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
          <Quote size={14} color="#c084fc" style={{ flexShrink: 0, marginTop: '3px' }} />
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
        <div key={idx} style={{ backgroundColor: '#09090b', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '8px', padding: '12px', overflowX: 'auto', fontSize: '12px', fontFamily: 'monospace', color: '#c084fc' }}>
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
 * Universal Markdown Report Renderer for Critique and AI Documents.
 */
export const CritiqueContentRenderer: React.FC<CritiqueContentRendererProps> = ({
  content,
  mode = 'document'
}) => {
  if (!content) return null;

  const isCompact = mode === 'compact';
  const { scores, remainingText } = extractScoreboard(content);
  const blocks = parseMarkdownToBlocks(remainingText);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: isCompact ? '12px' : '18px' }}>
      {/* 1. Scoreboard (if extracted) */}
      {scores && <CritiqueScoreboardCard scores={scores} isCompact={isCompact} />}

      {/* 2. Structured Markdown Blocks */}
      {blocks.map((block, idx) => renderBlock(block, idx, isCompact))}
    </div>
  );
};
