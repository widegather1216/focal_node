import React from 'react';
import { Award, Camera, HelpCircle, Info, Layers, Sliders, Sparkles } from 'lucide-react';

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  code: string;
  color: string;
  description: string;
}

const WEIGHT_ROWS = [
  {
    mode: '얕은 심도 인물 / 감성',
    condition: 'F ≤ 2.8',
    iaa: '65%',
    iqa: '25%',
    ista: '10%',
    purpose: '얕은 심도(보케)로 인한 질감 점수 저하 방어',
  },
  {
    mode: '팬포커스 풍경 / 건축',
    condition: 'F ≥ 5.6',
    iaa: '45%',
    iqa: '30%',
    ista: '25%',
    purpose: '전체 화면의 디테일과 텍스처 해상력 균형 반영',
  },
  {
    mode: '야경 / 스트리트 스냅',
    condition: 'ISO ≥ 1600',
    iaa: '70%',
    iqa: '20%',
    ista: '10%',
    purpose: '고감도 노이즈보다 순간의 분위기와 서사 우선',
  },
  {
    mode: '일반 스냅 (표준 모드)',
    condition: '그 외 / EXIF 누락',
    iaa: '55%',
    iqa: '30%',
    ista: '15%',
    purpose: '범용적인 시각적 균형 기준 적용',
  },
];

const MetricCard: React.FC<MetricCardProps> = ({ icon, label, code, color, description }) => (
  <div
    style={{
      backgroundColor: 'rgba(255, 255, 255, 0.03)',
      border: '1px solid var(--border-subtle)',
      borderRadius: '8px',
      padding: '12px 14px',
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
    }}
  >
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        {icon}
        <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{label}</span>
      </div>
      <span
        className="font-mono"
        style={{
          fontSize: '11px',
          fontWeight: 700,
          color,
          backgroundColor: 'rgba(255, 255, 255, 0.05)',
          padding: '2px 6px',
          borderRadius: '4px',
        }}
      >
        {code}
      </span>
    </div>
    <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.55 }}>{description}</p>
  </div>
);

const AdaptiveWeightsTable: React.FC = () => (
  <div style={{ overflowX: 'auto', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
      <thead>
        <tr style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', borderBottom: '1px solid var(--border-subtle)' }}>
          <th style={{ padding: '8px 10px', color: 'var(--text-primary)', fontWeight: 600 }}>촬영 모드</th>
          <th style={{ padding: '8px 10px', color: 'var(--text-secondary)', fontWeight: 600 }}>판정 조건</th>
          <th style={{ padding: '8px 10px', color: 'var(--accent-focal-hover)', fontWeight: 600 }}>미학 (IAA)</th>
          <th style={{ padding: '8px 10px', color: 'var(--accent-focal)', fontWeight: 600 }}>화질 (IQA)</th>
          <th style={{ padding: '8px 10px', color: 'var(--accent-focal-deep)', fontWeight: 600 }}>질감 (ISTA)</th>
          <th style={{ padding: '8px 10px', color: 'var(--text-secondary)', fontWeight: 600 }}>설계 의도</th>
        </tr>
      </thead>
      <tbody>
        {WEIGHT_ROWS.map((row, idx) => (
          <tr
            key={row.mode}
            style={{
              borderBottom: idx < WEIGHT_ROWS.length - 1 ? '1px solid rgba(255, 255, 255, 0.04)' : 'none',
              backgroundColor: idx % 2 === 1 ? 'rgba(255, 255, 255, 0.015)' : 'transparent',
            }}
          >
            <td style={{ padding: '8px 10px', fontWeight: 600, color: 'var(--text-primary)' }}>{row.mode}</td>
            <td style={{ padding: '8px 10px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{row.condition}</td>
            <td style={{ padding: '8px 10px', color: 'var(--accent-focal-hover)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{row.iaa}</td>
            <td style={{ padding: '8px 10px', color: 'var(--accent-focal)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{row.iqa}</td>
            <td style={{ padding: '8px 10px', color: 'var(--accent-focal-deep)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{row.ista}</td>
            <td style={{ padding: '8px 10px', color: 'var(--text-muted)', fontSize: '11.5px' }}>{row.purpose}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

export const ScoringGuideContent: React.FC = () => (
  <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <HelpCircle size={15} color="var(--accent-focal)" />
        <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
          1. 3대 지각 평가 지표 (Perceptual Metrics)
        </h3>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
        <MetricCard
          icon={<Sparkles size={14} color="var(--accent-focal-hover)" />}
          label="미학 & 구도 지수"
          code="IAA"
          color="var(--accent-focal-hover)"
          description="시각적 감동, 구도 조화, 빛과 색채의 예술적 표현력을 0~100점으로 측정합니다."
        />
        <MetricCard
          icon={<Camera size={14} color="var(--accent-focal)" />}
          label="화질 & 광학 지수"
          code="IQA"
          color="var(--accent-focal)"
          description="광학적 선명도, 초점 정확도, 저조도 노이즈 및 왜곡 억제력을 측정합니다."
        />
        <MetricCard
          icon={<Layers size={14} color="var(--accent-focal-deep)" />}
          label="구조 & 질감 지수"
          code="ISTA"
          color="var(--accent-focal-deep)"
          description="피사체 표면 질감, 텍스처 디테일, 공간 구조의 복잡도를 정량화합니다."
        />
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '8px',
          backgroundColor: 'rgba(225, 29, 72, 0.08)',
          borderLeft: '3px solid var(--accent-focal)',
          padding: '10px 12px',
          borderRadius: '0 6px 6px 0',
          fontSize: '11.5px',
          color: 'var(--text-secondary)',
          lineHeight: 1.55,
        }}
      >
        <Info size={14} color="var(--accent-focal)" style={{ flexShrink: 0, marginTop: '2px' }} />
        <span>
          <strong style={{ color: 'var(--text-primary)' }}>ISTA 해석 주의: </strong>
          ISTA는 화질의 우수성이 아니라 <strong>피사체의 텍스처 및 구조적 복잡 밀도</strong>를 측정합니다.
          따라서 얕은 심도의 보케(배경 흐림) 사진이나 미니멀한 단색 배경 사진은 점수가 자연스럽게 낮게 산출됩니다.
        </span>
      </div>
    </div>

    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Sliders size={15} color="var(--accent-focal)" />
        <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
          2. EXIF 기반 4대 적응형 가중치 분배
        </h3>
      </div>
      <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
        사진의 촬영 파라미터(조리개 F값, 감도 ISO)를 감지하여 장르와 기법에 맞게 가중치를 동적으로 최적화합니다.
      </p>
      <AdaptiveWeightsTable />
    </div>

    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Award size={15} color="var(--accent-focal)" />
        <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
          3. 미학적 탁월성 보너스 (Aesthetic Excellence Bonus)
        </h3>
      </div>

      <div
        style={{
          backgroundColor: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '8px',
          padding: '12px 14px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
          미학(IAA)이 <strong>75점 이상</strong>이고 기계적 화질(IQA)보다 높을 때,
          사진의 감성과 예술적 서사가 노이즈나 모션 블러 등의 광학적 한계를 상쇄하는 보너스를 가산합니다.
        </p>

        <div
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            padding: '8px 12px',
            borderRadius: '6px',
            fontFamily: 'var(--font-mono)',
            fontSize: '11.5px',
            color: 'var(--accent-focal-hover)',
            border: '1px solid rgba(225, 29, 72, 0.2)',
          }}
        >
          Δ_aesthetic = (IAA - IQA) × 0.25 × (IAA / 100)
        </div>

        <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
          * 최종 종합 평점은 가중 합산 기저 점수와 보너스를 합산한 후 0~100점으로 정수 클램핑됩니다.
        </span>
      </div>
    </div>
  </div>
);
