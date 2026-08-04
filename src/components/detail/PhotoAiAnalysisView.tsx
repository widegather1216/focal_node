import React from 'react';
import { RefreshCw, Save } from 'lucide-react';

interface PhotoAiAnalysisViewProps {
  aiAnalysis: {
    caption?: string | null;
    tags: string[];
    aesthetic_tags?: string[];
  };
  editing: boolean;
  reindexing: boolean;
  saving: boolean;
  captionEdit: string;
  tagsEdit: string[];
  setEditing: (editing: boolean) => void;
  setCaptionEdit: (caption: string) => void;
  setTagsEdit: (tags: string[]) => void;
  handleSave: () => void;
  handleReindex: () => void;
  handleTagClick: (tag: string) => void;
}

export const PhotoAiAnalysisView: React.FC<PhotoAiAnalysisViewProps> = ({
  aiAnalysis,
  editing,
  reindexing,
  saving,
  captionEdit,
  tagsEdit,
  setEditing,
  setCaptionEdit,
  setTagsEdit,
  handleSave,
  handleReindex,
  handleTagClick
}) => {
  return (
    <div style={{ marginBottom: '20px', backgroundColor: '#18181b', borderRadius: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <h4 style={{ margin: 0, fontSize: '13px', color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.05em' }}>AI 메타데이터 묘사</h4>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={handleReindex}
            disabled={reindexing}
            style={{ background: 'none', border: 'none', color: '#a1a1aa', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}
            title="AI 분석 다시 실행"
          >
            <RefreshCw size={12} className={reindexing ? 'spin' : ''} /> Re-index
          </button>
          {!editing ? (
            <button
              onClick={() => setEditing(true)}
              style={{ background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer', fontSize: '12px' }}
            >
              편집
            </button>
          ) : (
            <button
              onClick={handleSave}
              disabled={saving}
              style={{ background: '#38bdf8', border: 'none', color: '#000', cursor: 'pointer', fontSize: '12px', padding: '2px 8px', borderRadius: '4px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}
            >
              <Save size={12} /> {saving ? '저장 중...' : '저장'}
            </button>
          )}
        </div>
      </div>

      {!editing ? (
        <div>
          <p style={{ fontSize: '13px', color: '#d4d4d8', lineHeight: 1.5, margin: '0 0 12px 0', background: '#09090b', padding: '10px 12px', borderRadius: '6px' }}>
            {aiAnalysis.caption || "생성된 캡션이 없습니다."}
          </p>
          
          {/* Keyword Tags */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
            {aiAnalysis.tags.map((tag, idx) => (
              <span
                key={idx}
                onClick={() => handleTagClick(tag)}
                style={{ background: '#27272a', color: '#e4e4e7', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
              >
                #{tag}
              </span>
            ))}
          </div>

          {/* Aesthetic Tags */}
          {aiAnalysis.aesthetic_tags && aiAnalysis.aesthetic_tags.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
              {aiAnalysis.aesthetic_tags.map((tag, idx) => (
                <span
                  key={idx}
                  style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.3)', padding: '3px 8px', borderRadius: '4px', fontSize: '11px' }}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <textarea
            value={captionEdit}
            onChange={(e) => setCaptionEdit(e.target.value)}
            style={{ background: '#09090b', border: '1px solid #3f3f46', color: '#fff', padding: '8px', borderRadius: '4px', fontSize: '13px', minHeight: '80px', width: '100%', boxSizing: 'border-box' }}
          />
          <input
            type="text"
            value={tagsEdit.join(', ')}
            onChange={(e) => setTagsEdit(e.target.value.split(',').map(t => t.trim()).filter(Boolean))}
            placeholder="태그 (쉼표로 구분)"
            style={{ background: '#09090b', border: '1px solid #3f3f46', color: '#fff', padding: '8px', borderRadius: '4px', fontSize: '12px', width: '100%', boxSizing: 'border-box' }}
          />
        </div>
      )}
    </div>
  );
};
