import React from 'react';

export {
  extractScoreboard,
  determineThemeType,
  parseMarkdownToBlocks,
  type ParsedScores,
  type MarkdownBlock,
  type SectionThemeType,
} from './critiqueMarkdownParser';

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
            fontSize: '12px',
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
