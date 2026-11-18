import React from 'react';
import { AlertTriangle, RefreshCw, Save, X } from 'lucide-react';

interface PhotoAiAnalysisViewProps {
  aiAnalysis: {
    caption?: string | null;
    tags: string[];
    aesthetic_tags?: string[];
  };
  editing: boolean;
  reindexing: boolean;
  reindexingError?: string | null;
  saving: boolean;
  captionEdit: string;
  tagsEdit: string[];
  setEditing: (editing: boolean) => void;
  setCaptionEdit: (caption: string) => void;
  setTagsEdit: (tags: string[]) => void;
  handleSave: () => void;
  handleReindex: () => void;
  onDismissReindexError?: () => void;
  handleTagClick: (tag: string) => void;
}

export const PhotoAiAnalysisView: React.FC<PhotoAiAnalysisViewProps> = ({
  aiAnalysis,
  editing,
  reindexing,
  reindexingError = null,
  saving,
  captionEdit,
  tagsEdit,
  setEditing,
  setCaptionEdit,
  setTagsEdit,
  handleSave,
  handleReindex,
  onDismissReindexError,
  handleTagClick
}) => {
  return (
    <div style={{ marginBottom: '20px', backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <h4 style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>AI 장면 묘사</h4>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={handleReindex}
            disabled={reindexing}
            style={{
              background: 'none',
              border: 'none',
              color: reindexing ? 'var(--accent-focal)' : 'var(--text-muted)',
              cursor: reindexing ? 'not-allowed' : 'pointer',
              opacity: reindexing ? 0.75 : 1,
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="AI 분석 다시 실행"
          >
            <RefreshCw size={12} className={reindexing ? 'spin' : ''} />
            <span>{reindexing ? '재분석 중...' : '재분석'}</span>
          </button>
          {!editing ? (
            <button
              onClick={() => setEditing(true)}
              disabled={reindexing}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-focal)',
                cursor: reindexing ? 'not-allowed' : 'pointer',
                opacity: reindexing ? 0.45 : 1,
                fontSize: '12px',
                fontWeight: 500,
              }}
            >
              편집
            </button>
          ) : (
            <button
              onClick={handleSave}
              disabled={saving || reindexing}
              style={{
                background: 'var(--accent-focal)',
                border: 'none',
                color: '#fff',
                cursor: saving || reindexing ? 'not-allowed' : 'pointer',
                opacity: saving || reindexing ? 0.65 : 1,
                fontSize: '12px',
                padding: '3px 10px',
                borderRadius: '4px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <Save size={12} /> {saving ? '저장 중...' : '저장'}
            </button>
          )}
        </div>
      </div>

      {reindexingError && (
        <div
          role="alert"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
            padding: '8px 10px',
            marginBottom: '10px',
            borderRadius: '6px',
            border: '1px solid rgba(225, 29, 72, 0.4)',
            backgroundColor: 'rgba(225, 29, 72, 0.1)',
            color: '#fda4af',
            fontSize: '11.5px',
            lineHeight: 1.4,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0 }}>
            <AlertTriangle size={13} color="var(--accent-focal-hover)" style={{ flexShrink: 0 }} />
            <span style={{ wordBreak: 'break-word' }}>{reindexingError}</span>
          </div>
          {onDismissReindexError && (
            <button
              type="button"
              onClick={onDismissReindexError}
              title="오류 닫기"
              style={{
                background: 'none',
                border: 'none',
                color: '#fda4af',
                cursor: 'pointer',
                padding: '2px',
                display: 'flex',
                alignItems: 'center',
                flexShrink: 0,
              }}
            >
              <X size={12} />
            </button>
          )}
        </div>
      )}

      {!editing ? (
        <div>
          <p style={{ fontSize: '13px', color: '#d4d4d8', lineHeight: 1.6, margin: '0 0 12px 0', background: 'var(--bg-canvas)', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--border-subtle)', wordBreak: 'keep-all' }}>
            {aiAnalysis.caption || "생성된 캡션이 없습니다."}
          </p>
          
          {/* Keyword Tags */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
            {aiAnalysis.tags.map((tag, idx) => (
              <span
                key={idx}
                onClick={() => handleTagClick(tag)}
                style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)', padding: '3px 8px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer', whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center' }}
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
                  style={{ background: 'var(--accent-focal-subtle)', color: 'var(--accent-focal-hover)', border: '1px solid rgba(225, 29, 72, 0.25)', padding: '3px 8px', borderRadius: '4px', fontSize: '11px', whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center' }}
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
