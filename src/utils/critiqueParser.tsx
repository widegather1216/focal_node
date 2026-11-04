import React from 'react';

export interface ParsedScores {
  overall: number | null;
  iaa: number | null;
  iqa: number | null;
  ista: number | null;
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
                         trimmed.match(/^(\d+)\.\s*([^\n:]+):$/);
    if (headingMatch && !trimmed.startsWith('```')) {
      const isHash = headingMatch[1].startsWith('#');
      const level = isHash ? headingMatch[1].length : 2;
      const numberPrefix = isHash ? (headingMatch[2] ? `${headingMatch[2]}.` : undefined) : `${headingMatch[1]}.`;
      const title = (isHash ? headingMatch[3] : headingMatch[2]).trim();

      pushBlock({
        type: 'section',
        level,
        numberPrefix,
        title,
        themeType: determineThemeType(title),
        children: []
      });
      i++;
      continue;
    }

    // 3. Fenced Code Block: ```ts ... ```
    if (trimmed.startsWith('```')) {
      const language = trimmed.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      pushBlock({ type: 'code_block', language, code: codeLines.join('\n') });
      i++;
      continue;
    }

    // 4. Blockquote: "> ..."
    if (trimmed.startsWith('>')) {
      const quoteLines: string[] = [trimmed.replace(/^>\s*/, '')];
      while (i + 1 < lines.length && lines[i + 1].trim().startsWith('>')) {
        i++;
        quoteLines.push(lines[i].trim().replace(/^>\s*/, ''));
      }
      pushBlock({ type: 'blockquote', text: quoteLines.join(' ') });
      i++;
      continue;
    }

    // 5. Divider: "---" or "***"
    if (/^(\*{3,}|-{3,}|_{3,})$/.test(trimmed)) {
      pushBlock({ type: 'divider' });
      i++;
      continue;
    }

    // 6. Markdown Table: "| Head 1 | Head 2 |"
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.includes('|')) {
      const tableLines: string[] = [trimmed];
      while (i + 1 < lines.length && lines[i + 1].trim().startsWith('|') && lines[i + 1].trim().endsWith('|')) {
        i++;
        tableLines.push(lines[i].trim());
      }
      if (tableLines.length >= 2) {
        const headers = tableLines[0].slice(1, -1).split('|').map(s => s.trim());
        const dataRows = tableLines.slice(2).map(line => 
          line.slice(1, -1).split('|').map(s => s.trim())
        );
        pushBlock({ type: 'table', headers, rows: dataRows });
        i++;
        continue;
      }
    }

    // 7. Unordered Bullet List: "- " or "* " or "• "
    if (/^[-*•]\s+/.test(trimmed)) {
      const items: string[] = [trimmed.replace(/^[-*•]\s+/, '')];
      while (i + 1 < lines.length && /^[-*•]\s+/.test(lines[i + 1].trim())) {
        i++;
        items.push(lines[i].trim().replace(/^[-*•]\s+/, ''));
      }
      pushBlock({ type: 'bullet_list', items });
      i++;
      continue;
    }

    // 8. Ordered Numbered List: "1. " or "2. "
    if (/^\d+\.\s+/.test(trimmed) && !trimmed.endsWith(':')) {
      const items: string[] = [trimmed.replace(/^\d+\.\s+/, '')];
      while (i + 1 < lines.length && /^\d+\.\s+/.test(lines[i + 1].trim()) && !lines[i + 1].trim().endsWith(':')) {
        i++;
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
      }
      pushBlock({ type: 'ordered_list', items });
      i++;
      continue;
    }

    // 9. Standard Paragraph (merging multi-line consecutive paragraphs)
    const paraLines: string[] = [trimmed];
    while (
      i + 1 < lines.length &&
      lines[i + 1].trim() &&
      !lines[i + 1].trim().startsWith('#') &&
      !lines[i + 1].trim().startsWith('>') &&
      !lines[i + 1].trim().startsWith('```') &&
      !lines[i + 1].trim().startsWith('|') &&
      !/^[-*•]\s+/.test(lines[i + 1].trim()) &&
      !/^\d+\.\s+/.test(lines[i + 1].trim()) &&
      !/^(\*{3,}|-{3,}|_{3,})$/.test(lines[i + 1].trim())
    ) {
      i++;
      paraLines.push(lines[i].trim());
    }
    pushBlock({ type: 'paragraph', text: paraLines.join(' ') });
    i++;
  }

  if (currentSection) {
    rootBlocks.push(currentSection);
  }

  return rootBlocks;
}

/**
 * Utility to render inline markdown styles (**bold**, *italic*, `code`).
 */
export function renderInlineMarkdown(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let lastIdx = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push(text.substring(lastIdx, match.index));
    }

    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={match.index} style={{ color: '#fff', fontWeight: 600 }}>
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('*') && token.endsWith('*')) {
      parts.push(
        <em key={match.index} style={{ color: '#e4e4e7', fontStyle: 'italic' }}>
          {token.slice(1, -1)}
        </em>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code
          key={match.index}
          className="font-mono"
          style={{
            background: 'rgba(255, 255, 255, 0.08)',
            color: 'var(--accent-focal-hover)',
            padding: '1px 5px',
            borderRadius: '4px',
            fontSize: '12px'
          }}
        >
          {token.slice(1, -1)}
        </code>
      );
    }

    lastIdx = regex.lastIndex;
  }

  if (lastIdx < text.length) {
    parts.push(text.substring(lastIdx));
  }

  return parts;
}
