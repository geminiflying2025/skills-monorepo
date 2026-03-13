#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from typing import Any


TS_TYPES = dedent(
    """
    export type FreeReportBlock = {
      type: string;
      title: string;
      claim?: string;
      summary?: string;
      bullets?: string[];
    };

    export type FreeReportSection = {
      title: string;
      lead?: string;
      blocks: FreeReportBlock[];
    };

    export type FreeReportBrief = {
      title: string;
      summary: string[];
      userIntent?: string;
      contentType?: string;
      layoutFamily?: string;
      visualPriority?: string;
      hero?: {
        type: string;
        eyebrow?: string;
        headline: string;
        highlights?: string[];
        claim?: string;
        visualType?: string;
        visualData?: any;
      };
      cards: Array<{
        type: string;
        title?: string;
        sectionTitle?: string;
        claim?: string;
        summary?: string;
        bullets?: string[];
        items?: Array<{ label?: string; value?: string | number } | string>;
        emphasis?: string;
        headline?: string;
        highlights?: string[];
        visualType?: string;
        visualData?: any;
      }>;
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

    const ACCENTS = ['#2563EB', '#14B8A6', '#7C3AED', '#F59E0B', '#EC4899'];

    function splitHighlights(items: string[]) {
      const lead = items[0] || '';
      const rest = items.slice(1, 4);
      return { lead, rest };
    }

    function normalizeItems(items: Array<{ label?: string; value?: string | number } | string> | undefined) {
      return (items || []).map((item) => {
        if (typeof item === 'string') {
          return { label: item, value: '' };
        }
        return { label: item.label || '', value: item.value ?? '' };
      });
    }

    function accentFor(index: number) {
      return ACCENTS[index % ACCENTS.length];
    }

    function cardSpan(type: string, emphasis?: string) {
      if (type === 'hero-summary-card') return 'col-span-12';
      if (type === 'section-header-card') return 'col-span-12';
      if (type === 'comparison-card') return 'col-span-12';
      if (type === 'signal-card') return 'col-span-5';
      if (type === 'mini-bar-card' || type === 'probability-card') return 'col-span-6';
      if (emphasis === 'hero') return 'col-span-8';
      return 'col-span-4';
    }

    function SvgDots({ items, accent }: { items: Array<{ label?: string; value?: number }>; accent: string }) {
      return (
        <svg viewBox="0 0 320 120" className="h-[120px] w-full">
          {items.slice(0, 4).map((item, row) => {
            const active = Number(item.value || 2);
            return (
              <g key={row} transform={`translate(0, ${10 + row * 26})`}>
                <text x="0" y="12" fontSize="11" fill="#64748B">{item.label || `Item ${row + 1}`}</text>
                {Array.from({ length: 6 }).map((_, col) => (
                  <circle
                    key={col}
                    cx={145 + col * 22}
                    cy={8}
                    r={6}
                    fill={col < active ? accent : '#D7DFEA'}
                  />
                ))}
              </g>
            );
          })}
        </svg>
      );
    }

    function SvgFlow({ steps, accent }: { steps: string[]; accent: string }) {
      return (
        <svg viewBox="0 0 320 120" className="h-[120px] w-full">
          <defs>
            <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="#94A3B8" />
            </marker>
          </defs>
          {steps.slice(0, 3).map((step, index) => {
            const x = 10 + index * 102;
            return (
              <g key={index}>
                <rect x={x} y="34" width="90" height="44" rx="14" fill={index === 1 ? accent : '#E8EEF8'} />
                <text x={x + 45} y="60" textAnchor="middle" fontSize="11" fill={index === 1 ? '#fff' : '#0F172A'}>
                  {(step || '').slice(0, 8)}
                </text>
                {index < 2 ? <path d={`M ${x + 92} 56 L ${x + 108} 56`} stroke="#94A3B8" strokeWidth="2.5" markerEnd="url(#arrow)" /> : null}
              </g>
            );
          })}
        </svg>
      );
    }

    function SvgBars({ items, accent }: { items: Array<{ label?: string; value?: string | number }>; accent: string }) {
      return (
        <svg viewBox="0 0 320 120" className="h-[120px] w-full">
          {items.slice(0, 4).map((item, index) => {
            const raw = typeof item.value === 'number' ? item.value : Number(item.value || 0);
            const width = Number.isFinite(raw) ? Math.max(28, Math.min(200, raw * 2)) : 96;
            const y = 10 + index * 26;
            return (
              <g key={index}>
                <text x="0" y={y + 12} fontSize="11" fill="#64748B">{item.label || `Signal ${index + 1}`}</text>
                <rect x="102" y={y} width="180" height="12" rx="6" fill="#E5EDF6" />
                <rect x="102" y={y} width={width} height="12" rx="6" fill={accent} />
              </g>
            );
          })}
        </svg>
      );
    }

    function SvgComparison({ items, accent }: { items: Array<{ label?: string; value?: string | number }>; accent: string }) {
      return (
        <svg viewBox="0 0 320 120" className="h-[120px] w-full">
          {items.slice(0, 4).map((item, index) => {
            const x = 18 + index * 72;
            const h = 28 + (4 - index) * 12;
            return (
              <g key={index}>
                <rect x={x} y={96 - h} width="36" height={h} rx="10" fill={index % 2 === 0 ? accent : '#9DB8FF'} />
                <text x={x + 18} y="110" textAnchor="middle" fontSize="10" fill="#64748B">{(item.label || '').slice(0, 4)}</text>
              </g>
            );
          })}
        </svg>
      );
    }

    function SvgProbabilities({ items, accent }: { items: Array<{ label?: string; value?: string | number }>; accent: string }) {
      return (
        <svg viewBox="0 0 320 120" className="h-[120px] w-full">
          {items.slice(0, 3).map((item, index) => {
            const raw = typeof item.value === 'number' ? item.value : Number(item.value || 0);
            const width = Number.isFinite(raw) ? Math.max(40, Math.min(240, raw * 2.2)) : 120;
            const y = 14 + index * 32;
            return (
              <g key={index}>
                <text x="0" y={y + 12} fontSize="11" fill="#64748B">{item.label || `Case ${index + 1}`}</text>
                <rect x="98" y={y} width="190" height="14" rx="7" fill="#EEF2F7" />
                <rect x="98" y={y} width={width} height="14" rx="7" fill={accent} />
              </g>
            );
          })}
        </svg>
      );
    }

    function SvgVisual({ card, accent }: { card: any; accent: string }) {
      const data = card.visualData || {};
      if (card.visualType === 'mini-flow') return <SvgFlow steps={data.steps || []} accent={accent} />;
      if (card.visualType === 'signal-bar') return <SvgBars items={data.signals || data.items || []} accent={accent} />;
      if (card.visualType === 'comparison-strip') return <SvgComparison items={data.items || []} accent={accent} />;
      if (card.visualType === 'probability-strip') return <SvgProbabilities items={data.items || []} accent={accent} />;
      return <SvgDots items={data.nodes || data.items || []} accent={accent} />;
    }

    function renderCard(card: any, index: number) {
      const accent = accentFor(index);
      const normalizedItems = normalizeItems(card.items);
      const spanClass = cardSpan(card.type, card.emphasis);

      if (card.type === 'hero-summary-card') {
        return (
          <article key={index} className={`${spanClass} overflow-hidden rounded-[34px] bg-slate-950 px-10 py-10 text-white shadow-[0_18px_44px_rgba(15,23,42,0.16)]`}>
            <div className="text-[12px] font-bold tracking-[0.24em] text-slate-400">{card.eyebrow || 'hero-summary-card'}</div>
            <h2 className="mt-5 max-w-[960px] text-[44px] font-black leading-[1.15] tracking-[-0.04em]">{card.headline}</h2>
            {card.highlights?.length ? (
              <div className="mt-8 grid grid-cols-3 gap-4">
                {card.highlights.map((item: string, itemIndex: number) => (
                  <div key={itemIndex} className="rounded-[22px] bg-white/8 px-5 py-5 text-[17px] font-semibold leading-8 text-white/92">
                    {item}
                  </div>
                ))}
              </div>
            ) : null}
            <div className="mt-8 rounded-[24px] bg-white/8 px-5 py-5">
              <SvgVisual card={card} accent="#F8C84D" />
            </div>
          </article>
        );
      }

      if (card.type === 'section-header-card') {
        return (
          <article key={index} className={`${spanClass} flex items-end justify-between gap-8 border-t border-slate-900 pt-8`}>
            <div>
              <div className="text-[12px] font-bold tracking-[0.24em] text-slate-400">SECTION</div>
              <h3 className="mt-3 text-[34px] font-black leading-[1.2] tracking-[-0.03em] text-slate-950">{card.title}</h3>
            </div>
            {card.summary ? <div className="max-w-[760px] text-[18px] leading-8 text-slate-500">{card.summary}</div> : null}
          </article>
        );
      }

      if (card.type === 'signal-card') {
        return (
          <article key={index} className={`${spanClass} rounded-[28px] bg-white px-7 py-7 shadow-[0_10px_32px_rgba(15,23,42,0.06)]`}>
            <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">{card.title || '关键线索'}</div>
            {card.claim ? <div className="mt-3 text-[24px] font-black leading-[1.35] tracking-[-0.025em] text-slate-950">{card.claim}</div> : null}
            <div className="mt-5 space-y-3">
              {normalizedItems.map((item, itemIndex) => (
                <div key={itemIndex} className="flex items-start gap-3 rounded-[18px] bg-slate-50 px-4 py-4">
                  <div className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: accent }} />
                  <div className="text-[16px] leading-7 text-slate-700">{item.label}</div>
                </div>
              ))}
            </div>
            <div className="mt-6 rounded-[22px] bg-slate-50 px-4 py-4">
              <SvgVisual card={card} accent={accent} />
            </div>
          </article>
        );
      }

      if (card.type === 'comparison-card') {
        return (
          <article key={index} className={`${spanClass} rounded-[30px] bg-white px-8 py-8 shadow-[0_12px_36px_rgba(15,23,42,0.06)]`}>
            <div>
              <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">COMPARISON</div>
              <h3 className="mt-3 text-[30px] font-black tracking-[-0.03em] text-slate-950">{card.title}</h3>
              {card.claim ? <div className="mt-3 text-[18px] leading-8 text-slate-600">{card.claim}</div> : null}
            </div>
            <div className="mt-6 grid grid-cols-2 gap-4">
              {normalizedItems.map((item, itemIndex) => (
                <div key={itemIndex} className="rounded-[22px] border border-slate-200 bg-slate-50 px-5 py-5">
                  <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">{item.label}</div>
                  <div className="mt-3 text-[18px] font-semibold leading-8 text-slate-800">{item.value}</div>
                </div>
              ))}
            </div>
            <div className="mt-6 rounded-[22px] bg-slate-50 px-5 py-5">
              <SvgVisual card={card} accent={accent} />
            </div>
          </article>
        );
      }

      if (card.type === 'mini-bar-card' || card.type === 'probability-card') {
        const eyebrow = card.type === 'mini-bar-card' ? 'SCORES' : 'SCENARIOS';
        return (
          <article key={index} className={`${spanClass} rounded-[28px] bg-white px-7 py-7 shadow-[0_10px_32px_rgba(15,23,42,0.06)]`}>
            <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">{eyebrow}</div>
            <h3 className="mt-3 text-[28px] font-black tracking-[-0.03em] text-slate-950">{card.title}</h3>
            {card.claim ? <div className="mt-3 text-[17px] leading-8 text-slate-600">{card.claim}</div> : null}
            <div className="mt-6 rounded-[22px] bg-slate-50 px-4 py-4">
              <SvgVisual card={card} accent={accent} />
            </div>
          </article>
        );
      }

      return (
        <article key={index} className={`${spanClass} rounded-[28px] bg-white px-7 py-7 shadow-[0_10px_32px_rgba(15,23,42,0.06)]`}>
          <div className="mb-5 flex items-center gap-3">
            <div className="h-3 w-3 rounded-full" style={{ background: accent }} />
            <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">{card.sectionTitle || card.type}</div>
          </div>
          <h3 className="text-[28px] font-black leading-[1.25] tracking-[-0.03em] text-slate-950">{card.title}</h3>
          {card.claim ? <div className="mt-3 text-[20px] font-semibold leading-[1.6] text-slate-800">{card.claim}</div> : null}
          {card.bullets?.length ? (
            <div className="mt-5 space-y-3">
              {card.bullets.map((item: string, itemIndex: number) => (
                <div key={itemIndex} className="rounded-[18px] bg-slate-50 px-4 py-4 text-[16px] leading-7 text-slate-700">
                  {item}
                </div>
              ))}
            </div>
          ) : null}
          <div className="mt-6 rounded-[22px] bg-slate-50 px-4 py-4">
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
          backgroundColor: '#F2F4F7',
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
      const totalCards = cards.length;
      const { lead, rest } = useMemo(() => splitHighlights(FREE_REPORT_BRIEF.summary || []), []);

      return (
        <div className="min-h-screen bg-[#E6EBF1] px-8 py-10 text-slate-900">
          <div ref={captureRef} className="mx-auto w-[1480px] overflow-hidden rounded-[28px] bg-[#F2F4F7] shadow-[0_35px_100px_rgba(15,23,42,0.14)]">
            <section className="bg-[#F8FAFC] px-16 pt-14">
              <div className="grid grid-cols-[1.25fr_0.75fr] gap-10 border-b border-slate-200 pb-12">
                <div>
                  <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">FREE REPORT / SVG INFOGRAPHIC</div>
                  <h1 className="mt-5 max-w-[980px] text-[78px] font-black leading-[0.98] tracking-[-0.055em] text-slate-950">
                    {FREE_REPORT_BRIEF.title}
                  </h1>
                  <p className="mt-6 max-w-[880px] text-[24px] leading-[1.75] text-slate-600">
                    {FREE_REPORT_BRIEF.userIntent || '根据内容结构自动重组成观点提炼 + 示意图表的卡片式长图，优先保证扫读效率和视觉完成度。'}
                  </p>
                </div>

                <div className="flex flex-col justify-between rounded-[28px] bg-slate-950 px-8 py-8 text-white">
                  <div>
                    <div className="text-[12px] tracking-[0.22em] text-slate-400">内容速览</div>
                    <div className="mt-6 grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-[34px] font-black leading-none">{FREE_REPORT_BRIEF.layoutFamily || 'adaptive'}</div>
                        <div className="mt-2 text-sm text-slate-400">版式族</div>
                      </div>
                      <div>
                        <div className="text-[38px] font-black leading-none">{totalCards}</div>
                        <div className="mt-2 text-sm text-slate-400">观点卡片</div>
                      </div>
                    </div>
                  </div>
                  <div className="mt-8 border-t border-white/10 pt-6 text-[17px] leading-8 text-slate-300">
                    先看主判断，再扫要点卡和示意图表，最后回到分区细节。
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-[1.18fr_0.82fr] gap-8 py-10">
                <div className="rounded-[30px] bg-slate-950 px-10 py-10 text-white">
                  <div className="text-[12px] font-bold tracking-[0.24em] text-slate-400">首要判断</div>
                  <div className="mt-5 text-[42px] font-black leading-[1.28] tracking-[-0.03em] text-white">
                    {lead || '等待补充核心判断'}
                  </div>
                </div>

                <div className="grid gap-4">
                  {rest.map((item, index) => (
                    <div key={index} className="rounded-[24px] border border-slate-200 bg-white px-6 py-6">
                      <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">核心线索 {index + 1}</div>
                      <div className="mt-3 text-[22px] font-semibold leading-[1.7] text-slate-800">{item}</div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {FREE_REPORT_BRIEF.referenceImages?.length ? (
              <section className="border-t border-slate-200 bg-[#F6FAFF] px-16 py-5 text-[16px] leading-8 text-[#26408B]">
                本版面仅参考参考图的视觉节奏与结构方式，所有内容卡片与SVG示意图均为根据当前内容重新生成。
              </section>
            ) : null}

            <main className="px-16 py-12">
              <div className="grid grid-cols-12 gap-5">
                {FREE_REPORT_BRIEF.cards.map((card, index) => renderCard(card, index))}
              </div>
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
    (src_dir / "constants.ts").write_text(
        CONSTANTS_TEMPLATE.format(payload=payload),
        encoding="utf-8",
    )
    (src_dir / "types.ts").write_text(TS_TYPES, encoding="utf-8")
    (src_dir / "App.tsx").write_text(APP_TEMPLATE, encoding="utf-8")
