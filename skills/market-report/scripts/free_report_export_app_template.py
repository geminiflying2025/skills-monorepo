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
      };
      cards: Array<{
        type: string;
        title?: string;
        sectionTitle?: string;
        summary?: string;
        bullets?: string[];
        items?: Array<{ label?: string; value?: string | number } | string>;
        emphasis?: string;
        headline?: string;
        highlights?: string[];
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

    const ACCENTS = ['#1D4ED8', '#0F766E', '#7C3AED', '#EA580C', '#DB2777'];

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
        return {
          label: item.label || '',
          value: item.value ?? '',
        };
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
      if (type === 'risk-card') return 'col-span-4';
      if (emphasis === 'hero') return 'col-span-8';
      return 'col-span-4';
    }

    function MetricBars({ items, accent }: { items: Array<{ label: string; value: string | number }>; accent: string }) {
      return (
        <div className="space-y-4">
          {items.map((item, index) => {
            const raw = typeof item.value === 'number' ? item.value : Number(item.value || 0);
            const width = Number.isFinite(raw) ? Math.max(12, Math.min(100, raw)) : 48;
            return (
              <div key={index}>
                <div className="mb-2 flex items-center justify-between text-[13px] font-semibold text-slate-500">
                  <span>{item.label}</span>
                  <span className="text-slate-900">{item.value || '--'}</span>
                </div>
                <div className="h-2.5 rounded-full bg-slate-100">
                  <div className="h-2.5 rounded-full" style={{ width: `${width}%`, background: accent }} />
                </div>
              </div>
            );
          })}
        </div>
      );
    }

    function ProbabilityRows({ items, accent }: { items: Array<{ label: string; value: string | number }>; accent: string }) {
      return (
        <div className="space-y-3">
          {items.map((item, index) => {
            const raw = typeof item.value === 'number' ? item.value : Number(item.value || 0);
            const width = Number.isFinite(raw) ? Math.max(14, Math.min(100, raw)) : 33;
            return (
              <div key={index} className="rounded-[18px] bg-slate-50 px-4 py-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="text-[15px] font-semibold text-slate-800">{item.label}</div>
                  <div className="text-[14px] font-black text-slate-500">{item.value || '--'}</div>
                </div>
                <div className="mt-3 h-2.5 rounded-full bg-white">
                  <div className="h-2.5 rounded-full" style={{ width: `${width}%`, background: accent }} />
                </div>
              </div>
            );
          })}
        </div>
      );
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
            <div className="mt-5 space-y-3">
              {normalizedItems.map((item, itemIndex) => (
                <div key={itemIndex} className="flex items-start gap-3 rounded-[18px] bg-slate-50 px-4 py-4">
                  <div className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: accent }} />
                  <div className="text-[16px] leading-7 text-slate-700">{item.label}</div>
                </div>
              ))}
            </div>
          </article>
        );
      }

      if (card.type === 'comparison-card') {
        return (
          <article key={index} className={`${spanClass} rounded-[30px] bg-white px-8 py-8 shadow-[0_12px_36px_rgba(15,23,42,0.06)]`}>
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">COMPARISON</div>
                <h3 className="mt-3 text-[30px] font-black tracking-[-0.03em] text-slate-950">{card.title}</h3>
              </div>
            </div>
            <div className="mt-6 grid grid-cols-2 gap-4">
              {normalizedItems.map((item, itemIndex) => (
                <div key={itemIndex} className="rounded-[22px] border border-slate-200 bg-slate-50 px-5 py-5">
                  <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">{item.label}</div>
                  <div className="mt-3 text-[18px] font-semibold leading-8 text-slate-800">{item.value}</div>
                </div>
              ))}
            </div>
          </article>
        );
      }

      if (card.type === 'mini-bar-card') {
        return (
          <article key={index} className={`${spanClass} rounded-[28px] bg-white px-7 py-7 shadow-[0_10px_32px_rgba(15,23,42,0.06)]`}>
            <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">SCORES</div>
            <h3 className="mt-3 text-[28px] font-black tracking-[-0.03em] text-slate-950">{card.title}</h3>
            <div className="mt-6">
              <MetricBars items={normalizedItems} accent={accent} />
            </div>
          </article>
        );
      }

      if (card.type === 'probability-card') {
        return (
          <article key={index} className={`${spanClass} rounded-[28px] bg-white px-7 py-7 shadow-[0_10px_32px_rgba(15,23,42,0.06)]`}>
            <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">SCENARIOS</div>
            <h3 className="mt-3 text-[28px] font-black tracking-[-0.03em] text-slate-950">{card.title}</h3>
            <div className="mt-6">
              <ProbabilityRows items={normalizedItems} accent={accent} />
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
          {card.summary ? <p className="mt-4 text-[18px] leading-8 text-slate-600">{card.summary}</p> : null}
          {card.bullets?.length ? (
            <div className="mt-5 space-y-3">
              {card.bullets.map((item: string, itemIndex: number) => (
                <div key={itemIndex} className="rounded-[18px] bg-slate-50 px-4 py-4 text-[16px] leading-7 text-slate-700">
                  {item}
                </div>
              ))}
            </div>
          ) : null}
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
      const totalBlocks = useMemo(() => cards.length, [cards]);
      const { lead, rest } = useMemo(() => splitHighlights(FREE_REPORT_BRIEF.summary || []), []);

      return (
        <div className="min-h-screen bg-[#E6EBF1] px-8 py-10 text-slate-900">
          <div ref={captureRef} className="mx-auto w-[1480px] overflow-hidden rounded-[28px] bg-[#F2F4F7] shadow-[0_35px_100px_rgba(15,23,42,0.14)]">
            <section className="bg-[#F8FAFC] px-16 pt-14">
              <div className="grid grid-cols-[1.25fr_0.75fr] gap-10 border-b border-slate-200 pb-12">
                <div>
                  <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">自由研报 / 编辑版式</div>
                  <h1 className="mt-5 max-w-[980px] text-[78px] font-black leading-[0.98] tracking-[-0.055em] text-slate-950">
                    {FREE_REPORT_BRIEF.title}
                  </h1>
                  <p className="mt-6 max-w-[880px] text-[24px] leading-[1.75] text-slate-600">
                    {FREE_REPORT_BRIEF.userIntent || '根据内容结构自动重组成媒体化卡片长图，优先突出结论、对比关系与可转发的视觉节奏。'}
                  </p>
                </div>

                <div className="flex flex-col justify-between rounded-[28px] bg-slate-950 px-8 py-8 text-white">
                  <div>
                    <div className="text-[12px] tracking-[0.22em] text-slate-400">内容速览</div>
                    <div className="mt-6 grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-[38px] font-black leading-none">{FREE_REPORT_BRIEF.layoutFamily || 'adaptive'}</div>
                        <div className="mt-2 text-sm text-slate-400">版式族</div>
                      </div>
                      <div>
                        <div className="text-[38px] font-black leading-none">{totalBlocks}</div>
                        <div className="mt-2 text-sm text-slate-400">信息卡片</div>
                      </div>
                    </div>
                  </div>
                  <div className="mt-8 border-t border-white/10 pt-6 text-[17px] leading-8 text-slate-300">
                    阅读顺序：先抓主判断，再扫卡片组块，最后回看重点分区与风险提示。
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
                本版面参考了用户提供样式图中的信息层级、视觉节奏与结构方式，但最终输出为基于当前内容重新组织的原创长图。
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
