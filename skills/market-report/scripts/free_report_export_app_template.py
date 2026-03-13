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

    const ACCENTS = ['#2458FF', '#1E3A8A', '#0F766E', '#9A3412'];

    type SectionLayout = 'focus' | 'dual' | 'compact';

    function layoutForSection(blockCount: number, index: number): SectionLayout {
      if (index === 0 || blockCount >= 3) return 'focus';
      if (blockCount === 2) return 'dual';
      return 'compact';
    }

    export default function App() {
      const captureRef = useRef<HTMLDivElement>(null);

      const exportCapture = async () => {
        if (captureRef.current === null) return null;
        return toPng(captureRef.current, {
          cacheBust: true,
          backgroundColor: '#EDF3F8',
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

      const totalBlocks = useMemo(() => FREE_REPORT_BRIEF.sections.reduce((sum, section) => sum + section.blocks.length, 0), []);
      const overview = useMemo(() => FREE_REPORT_BRIEF.summary.slice(0, 4), []);

      return (
        <div className="min-h-screen bg-[#DCE6F0] px-8 py-10 text-slate-900">
          <div ref={captureRef} className="mx-auto w-[1440px] overflow-hidden rounded-[40px] bg-[#EDF3F8] shadow-[0_30px_90px_rgba(15,23,42,0.16)]">
            <section className="relative overflow-hidden bg-[#0F172A] px-14 pb-14 pt-14 text-white">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.30),transparent_34%),radial-gradient(circle_at_20%_16%,rgba(255,255,255,0.12),transparent_25%)]" />
              <div className="relative grid grid-cols-[1.55fr_0.9fr] gap-8">
                <div>
                  <div className="inline-flex items-center rounded-full border border-white/15 bg-white/8 px-4 py-2 text-[13px] font-semibold tracking-[0.18em] text-slate-200">
                    报告风长图 · 动态编排
                  </div>
                  <h1 className="mt-7 max-w-[940px] text-[68px] font-black leading-[1.02] tracking-[-0.05em]">
                    {FREE_REPORT_BRIEF.title}
                  </h1>
                  <p className="mt-5 max-w-[920px] text-[22px] leading-[1.75] text-slate-200/90">
                    {FREE_REPORT_BRIEF.userIntent || '按原文结构和重点信息进行重组，默认保持中性保真，不过度压缩。'}
                  </p>

                  {overview.length ? (
                    <div className="mt-10 grid grid-cols-2 gap-5">
                      {overview.map((item, index) => (
                        <div key={index} className="rounded-[24px] border border-white/10 bg-white/8 px-6 py-6 backdrop-blur-sm">
                          <div className="text-[12px] font-semibold tracking-[0.2em] text-slate-300">核心判断 {index + 1}</div>
                          <div className="mt-4 text-[22px] font-semibold leading-[1.7] text-white/95">{item}</div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>

                <div className="space-y-5">
                  <div className="rounded-[28px] border border-white/12 bg-white/8 px-7 py-7 backdrop-blur-sm">
                    <div className="text-[12px] tracking-[0.22em] text-slate-300">内容概览</div>
                    <div className="mt-5 grid grid-cols-2 gap-4">
                      <div className="rounded-[20px] bg-black/10 px-4 py-5">
                        <div className="text-[34px] font-black leading-none">{FREE_REPORT_BRIEF.sections.length}</div>
                        <div className="mt-2 text-sm text-slate-300">主章节</div>
                      </div>
                      <div className="rounded-[20px] bg-black/10 px-4 py-5">
                        <div className="text-[34px] font-black leading-none">{totalBlocks}</div>
                        <div className="mt-2 text-sm text-slate-300">重点观点</div>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-[28px] border border-white/12 bg-[linear-gradient(135deg,rgba(36,88,255,0.18),rgba(15,118,110,0.10))] px-7 py-7">
                    <div className="text-[12px] tracking-[0.22em] text-slate-300">阅读方式</div>
                    <div className="mt-4 text-[20px] font-semibold leading-[1.8] text-white/95">
                      先看核心判断，再按章节阅读依据与展开，适合滚动浏览与转发分享。
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {FREE_REPORT_BRIEF.referenceImages?.length ? (
              <section className="border-b border-slate-200 bg-[#F4F9FF] px-14 py-6 text-[16px] leading-8 text-[#26408B]">
                本版面参考了用户提供样式图中的信息层级、视觉节奏与结构方式，但最终输出为基于当前内容重新组织的原创长图。
              </section>
            ) : null}

            <main className="px-14 py-12">
              <div className="space-y-8">
                {FREE_REPORT_BRIEF.sections.map((section, sectionIndex) => {
                  const accent = ACCENTS[sectionIndex % ACCENTS.length];
                  const layout = layoutForSection(section.blocks.length, sectionIndex);
                  const [first, ...rest] = section.blocks;
                  return (
                    <section key={sectionIndex} className="overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.06)]">
                      <div className="flex items-stretch">
                        <div className="w-[12px] shrink-0" style={{ background: accent }} />
                        <div className="flex-1 px-10 pb-10 pt-9">
                          <div className="flex items-start justify-between gap-8">
                            <div className="max-w-[920px]">
                              <div className="text-[12px] font-bold tracking-[0.24em] text-slate-400">第 {sectionIndex + 1} 章节</div>
                              <h2 className="mt-3 text-[38px] font-black tracking-[-0.03em] text-slate-950">{section.title}</h2>
                              {section.lead ? <p className="mt-4 text-[20px] leading-9 text-slate-500">{section.lead}</p> : null}
                            </div>
                            <div className="rounded-[20px] border border-slate-200 bg-slate-50 px-5 py-4 text-right">
                              <div className="text-[12px] font-semibold tracking-[0.22em] text-slate-400">要点数</div>
                              <div className="mt-2 text-[34px] font-black leading-none text-slate-900">{section.blocks.length}</div>
                            </div>
                          </div>

                          {layout === 'focus' && first ? (
                            <div className="mt-8 grid grid-cols-[1.18fr_0.82fr] gap-5">
                              <article className="relative overflow-hidden rounded-[28px] bg-[#F7FAFF] px-8 py-8 shadow-[0_14px_30px_rgba(37,99,235,0.06)] ring-1 ring-slate-200">
                                <div className="absolute inset-x-0 top-0 h-[5px]" style={{ background: accent }} />
                                <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">首要判断</div>
                                <h3 className="mt-4 text-[34px] font-black leading-[1.25] tracking-[-0.03em] text-slate-950">{first.title}</h3>
                                {first.summary ? <p className="mt-5 text-[20px] leading-9 text-slate-700">{first.summary}</p> : null}
                                {first.bullets?.length ? (
                                  <div className="mt-6 grid gap-3">
                                    {first.bullets.slice(0, 4).map((item, idx) => (
                                      <div key={idx} className="rounded-[18px] bg-white px-4 py-4 text-[16px] leading-7 text-slate-600 ring-1 ring-slate-100">
                                        {item}
                                      </div>
                                    ))}
                                  </div>
                                ) : null}
                              </article>

                              <div className="grid gap-4">
                                {rest.map((block, blockIndex) => {
                                  const highlight = ACCENTS[(sectionIndex + blockIndex + 1) % ACCENTS.length];
                                  return (
                                    <article key={blockIndex} className="relative overflow-hidden rounded-[24px] border border-slate-200 bg-white px-6 py-5 shadow-[0_10px_22px_rgba(15,23,42,0.04)]">
                                      <div className="absolute inset-x-0 top-0 h-[4px]" style={{ background: highlight }} />
                                      <div className="text-[12px] font-bold tracking-[0.2em] text-slate-400">补充判断 {blockIndex + 1}</div>
                                      <h4 className="mt-3 text-[24px] font-black leading-[1.4] text-slate-950">{block.title}</h4>
                                      {block.summary ? <p className="mt-4 text-[17px] leading-8 text-slate-600">{block.summary}</p> : null}
                                    </article>
                                  );
                                })}
                              </div>
                            </div>
                          ) : null}

                          {layout === 'dual' ? (
                            <div className="mt-8 grid grid-cols-2 gap-5">
                              {section.blocks.map((block, blockIndex) => {
                                const highlight = ACCENTS[(sectionIndex + blockIndex) % ACCENTS.length];
                                return (
                                  <article key={blockIndex} className="relative overflow-hidden rounded-[26px] border border-slate-200 bg-[#F8FBFF] px-7 py-6 shadow-[0_10px_24px_rgba(37,99,235,0.05)]">
                                    <div className="absolute inset-x-0 top-0 h-[4px]" style={{ background: highlight }} />
                                    <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">重点 {blockIndex + 1}</div>
                                    <h3 className="mt-3 text-[28px] font-black leading-[1.3] tracking-[-0.02em] text-slate-950">{block.title}</h3>
                                    {block.summary ? <p className="mt-5 text-[19px] leading-9 text-slate-700">{block.summary}</p> : null}
                                    {block.bullets?.length ? (
                                      <div className="mt-5 space-y-3">
                                        {block.bullets.slice(0, 4).map((item, bulletIndex) => (
                                          <div key={bulletIndex} className="flex items-start gap-3 rounded-2xl bg-white/90 px-4 py-3">
                                            <div className="mt-[10px] h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: highlight }} />
                                            <div className="text-[16px] leading-7 text-slate-500">{item}</div>
                                          </div>
                                        ))}
                                      </div>
                                    ) : null}
                                  </article>
                                );
                              })}
                            </div>
                          ) : null}

                          {layout === 'compact' ? (
                            <div className="mt-8 space-y-4">
                              {section.blocks.map((block, blockIndex) => {
                                const highlight = ACCENTS[(sectionIndex + blockIndex) % ACCENTS.length];
                                return (
                                  <article key={blockIndex} className="relative overflow-hidden rounded-[24px] border border-slate-200 bg-[#F8FBFF] px-7 py-6 shadow-[0_10px_24px_rgba(37,99,235,0.05)]">
                                    <div className="absolute inset-y-0 left-0 w-[6px]" style={{ background: highlight }} />
                                    <div className="pl-2">
                                      <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">重点 {blockIndex + 1}</div>
                                      <h3 className="mt-3 text-[26px] font-black leading-[1.35] tracking-[-0.02em] text-slate-950">{block.title}</h3>
                                      {block.summary ? <p className="mt-4 text-[18px] leading-8 text-slate-700">{block.summary}</p> : null}
                                      {block.bullets?.length ? (
                                        <div className="mt-4 grid gap-2">
                                          {block.bullets.slice(0, 4).map((item, bulletIndex) => (
                                            <div key={bulletIndex} className="text-[16px] leading-7 text-slate-500">• {item}</div>
                                          ))}
                                        </div>
                                      ) : null}
                                    </div>
                                  </article>
                                );
                              })}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </section>
                  );
                })}
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
