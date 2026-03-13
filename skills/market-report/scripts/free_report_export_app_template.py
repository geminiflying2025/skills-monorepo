#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from typing import Any


TS_TYPES = dedent(
    """
    export type FreeReportBlock = {
      title: string;
      claim?: string;
      summary?: string;
      bullets?: string[];
      score?: number | null;
      scenarios?: Array<[string, number]>;
    };

    export type FreeReportSection = {
      title: string;
      lead?: string;
      blocks: FreeReportBlock[];
    };

    export type FreeReportCard = {
      type: string;
      title?: string;
      sectionTitle?: string;
      claim?: string;
      summary?: string;
      bullets?: string[];
      headline?: string;
      highlights?: string[];
      visualType?: string;
      visualData?: any;
    };

    export type FreeReportBrief = {
      title: string;
      summary: string[];
      userIntent?: string;
      contentType?: string;
      layoutFamily?: string;
      visualPriority?: string;
      hero?: FreeReportCard;
      cards: FreeReportCard[];
      sections: FreeReportSection[];
      referenceImages?: string[];
    };
    """
).strip() + "\n"


APP_TEMPLATE = dedent(
    """
    import React, { useMemo, useRef } from 'react';
    import { toPng } from 'html-to-image';
    import { FREE_REPORT_BRIEF } from './constants';

    const ACCENTS = ['#2F5BEA', '#18B3A4', '#F0A51A', '#0F204A', '#8E6DFF'];

    function accentFor(index: number) {
      return ACCENTS[index % ACCENTS.length];
    }

    function normalizeItems(items: any[] | undefined) {
      return (items || []).map((item) => {
        if (typeof item === 'string') return { label: item, value: '' };
        return { label: item.label || '', value: item.value ?? '' };
      });
    }

    function SvgConstellation({ items, accent }: { items: any[]; accent: string }) {
      return (
        <svg viewBox="0 0 420 120" className="h-[120px] w-full">
          {items.slice(0, 4).map((item, index) => {
            const x = 60 + index * 95;
            const y = index % 2 === 0 ? 35 : 70;
            return (
              <g key={index}>
                {index > 0 ? <line x1={x - 60} y1={index % 2 === 0 ? 70 : 35} x2={x} y2={y} stroke="rgba(255,255,255,0.35)" strokeWidth="2" /> : null}
                <circle cx={x} cy={y} r="13" fill={accent} />
                <text x={x} y={108} textAnchor="middle" fontSize="11" fill="#CBD5E1">{(item.label || '').slice(0, 8)}</text>
              </g>
            );
          })}
        </svg>
      );
    }

function SvgEditorialScoreDots({ score, accent, label }: { score?: number; accent: string; label?: string }) {
      const active = Math.max(1, Math.min(5, Math.round((score || 60) / 20)));
      return (
        <svg viewBox="0 0 420 120" className="h-[120px] w-full">
          <rect x="0" y="0" width="420" height="120" rx="20" fill="#F7F9FC" />
          <text x="18" y="24" fontSize="12" fill="#64748B">{label || '评分强度'}</text>
          <rect x="292" y="14" width="94" height="26" rx="13" fill="#E7EFFC" />
          <text x="339" y="31" textAnchor="middle" fontSize="11" fill="#2F5BEA">结论偏强</text>
          {['基本面','政策面','外部扰动','结构分化'].map((item, row) => (
            <g key={row} transform={`translate(18, ${48 + row * 16})`}>
              <text x="0" y="10" fontSize="10" fill="#64748B">{item}</text>
              {Array.from({ length: 5 }).map((_, index) => (
                <circle key={index} cx={170 + index * 24} cy={6} r="6.5" fill={index < Math.max(1, active - (row % 2)) ? accent : '#D7DFEA'} />
              ))}
            </g>
          ))}
        </svg>
      );
    }

function SvgTrendBand({ start, end, accent, label }: { start?: number; end?: number; accent: string; label?: string }) {
      return (
        <svg viewBox="0 0 420 120" className="h-[120px] w-full">
          <rect x="0" y="0" width="420" height="120" rx="20" fill="#F7F9FC" />
          <text x="18" y="22" fontSize="12" fill="#64748B">{label || '区间示意'}</text>
          <rect x="44" y="58" width="320" height="18" rx="9" fill="#DFE7F1" />
          <rect x={44 + (start || 24) * 2.2} y="58" width={Math.max(70, ((end || 78) - (start || 24)) * 2.2)} height="18" rx="9" fill="#CFE0FF" />
          <circle cx={44 + ((start || 24) + (end || 78)) * 1.1} cy="67" r="8" fill={accent} />
          <path d="M 44 46 C 110 28, 180 76, 250 54 S 340 44, 364 48" stroke={accent} strokeWidth="3" fill="none" />
          <text x="40" y="98" fontSize="10" fill="#64748B">低位</text>
          <text x="356" y="98" fontSize="10" fill="#64748B">高位</text>
        </svg>
      );
    }

function SvgComparison({ items, accent }: { items: any[]; accent: string }) {
      return (
        <svg viewBox="0 0 420 120" className="h-[120px] w-full">
          <rect x="0" y="0" width="420" height="120" rx="20" fill="#F7F9FC" />
          {items.slice(0, 4).map((item, index) => {
            const x = 30 + index * 92;
            const value = Number(item.value || 60);
            const h = 24 + value;
            return (
              <g key={index}>
                <rect x={x} y={94 - h} width="42" height={h} rx="12" fill={index % 2 === 0 ? accent : '#AFC4FF'} />
                <text x={x + 21} y="110" textAnchor="middle" fontSize="11" fill="#64748B">{(item.label || '').slice(0, 6)}</text>
              </g>
            );
          })}
        </svg>
      );
}

function SvgMiniFlow({ steps, accent }: { steps: string[]; accent: string }) {
      return (
        <svg viewBox="0 0 420 120" className="h-[120px] w-full">
          <rect x="0" y="0" width="420" height="120" rx="20" fill="#F7F9FC" />
          <defs>
            <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="#94A3B8" />
            </marker>
          </defs>
          {steps.slice(0, 3).map((step, index) => {
            const x = 18 + index * 130;
            return (
              <g key={index}>
                <rect x={x} y="36" width="110" height="46" rx="16" fill={index === 1 ? accent : '#E9EFF8'} />
                <text x={x + 55} y="63" textAnchor="middle" fontSize="12" fill={index === 1 ? '#fff' : '#0F172A'}>
                  {(step || '').slice(0, 10)}
                </text>
                {index < 2 ? <line x1={x + 112} y1="59" x2={x + 128} y2="59" stroke="#94A3B8" strokeWidth="2.5" markerEnd="url(#arrow)" /> : null}
                {index < 2 ? <text x={x + 64} y="100" textAnchor="middle" fontSize="10" fill="#64748B">驱动</text> : null}
              </g>
            );
          })}
        </svg>
      );
}

function SvgPositionMap({ items, accent }: { items: any[]; accent: string }) {
  return (
    <svg viewBox="0 0 420 130" className="h-[130px] w-full">
      <rect x="20" y="10" width="380" height="104" rx="22" fill="#F7F9FC" />
      <rect x="58" y="18" width="280" height="86" rx="18" fill="#F1F5FA" />
      <line x1="198" y1="18" x2="198" y2="104" stroke="#CBD5E1" strokeWidth="2" />
      <line x1="58" y1="61" x2="338" y2="61" stroke="#CBD5E1" strokeWidth="2" />
      <text x="198" y="30" textAnchor="middle" fontSize="10" fill="#94A3B8">高景气</text>
      <text x="198" y="98" textAnchor="middle" fontSize="10" fill="#94A3B8">低景气</text>
      <text x="198" y="118" textAnchor="middle" fontSize="11" fill="#64748B">风格位置</text>
      {items.slice(0, 3).map((item, index) => {
        const positions = [[150, 44], [230, 72], [272, 48]];
        const [x, y] = positions[index] || [160 + index * 30, 50];
        return (
          <g key={index}>
            <circle cx={x} cy={y} r="10" fill={index === 0 ? accent : index === 1 ? '#0F204A' : '#9DB8FF'} />
            <text x={x + 14} y={y + 4} fontSize="11" fill="#475569">{(item.label || '').slice(0, 6)}</text>
          </g>
        );
      })}
    </svg>
  );
}

function SvgDynamicDiagram({ data, accent }: { data: any; accent: string }) {
  const nodes = data.nodes || [];
  const edges = data.edges || [];
  const positions = [
    [84, 44],
    [220, 34],
    [164, 94],
    [316, 84],
  ];
  return (
    <svg viewBox="0 0 420 130" className="h-[130px] w-full">
      <rect x="0" y="0" width="420" height="130" rx="20" fill="#F7F9FC" />
      {edges.map((edge: any, index: number) => {
        const from = positions[edge.from] || positions[0];
        const to = positions[edge.to] || positions[1];
        return (
          <g key={index}>
            <path
              d={`M ${from[0]} ${from[1]} C ${(from[0] + to[0]) / 2} ${from[1] - 24}, ${(from[0] + to[0]) / 2} ${to[1] + 24}, ${to[0]} ${to[1]}`}
              stroke={accent}
              strokeWidth="2.5"
              fill="none"
            />
            <text x={(from[0] + to[0]) / 2} y={(from[1] + to[1]) / 2 - 8} textAnchor="middle" fontSize="10" fill="#64748B">
              {edge.label || ''}
            </text>
          </g>
        );
      })}
      {nodes.map((node: any, index: number) => {
        const [x, y] = positions[index] || [80 + index * 60, 60];
        return (
          <g key={index}>
            <circle cx={x} cy={y} r="18" fill={index % 2 === 0 ? accent : '#D7E3FF'} />
            <text x={x} y={y + 4} textAnchor="middle" fontSize="10" fill={index % 2 === 0 ? '#fff' : '#0F172A'}>
              {(node.label || '').slice(0, 4)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function SvgSignalIcons({ items, accent }: { items: any[]; accent: string }) {
      return (
        <svg viewBox="0 0 420 120" className="h-[120px] w-full">
          <rect x="0" y="0" width="420" height="120" rx="20" fill="#F7F9FC" />
          {items.slice(0, 4).map((item, index) => {
            const x = 28 + index * 96;
            const fill = item.tone === 'warning' ? '#F59E0B' : index % 2 === 0 ? accent : '#C8D6F9';
            return (
              <g key={index}>
                <rect x={x} y="28" width="42" height="42" rx="12" fill={fill} />
                <rect x={x - 8} y="82" width="58" height="20" rx="10" fill="#E9EEF5" />
                <text x={x + 21} y="95" textAnchor="middle" fontSize="10" fill="#64748B">{(item.label || '').slice(0, 6)}</text>
              </g>
            );
          })}
        </svg>
      );
    }

function SvgFlowBars({ items, accent }: { items: any[]; accent: string }) {
      return (
        <svg viewBox="0 0 420 120" className="h-[120px] w-full">
          <rect x="0" y="0" width="420" height="120" rx="20" fill="#F7F9FC" />
          {items.slice(0, 5).map((item, index) => {
            const x = 26 + index * 72;
            const h = Number(item.value || 40);
            return (
              <g key={index}>
                <rect x={x} y={92 - h} width="26" height={h} rx="10" fill="#BFD0FF" />
                <text x={x + 13} y="110" textAnchor="middle" fontSize="10" fill="#64748B">{(item.label || '').slice(0, 4)}</text>
              </g>
            );
          })}
          <path d="M 26 52 C 98 40, 170 78, 242 54 S 360 38, 392 30" stroke={accent} strokeWidth="3" fill="none" />
        </svg>
      );
    }

function SvgDotMatrix({ items, accent }: { items: any[]; accent: string }) {
      return (
        <svg viewBox="0 0 420 120" className="h-[120px] w-full">
          <rect x="0" y="0" width="420" height="120" rx="20" fill="#F7F9FC" />
          {items.slice(0, 4).map((item, row) => {
            const active = Number(item.value || 2);
            return (
              <g key={row} transform={`translate(0, ${10 + row * 26})`}>
                <text x="0" y="12" fontSize="12" fill="#64748B">{item.label || `Item ${row + 1}`}</text>
                {Array.from({ length: 6 }).map((_, col) => (
                  <circle key={col} cx={190 + col * 28} cy={8} r="8" fill={col < active ? accent : '#D7DFEA'} />
                ))}
              </g>
            );
          })}
        </svg>
      );
    }

    function SvgVisual({ card, accent }: { card: any; accent: string }) {
      const data = card.visualData || {};
      if (card.visualType === 'constellation') return <SvgConstellation items={data.items || []} accent={accent} />;
      if (card.visualType === 'score-dots') return <SvgEditorialScoreDots score={data.score} label={data.label} accent={accent} />;
      if (card.visualType === 'range-band') return <SvgTrendBand start={data.start} end={data.end} label={data.label} accent={accent} />;
      if (card.visualType === 'comparison-strip') return <SvgComparison items={data.items || []} accent={accent} />;
      if (card.visualType === 'mini-flow') return <SvgMiniFlow steps={data.steps || []} accent={accent} />;
      if (card.visualType === 'position-map') return <SvgPositionMap items={data.items || []} accent={accent} />;
      if (card.visualType === 'dynamic-svg') return <SvgDynamicDiagram data={data} accent={accent} />;
      if (card.visualType === 'signal-icons') return <SvgSignalIcons items={data.items || []} accent={accent} />;
      if (card.visualType === 'flow-bars') return <SvgFlowBars items={data.items || []} accent={accent} />;
      if (card.visualType === 'probability-strip') return <SvgComparison items={data.items || []} accent={accent} />;
      return <SvgDotMatrix items={data.items || []} accent={accent} />;
    }

    function TopicCard({ card, index }: { card: any; index: number }) {
      const accent = accentFor(index);
      return (
        <article className="rounded-[28px] border border-slate-200 bg-white px-8 py-8 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
          <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">{card.sectionTitle || 'TOPIC'}</div>
          <h3 className="mt-3 text-[32px] font-black leading-[1.2] tracking-[-0.03em] text-slate-950">{card.title}</h3>
          {card.claim ? <div className="mt-4 text-[22px] font-semibold leading-[1.55] text-slate-900">{card.claim}</div> : null}
          {card.bullets?.length ? (
            <div className="mt-5 space-y-3">
              {card.bullets.slice(0, 4).map((item: string, itemIndex: number) => (
                <div key={itemIndex} className="flex items-start gap-3 text-[17px] leading-8 text-slate-600">
                  <div className="mt-[11px] h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: accent }} />
                  <div>{item}</div>
                </div>
              ))}
            </div>
          ) : null}
          <div className="mt-6 rounded-[22px] bg-slate-50 px-5 py-5">
            <SvgVisual card={card} accent={accent} />
          </div>
        </article>
      );
    }

    export default function App() {
      const captureRef = useRef<HTMLDivElement>(null);

      const exportCapture = async () => {
        if (captureRef.current === null) return null;
        return toPng(captureRef.current, {
          cacheBust: true,
          backgroundColor: '#EEF2F6',
          pixelRatio: 2,
          filter: (node: any) => {
            if (node.classList?.contains('no-capture')) return false;
            return true;
          }
        });
      };

      React.useEffect(() => {
        (window as any).__MARKET_REPORT_EXPORT__ = exportCapture;
        return () => {
          delete (window as any).__MARKET_REPORT_EXPORT__;
        };
      }, []);

      const cards = useMemo(() => FREE_REPORT_BRIEF.cards || [], []);
      const hero = cards[0];
      const remainingCards = cards.slice(1);
      const summary = FREE_REPORT_BRIEF.summary || [];
      const lead = summary[0] || hero?.headline || '';
      const highlights = summary.slice(1, 4);

      return (
        <div className="min-h-screen bg-[#EEF2F6] px-8 py-10 text-slate-900">
          <div ref={captureRef} className="mx-auto w-[1320px] overflow-hidden rounded-[28px] bg-[#EEF2F6] shadow-[0_35px_100px_rgba(15,23,42,0.12)]">
            <section className="rounded-t-[28px] bg-[#12233F] px-14 pb-12 pt-12 text-white">
              <div className="text-[12px] font-bold tracking-[0.24em] text-slate-300">FREE REPORT / VIEWPOINT + SCHEMATIC</div>
              <h1 className="mt-4 text-[62px] font-black leading-[1.02] tracking-[-0.05em]">{FREE_REPORT_BRIEF.title}</h1>
              <div className="mt-5 max-w-[980px] text-[24px] font-semibold leading-[1.6] text-white/95">{lead}</div>
              {highlights.length ? (
                <div className="mt-8 flex flex-wrap gap-3">
                  {highlights.map((item, index) => (
                    <div key={index} className="rounded-full bg-white/10 px-4 py-2 text-[14px] font-semibold text-white/92">
                      {item}
                    </div>
                  ))}
                </div>
              ) : null}
              {hero ? (
                <div className="mt-8 rounded-[24px] bg-white/8 px-6 py-5">
                  <SvgVisual card={hero} accent="#F2C94C" />
                </div>
              ) : null}
            </section>

            <main className="space-y-5 bg-[#EEF2F6] px-10 py-8">
              {remainingCards.map((card, index) => {
                if (card.type === 'section-header-card') {
                  return (
                    <section key={index} className="pt-4">
                      <div className="inline-flex items-center gap-3 rounded-full bg-[#12233F] px-4 py-2 text-white">
                        <div className="h-3 w-3 rounded-full bg-[#F2C94C]" />
                        <div className="text-[18px] font-black tracking-[-0.02em]">{card.title}</div>
                      </div>
                    </section>
                  );
                }
                return <TopicCard key={index} card={card} index={index} />;
              })}
            </main>
          </div>
        </div>
      );
    }
    """
).strip() + "\n"


CONSTANTS_TEMPLATE = "import {{ FreeReportBrief }} from './types';\n\nexport const FREE_REPORT_BRIEF: FreeReportBrief = {payload};\n"


def write_free_report_react_app(app_dir: Path, brief: dict[str, Any]) -> None:
    src_dir = app_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(brief, ensure_ascii=False, indent=2)
    (src_dir / "constants.ts").write_text(CONSTANTS_TEMPLATE.format(payload=payload), encoding="utf-8")
    (src_dir / "types.ts").write_text(TS_TYPES, encoding="utf-8")
    (src_dir / "App.tsx").write_text(APP_TEMPLATE, encoding="utf-8")
