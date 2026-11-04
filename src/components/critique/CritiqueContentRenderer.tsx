import React from 'react';
import { 
  extractScoreboard, 
  parseMarkdownToBlocks, 
  ParsedScores 
} from '../../utils/critiqueParser';
import { CritiqueScoreboardCard } from './CritiqueScoreboardCard';
import { OriginalEnglishCritiqueCard } from './OriginalEnglishCritiqueCard';
import { CritiqueBlockItem } from './CritiqueBlockItem';

// Re-export parser utilities and types for backwards compatibility
export { 
  extractScoreboard, 
  parseMarkdownToBlocks, 
  determineThemeType, 
  renderInlineMarkdown 
} from '../../utils/critiqueParser';
export type { ParsedScores, MarkdownBlock } from '../../utils/critiqueParser';
export { CritiqueScoreboardCard } from './CritiqueScoreboardCard';
export { ExecutiveSummaryCard } from './ExecutiveSummaryCard';
export { OriginalEnglishCritiqueCard } from './OriginalEnglishCritiqueCard';
export { CritiqueBlockItem } from './CritiqueBlockItem';

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
      {blocks.map((block, idx) => (
        <CritiqueBlockItem key={idx} block={block} index={idx} isCompact={isCompact} />
      ))}

      {/* 3. UniPercept 8B VQA English Original Feedback */}
      {effCritiqueEn && (
        <OriginalEnglishCritiqueCard critiqueEn={effCritiqueEn} isCompact={isCompact} />
      )}
    </div>
  );
};
