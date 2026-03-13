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
    import React, { useRef } from 'react';
    import { toPng } from 'html-to-image';
    import { FREE_REPORT_BRIEF } from './constants';

    export default function App() {
      const captureRef = useRef<HTMLDivElement>(null);

      const exportCapture = async () => {
        if (captureRef.current === null) return null;
        return toPng(captureRef.current, {
          cacheBust: true,
          backgroundColor: '#EEF3F8',
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

      return (
        <div className="min-h-screen bg-slate-200 flex justify-center overflow-x-hidden">
          <div ref={captureRef} className="bg-[#EEF3F8] w-full max-w-[1440px] min-h-screen px-10 py-12">
            <section className="rounded-[28px] bg-gradient-to-br from-slate-900 to-blue-900 text-white px-10 py-10 shadow-2xl shadow-slate-400/30">
              <div className="text-sm uppercase tracking-[0.35em] text-slate-300">AI Report Layout</div>
              <h1 className="mt-4 text-5xl font-black tracking-tight leading-tight">{FREE_REPORT_BRIEF.title}</h1>
              <p className="mt-4 text-xl leading-8 text-slate-100/90">{FREE_REPORT_BRIEF.userIntent || '报告风长图 · 自由设计模式'}</p>
              {FREE_REPORT_BRIEF.summary?.length ? (
                <div className="mt-8 grid grid-cols-3 gap-4">
                  {FREE_REPORT_BRIEF.summary.slice(0, 3).map((item, index) => (
                    <div key={index} className="rounded-2xl border border-white/15 bg-white/10 px-5 py-4 text-lg leading-8 text-slate-50">
                      {item}
                    </div>
                  ))}
                </div>
              ) : null}
            </section>

            {FREE_REPORT_BRIEF.referenceImages?.length ? (
              <section className="mt-6 rounded-2xl border border-blue-200 bg-blue-50 px-6 py-5 text-base leading-7 text-blue-900">
                本版面参考了用户提供样式图的层级、密度与版式节奏，但输出为基于当前内容重新生成的原创长图，不直接复制原图内容或品牌元素。
              </section>
            ) : null}

            <main className="mt-7 space-y-6">
              {FREE_REPORT_BRIEF.sections.map((section, index) => (
                <section key={index} className="rounded-[24px] border border-slate-200 bg-white px-7 py-7 shadow-lg shadow-slate-200/50">
                  <h2 className="text-3xl font-extrabold tracking-tight text-slate-900">{section.title}</h2>
                  {section.lead ? <p className="mt-3 text-lg leading-8 text-slate-500">{section.lead}</p> : null}
                  <div className="mt-6 grid grid-cols-2 gap-5">
                    {section.blocks.map((block, blockIndex) => (
                      <article key={blockIndex} className="rounded-[20px] border border-slate-200 bg-slate-50 px-6 py-5">
                        <h3 className="text-2xl font-bold leading-9 text-slate-900">{block.title}</h3>
                        {block.summary ? <p className="mt-3 text-lg leading-8 text-slate-700">{block.summary}</p> : null}
                        {block.bullets?.length ? (
                          <ul className="mt-3 list-disc space-y-2 pl-5 text-base leading-7 text-slate-500">
                            {block.bullets.slice(0, 6).map((item, bulletIndex) => <li key={bulletIndex}>{item}</li>)}
                          </ul>
                        ) : null}
                      </article>
                    ))}
                  </div>
                </section>
              ))}
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
