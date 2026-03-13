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

    export default function App() {
      const captureRef = useRef<HTMLDivElement>(null);

      const exportCapture = async () => {
        if (captureRef.current === null) return null;
        return toPng(captureRef.current, {
          cacheBust: true,
          backgroundColor: '#ECF2F8',
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

      return (
        <div className="min-h-screen bg-[#DDE6F2] px-8 py-10 text-slate-900">
          <div ref={captureRef} className="mx-auto w-[1440px] overflow-hidden rounded-[36px] bg-[#ECF2F8] shadow-[0_24px_80px_rgba(15,23,42,0.18)]">
            <section className="relative overflow-hidden bg-[#152238] px-14 pb-14 pt-16 text-white">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(86,132,255,0.28),transparent_34%),radial-gradient(circle_at_20%_20%,rgba(255,255,255,0.14),transparent_28%)]" />
              <div className="relative">
                <div className="flex items-start justify-between gap-8">
                  <div className="max-w-[920px]">
                    <div className="inline-flex items-center rounded-full border border-white/15 bg-white/8 px-4 py-2 text-[13px] font-semibold tracking-[0.28em] text-slate-200 uppercase">
                      研报长图 · 自由版式
                    </div>
                    <h1 className="mt-7 max-w-[980px] text-[64px] font-black leading-[1.04] tracking-[-0.04em]">
                      {FREE_REPORT_BRIEF.title}
                    </h1>
                    <p className="mt-5 max-w-[900px] text-[24px] leading-[1.6] text-slate-200/90">
                      {FREE_REPORT_BRIEF.userIntent || '按原文结构与重点信息进行动态重排，默认不过度压缩内容。'}
                    </p>
                  </div>
                  <div className="w-[250px] shrink-0 rounded-[28px] border border-white/12 bg-white/8 px-6 py-6 backdrop-blur-sm">
                    <div className="text-[12px] tracking-[0.22em] text-slate-300">内容概览</div>
                    <div className="mt-5 grid gap-5">
                      <div>
                        <div className="text-[34px] font-black leading-none">{FREE_REPORT_BRIEF.sections.length}</div>
                        <div className="mt-2 text-sm text-slate-300">主章节</div>
                      </div>
                      <div>
                        <div className="text-[34px] font-black leading-none">{totalBlocks}</div>
                        <div className="mt-2 text-sm text-slate-300">重点观点</div>
                      </div>
                    </div>
                  </div>
                </div>

                {FREE_REPORT_BRIEF.summary?.length ? (
                  <div className="mt-10 grid grid-cols-2 gap-5">
                    {FREE_REPORT_BRIEF.summary.slice(0, 4).map((item, index) => (
                      <div key={index} className="rounded-[24px] border border-white/10 bg-white/10 px-6 py-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
                        <div className="text-[12px] font-semibold tracking-[0.24em] text-slate-300">核心判断 {index + 1}</div>
                        <div className="mt-4 text-[22px] font-semibold leading-[1.7] text-white/95">{item}</div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </section>

            {FREE_REPORT_BRIEF.referenceImages?.length ? (
              <section className="border-b border-slate-200 bg-[#F5F9FF] px-14 py-6 text-[16px] leading-8 text-[#26408B]">
                本版面参考了用户提供样式图中的信息层级、视觉节奏与结构方式，但最终输出为基于当前内容重新组织的原创长图。
              </section>
            ) : null}

            <main className="px-14 py-12">
              <div className="space-y-8">
                {FREE_REPORT_BRIEF.sections.map((section, sectionIndex) => {
                  const accent = ACCENTS[sectionIndex % ACCENTS.length];
                  const isSingleColumn = section.blocks.length <= 1;
                  return (
                    <section key={sectionIndex} className="overflow-hidden rounded-[30px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.07)]">
                      <div className="flex items-stretch">
                        <div className="w-[12px] shrink-0" style={{ background: accent }} />
                        <div className="flex-1 px-10 pb-10 pt-9">
                          <div className="flex items-start justify-between gap-8">
                            <div className="max-w-[880px]">
                              <div className="text-[12px] font-bold tracking-[0.24em] text-slate-400">第 {sectionIndex + 1} 章节</div>
                              <h2 className="mt-3 text-[38px] font-black tracking-[-0.03em] text-slate-950">{section.title}</h2>
                              {section.lead ? <p className="mt-4 text-[20px] leading-9 text-slate-500">{section.lead}</p> : null}
                            </div>
                            <div className="rounded-[20px] border border-slate-200 bg-slate-50 px-5 py-4 text-right">
                              <div className="text-[12px] font-semibold tracking-[0.22em] text-slate-400">要点数</div>
                              <div className="mt-2 text-[34px] font-black leading-none text-slate-900">{section.blocks.length}</div>
                            </div>
                          </div>

                          <div className={`mt-8 grid gap-5 ${isSingleColumn ? 'grid-cols-1' : 'grid-cols-2'}`}>
                            {section.blocks.map((block, blockIndex) => {
                              const highlight = ACCENTS[(sectionIndex + blockIndex) % ACCENTS.length];
                              return (
                                <article key={blockIndex} className="group relative overflow-hidden rounded-[24px] border border-slate-200 bg-[#F8FBFF] px-7 py-6 shadow-[0_10px_24px_rgba(37,99,235,0.05)]">
                                  <div className="absolute inset-x-0 top-0 h-[4px]" style={{ background: highlight }} />
                                  <div className="flex items-start justify-between gap-4">
                                    <div className="max-w-[80%]">
                                      <div className="text-[12px] font-bold tracking-[0.22em] text-slate-400">重点 {blockIndex + 1}</div>
                                      <h3 className="mt-3 text-[28px] font-black leading-[1.3] tracking-[-0.02em] text-slate-950">{block.title}</h3>
                                    </div>
                                    <div className="mt-1 h-3 w-3 shrink-0 rounded-full" style={{ background: highlight }} />
                                  </div>
                                  {block.summary ? <p className="mt-5 text-[19px] leading-9 text-slate-700">{block.summary}</p> : null}
                                  {block.bullets?.length ? (
                                    <div className="mt-5 space-y-3">
                                      {block.bullets.slice(0, 6).map((item, bulletIndex) => (
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
