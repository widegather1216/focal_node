export interface ParsedScores {
  overall: number | null;
  iaa: number | null;
  iqa: number | null;
  ista: number | null;
}

export type SectionThemeType = 'aesthetic' | 'defect' | 'advice' | 'camera' | 'structure' | 'general';

export type MarkdownBlock =
  | { type: 'executive_summary'; summary: string }
  | { type: 'section'; level: number; numberPrefix?: string; title: string; themeType: SectionThemeType; children: MarkdownBlock[] }
  | { type: 'paragraph'; text: string }
  | { type: 'bullet_list'; items: string[] }
  | { type: 'ordered_list'; items: string[] }
  | { type: 'blockquote'; text: string }
  | { type: 'table'; headers: string[]; rows: string[][] }
  | { type: 'code_block'; language: string; code: string }
  | { type: 'divider' };

const THEME_RULES: ReadonlyArray<{ type: SectionThemeType; keywords: string[] }> = [
  { type: 'defect', keywords: ['결함', '왜곡', '실책', '보완', '취약', '🔍', '⚠️'] },
  { type: 'advice', keywords: ['조언', '가이드라인', '솔루션', '재촬영', '개선', '💡', '🚀'] },
  { type: 'aesthetic', keywords: ['미학', 'iaa', '장점', '개성', '🎨', '🌟'] },
  { type: 'structure', keywords: ['구조', '질감', 'ista', '재질', '텍스처'] },
  { type: 'camera', keywords: ['화질', '광학', 'iqa', 'exif', '장비', '카메라', '습관', '📷'] },
];

export function extractScoreboard(text: string): { scores: ParsedScores | null; remainingText: string } {
  const scoreboardRegex = /\[(?:📊\s*)?6-Way\s*앙상블\s*비평\s*스코어보드\]([\s\S]*?)(?=(?:\n\s*#{1,4}\s*|\n\s*\d+\.\s*\[|\n\s*>\s*|$))/i;
  const match = text.match(scoreboardRegex);

  if (!match) {
    const fallbackMatch = text.match(/\[품질\/미학\s*점수:\s*(\d+)점/i);
    if (!fallbackMatch) return { scores: null, remainingText: text };
    return {
      scores: { overall: parseInt(fallbackMatch[1], 10), iaa: null, iqa: null, ista: null },
      remainingText: text.replace(fallbackMatch[0], '').trim(),
    };
  }

  const scoreBlock = match[1];
  const parseMetric = (pattern: RegExp): number | null => {
    const metricMatch = scoreBlock.match(pattern);
    return metricMatch ? parseInt(metricMatch[1], 10) : null;
  };

  return {
    scores: {
      overall: parseMetric(/최종\s*종합\s*평점:\s*(\d+)/i),
      iaa: parseMetric(/(?:미학|IAA)[\s\S]*?:\s*(\d+)/i),
      iqa: parseMetric(/(?:화질|IQA)[\s\S]*?:\s*(\d+)/i),
      ista: parseMetric(/(?:구조|질감|ISTA)[\s\S]*?:\s*(\d+)/i),
    },
    remainingText: text.replace(match[0], '').trim(),
  };
}

export function determineThemeType(text: string): SectionThemeType {
  const lower = text.toLowerCase();
  const matched = THEME_RULES.find((rule) =>
    rule.keywords.some((kw) => lower.includes(kw) || text.includes(kw))
  );
  return matched ? matched.type : 'general';
}

function tryConsumeExecutiveSummary(lines: string[], startIndex: number): { summary: string; nextIndex: number } | null {
  const trimmed = lines[startIndex].trim();
  const match = trimmed.match(/^>\s*(?:[💡🌟]\s*)?(?:\*\*)?(?:한\s*줄\s*총평|포트폴리오\s*종합\s*총평|종합\s*총평|총평)(?:\*\*)?[\s:]*(.*)/i);
  if (!match) return null;

  let summaryText = match[1].replace(/^\*\*|\*\*$/g, '').trim();
  let cursor = startIndex;
  while (cursor + 1 < lines.length && lines[cursor + 1].trim().startsWith('>')) {
    cursor++;
    summaryText += ' ' + lines[cursor].trim().replace(/^>\s*/, '');
  }
  return { summary: summaryText.trim(), nextIndex: cursor + 1 };
}

function tryParseHeadingBlock(trimmed: string): Extract<MarkdownBlock, { type: 'section' }> | null {
  if (trimmed.startsWith('```')) return null;
  const headingMatch = trimmed.match(/^(#{1,4})\s*(?:(\d+)\.\s*)?([^\n:]+):?$/) || trimmed.match(/^(\d+)\.\s*([^\n:]+):$/);
  if (!headingMatch) return null;

  const isHash = headingMatch[1].startsWith('#');
  const level = isHash ? headingMatch[1].length : 2;
  const numberPrefix = isHash ? (headingMatch[2] ? `${headingMatch[2]}.` : undefined) : `${headingMatch[1]}.`;
  let title = (isHash ? headingMatch[3] : headingMatch[2]).trim();
  if (title.startsWith('**') && title.endsWith('**')) title = title.slice(2, -2).trim();
  if (title.startsWith('[') && title.endsWith(']')) title = title.slice(1, -1).trim();

  return { type: 'section', level, numberPrefix, title, themeType: determineThemeType(title), children: [] };
}

function consumeCodeBlock(lines: string[], startIndex: number): { block: MarkdownBlock; nextIndex: number } {
  const language = lines[startIndex].trim().slice(3).trim();
  const codeLines: string[] = [];
  let cursor = startIndex + 1;
  while (cursor < lines.length && !lines[cursor].trim().startsWith('```')) {
    codeLines.push(lines[cursor]);
    cursor++;
  }
  return { block: { type: 'code_block', language, code: codeLines.join('\n') }, nextIndex: cursor + 1 };
}

function consumeTableBlock(lines: string[], startIndex: number): { block: MarkdownBlock; nextIndex: number } | null {
  const firstTrimmed = lines[startIndex].trim();
  if (!firstTrimmed.startsWith('|') || !firstTrimmed.endsWith('|')) return null;
  const tableLines: string[] = [firstTrimmed];
  let cursor = startIndex;
  while (cursor + 1 < lines.length && lines[cursor + 1].trim().startsWith('|') && lines[cursor + 1].trim().endsWith('|')) {
    cursor++;
    tableLines.push(lines[cursor].trim());
  }
  if (tableLines.length < 2) return null;
  const headers = tableLines[0].slice(1, -1).split('|').map((cell) => cell.trim());
  const rows = tableLines.slice(2).map((line) => line.slice(1, -1).split('|').map((cell) => cell.trim()));
  return { block: { type: 'table', headers, rows }, nextIndex: cursor + 1 };
}

function consumeListBlock(lines: string[], startIndex: number, isOrdered: boolean): { block: MarkdownBlock; nextIndex: number } {
  const stripPrefix = (line: string) =>
    isOrdered ? line.replace(/^\d+\.\s+/, '') : line.replace(/^[-*•]\s+/, '');
  const matchesLine = (trimmedLine: string) =>
    isOrdered ? /^\d+\.\s+/.test(trimmedLine) && !trimmedLine.endsWith(':') : /^[-*•]\s+/.test(trimmedLine);

  const items: string[] = [stripPrefix(lines[startIndex].trim())];
  let cursor = startIndex;
  while (cursor + 1 < lines.length && matchesLine(lines[cursor + 1].trim())) {
    cursor++;
    items.push(stripPrefix(lines[cursor].trim()));
  }
  return { block: { type: isOrdered ? 'ordered_list' : 'bullet_list', items }, nextIndex: cursor + 1 };
}

function isParagraphBreak(trimmedLine: string): boolean {
  return (
    !trimmedLine ||
    trimmedLine.startsWith('#') ||
    trimmedLine.startsWith('>') ||
    trimmedLine.startsWith('```') ||
    trimmedLine.startsWith('|') ||
    /^[-*•]\s+/.test(trimmedLine) ||
    /^\d+\.\s+/.test(trimmedLine) ||
    /^(\*{3,}|-{3,}|_{3,})$/.test(trimmedLine)
  );
}

function consumeParagraphOrQuote(lines: string[], startIndex: number): { block: MarkdownBlock; nextIndex: number } {
  const firstTrimmed = lines[startIndex].trim();
  if (firstTrimmed.startsWith('>')) {
    const quoteLines: string[] = [firstTrimmed.replace(/^>\s*/, '')];
    let cursor = startIndex;
    while (cursor + 1 < lines.length && lines[cursor + 1].trim().startsWith('>')) {
      cursor++;
      quoteLines.push(lines[cursor].trim().replace(/^>\s*/, ''));
    }
    return { block: { type: 'blockquote', text: quoteLines.join(' ') }, nextIndex: cursor + 1 };
  }

  const paraLines: string[] = [firstTrimmed];
  let cursor = startIndex;
  while (cursor + 1 < lines.length && !isParagraphBreak(lines[cursor + 1].trim())) {
    cursor++;
    paraLines.push(lines[cursor].trim());
  }
  return { block: { type: 'paragraph', text: paraLines.join(' ') }, nextIndex: cursor + 1 };
}

export function parseMarkdownToBlocks(text: string): MarkdownBlock[] {
  const lines = text.split('\n');
  const rootBlocks: MarkdownBlock[] = [];
  let currentSection: Extract<MarkdownBlock, { type: 'section' }> | null = null;

  const pushBlock = (block: MarkdownBlock) => {
    if (block.type === 'section') {
      if (currentSection) rootBlocks.push(currentSection);
      currentSection = block;
    } else if (currentSection) {
      currentSection.children.push(block);
    } else {
      rootBlocks.push(block);
    }
  };

  let i = 0;
  while (i < lines.length) {
    const trimmed = lines[i].trim();
    if (!trimmed) { i++; continue; }

    const summaryMatch = tryConsumeExecutiveSummary(lines, i);
    if (summaryMatch) { rootBlocks.push({ type: 'executive_summary', summary: summaryMatch.summary }); i = summaryMatch.nextIndex; continue; }

    const heading = tryParseHeadingBlock(trimmed);
    if (heading) { pushBlock(heading); i++; continue; }

    if (trimmed.startsWith('```')) { const parsed = consumeCodeBlock(lines, i); pushBlock(parsed.block); i = parsed.nextIndex; continue; }
    if (/^(\*{3,}|-{3,}|_{3,})$/.test(trimmed)) { pushBlock({ type: 'divider' }); i++; continue; }

    const tableMatch = consumeTableBlock(lines, i);
    if (tableMatch) { pushBlock(tableMatch.block); i = tableMatch.nextIndex; continue; }

    if (/^[-*•]\s+/.test(trimmed)) { const parsed = consumeListBlock(lines, i, false); pushBlock(parsed.block); i = parsed.nextIndex; continue; }
    if (/^\d+\.\s+/.test(trimmed) && !trimmed.endsWith(':')) { const parsed = consumeListBlock(lines, i, true); pushBlock(parsed.block); i = parsed.nextIndex; continue; }

    const paraOrQuote = consumeParagraphOrQuote(lines, i);
    pushBlock(paraOrQuote.block);
    i = paraOrQuote.nextIndex;
  }

  if (currentSection) rootBlocks.push(currentSection);
  return rootBlocks;
}
