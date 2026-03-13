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
      cardComponent?: string;
      infoType?: string;
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

    function toneColor(tone?: string, accent?: string) {
      if (tone === 'gold') return '#C9A227';
      if (tone === 'warning') return '#F59E0B';
      if (tone === 'positive') return '#14B8A6';
      if (tone === 'ink') return '#0F204A';
      if (tone === 'muted') return '#CBD5E1';
      if (tone === 'primary') return accent || '#2F5BEA';
      return accent || '#2F5BEA';
    }

    function TagPill({ x, y, label, fill, textFill, width }: { x: number; y: number; label: string; fill: string; textFill: string; width?: number }) {
      const w = width || Math.max(52, label.length * 12 + 24);
      return (
        <g>
          <rect x={x} y={y} width={w} height="24" rx="12" fill={fill} />
          <text x={x + w / 2} y={y + 16} textAnchor="middle" fontSize="10" fill={textFill}>{label}</text>
        </g>
      );
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

    function SvgScoreGrid({ data, accent }: { data: any; accent: string }) {
      const rows = data.rows || [];
      return (
        <svg viewBox="0 0 420 170" className="h-[170px] w-full">
          <rect x="0" y="0" width="420" height="170" rx="22" fill="#F8FAFC" />
          <text x="18" y="24" fontSize="12" fill="#64748B">宏观温度计（示意）</text>
          <TagPill x={302} y={12} label={data.badge || '观点偏强'} fill="#DBEAFE" textFill="#1D4ED8" width={96} />
          {data.secondaryBadge ? <TagPill x={314} y={40} label={data.secondaryBadge} fill="#FEF3C7" textFill="#92400E" width={84} /> : null}
          {rows.slice(0, 5).map((row: any, index: number) => (
            <g key={index} transform={`translate(18, ${52 + index * 22})`}>
              <text x="0" y="10" fontSize="11" fill="#475569">{row.label}</text>
              {Array.from({ length: 5 }).map((_, dotIndex) => (
                <circle
                  key={dotIndex}
                  cx={178 + dotIndex * 24}
                  cy={6}
                  r="6.5"
                  fill={dotIndex < (row.level || 3) ? toneColor(row.tone, accent) : '#D6DEEA'}
                />
              ))}
            </g>
          ))}
        </svg>
      );
    }

    function SvgPhaseShift({ data, accent }: { data: any; accent: string }) {
      const stages = data.stages || [];
      const tags = data.tags || [];
      return (
        <svg viewBox="0 0 420 168" className="h-[168px] w-full">
          <rect x="0" y="0" width="420" height="168" rx="22" fill="#F8FAFC" />
          <text x="18" y="24" fontSize="12" fill="#64748B">市场主线切换</text>
          <defs>
            <marker id="editorial-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="#94A3B8" />
            </marker>
          </defs>
          {stages.slice(0, 3).map((label: string, index: number) => {
            const x = 18 + index * 132;
            const fill = index === 1 ? '#BFD4FF' : index === 2 ? '#0F204A' : '#E2E8F0';
            const textFill = index === 2 ? '#FFFFFF' : '#0F172A';
            return (
              <g key={index}>
                <rect x={x} y="44" width="112" height="50" rx="18" fill={fill} />
                <text x={x + 56} y="73" textAnchor="middle" fontSize="12" fill={textFill}>{label}</text>
                {index < 2 ? <line x1={x + 116} y1="69" x2={x + 130} y2="69" stroke="#94A3B8" strokeWidth="2.5" markerEnd="url(#editorial-arrow)" /> : null}
              </g>
            );
          })}
          {tags.slice(0, 4).map((tag: string, index: number) => (
            <TagPill
              key={index}
              x={18 + (index % 2) * 130}
              y={116 + Math.floor(index / 2) * 28}
              label={tag}
              fill={index === 0 ? '#DBEAFE' : index === 1 ? '#E2E8F0' : index === 2 ? '#FEF3C7' : '#ECFDF5'}
              textFill={index === 0 ? '#1D4ED8' : index === 1 ? '#334155' : index === 2 ? '#92400E' : '#047857'}
              width={102}
            />
          ))}
        </svg>
      );
    }

    function SvgRangePosition({ data, accent }: { data: any; accent: string }) {
      const start = data.start || 26;
      const end = data.end || 76;
      const position = 44 + ((start + end) / 2) * 2.2;
      return (
        <svg viewBox="0 0 420 150" className="h-[150px] w-full">
          <rect x="0" y="0" width="420" height="150" rx="22" fill="#F8FAFC" />
          <text x="18" y="24" fontSize="12" fill="#64748B">{data.label || '区间运行示意'}</text>
          <line x1="44" y1="86" x2="374" y2="86" stroke="#CBD5E1" strokeWidth="2" strokeDasharray="7 7" />
          <rect x={44 + start * 2.2} y="68" width={Math.max(88, (end - start) * 2.2)} height="36" rx="18" fill="#CFE0FF" />
          <circle cx={position} cy="86" r="12" fill={accent} />
          <text x={position} y="90" textAnchor="middle" fontSize="10" fill="#FFFFFF">震荡</text>
          <path d="M 44 58 C 110 36, 184 74, 260 52 S 338 48, 374 54" stroke={accent} strokeWidth="3" fill="none" />
          <text x="44" y="52" fontSize="10" fill="#64748B">{data.startLabel || '低位支撑'}</text>
          <text x="374" y="52" textAnchor="end" fontSize="10" fill="#64748B">{data.endLabel || '上行受限'}</text>
          <text x="210" y="132" textAnchor="middle" fontSize="10" fill="#64748B">{data.footnote || '票息 + 区间交易'}</text>
        </svg>
      );
    }

    function SvgThemePillars({ data, accent }: { data: any; accent: string }) {
      const items = data.items || [];
      const tags = data.tags || [];
      return (
        <svg viewBox="0 0 420 162" className="h-[162px] w-full">
          <rect x="0" y="0" width="420" height="162" rx="22" fill="#F8FAFC" />
          <text x="18" y="24" fontSize="12" fill="#64748B">驱动拆解</text>
          {items.slice(0, 3).map((item: any, index: number) => {
            const x = 44 + index * 118;
            return (
              <g key={index}>
                <rect x={x} y={52 + (index === 1 ? 10 : 0)} width="26" height={50 + index * 12} rx="10" fill={toneColor(item.tone, accent)} />
                <rect x={x - 6} y="42" width="38" height="82" rx="14" fill="none" stroke="#D7DFEA" strokeDasharray="6 6" />
                <text x={x + 13} y="138" textAnchor="middle" fontSize="11" fill="#475569">{item.label}</text>
              </g>
            );
          })}
          {tags.slice(0, 4).map((tag: string, index: number) => (
            <TagPill
              key={index}
              x={18 + index * 96}
              y={138}
              label={tag}
              fill={index === 0 ? '#FEF3C7' : index === 1 ? '#DBEAFE' : index === 2 ? '#ECFDF5' : '#F1F5F9'}
              textFill={index === 0 ? '#92400E' : index === 1 ? '#1D4ED8' : index === 2 ? '#047857' : '#334155'}
              width={82}
            />
          ))}
        </svg>
      );
    }

    function SvgPositionMap({ data, accent }: { data: any; accent: string }) {
      const points = data.points || [];
      const tags = data.tags || [];
      return (
        <svg viewBox="0 0 420 186" className="h-[186px] w-full">
          <rect x="0" y="0" width="420" height="186" rx="22" fill="#F8FAFC" />
          <text x="18" y="24" fontSize="12" fill="#64748B">风格热度示意</text>
          <rect x="86" y="38" width="248" height="96" rx="18" fill="#FFFFFF" stroke="#E2E8F0" />
          <line x1="210" y1="48" x2="210" y2="124" stroke="#CBD5E1" strokeWidth="2" />
          <line x1="98" y1="86" x2="322" y2="86" stroke="#CBD5E1" strokeWidth="2" />
          <text x="210" y="56" textAnchor="middle" fontSize="10" fill="#94A3B8">成长</text>
          <text x="210" y="122" textAnchor="middle" fontSize="10" fill="#94A3B8">价值</text>
          <text x="102" y="90" fontSize="10" fill="#94A3B8">小盘</text>
          <text x="288" y="90" fontSize="10" fill="#94A3B8">大盘</text>
          {points.slice(0, 3).map((point: any, index: number) => {
            const x = 86 + (point.x || 0.5) * 248;
            const y = 38 + (point.y || 0.5) * 96;
            return (
              <g key={index}>
                <circle cx={x} cy={y} r={index === 0 ? 12 : 10} fill={toneColor(point.tone, accent)} />
                <text x={x + 16} y={y + 4} fontSize="11" fill="#334155">{point.label}</text>
              </g>
            );
          })}
          {tags.slice(0, 4).map((tag: string, index: number) => (
            <TagPill key={index} x={18 + index * 96} y={146} label={tag} fill="#EFF6FF" textFill="#1D4ED8" width={82} />
          ))}
        </svg>
      );
    }

    function SvgQuadrantSignal({ data }: { data: any; accent: string }) {
      const point = data.point || { x: 0.4, y: 0.3, label: '当前阶段' };
      const tags = data.tags || [];
      return (
        <svg viewBox="0 0 420 182" className="h-[182px] w-full">
          <rect x="0" y="0" width="420" height="182" rx="22" fill="#F8FAFC" />
          <text x="18" y="24" fontSize="12" fill="#64748B">市场中性环境示意</text>
          <rect x="96" y="40" width="228" height="92" rx="18" fill="#FFFFFF" stroke="#E2E8F0" />
          <line x1="210" y1="50" x2="210" y2="122" stroke="#CBD5E1" strokeWidth="2" />
          <line x1="108" y1="86" x2="312" y2="86" stroke="#CBD5E1" strokeWidth="2" />
          <text x="210" y="56" textAnchor="middle" fontSize="10" fill="#94A3B8">风格分化高</text>
          <text x="210" y="122" textAnchor="middle" fontSize="10" fill="#94A3B8">风格分化低</text>
          <text x="112" y="90" fontSize="10" fill="#94A3B8">对冲便宜</text>
          <text x="266" y="90" fontSize="10" fill="#94A3B8">对冲偏贵</text>
          <circle cx={96 + (point.x || 0.4) * 228} cy={40 + (point.y || 0.3) * 92} r="12" fill="#14B8A6" />
          <text x={96 + (point.x || 0.4) * 228 + 16} y={40 + (point.y || 0.3) * 92 + 4} fontSize="11" fill="#334155">{point.label}</text>
          {tags.slice(0, 3).map((tag: string, index: number) => (
            <TagPill
              key={index}
              x={104 + index * 84}
              y={144}
              label={tag}
              fill={index === 0 ? '#DBEAFE' : index === 1 ? '#ECFDF5' : '#FEF3C7'}
              textFill={index === 0 ? '#1D4ED8' : index === 1 ? '#047857' : '#92400E'}
              width={76}
            />
          ))}
        </svg>
      );
    }

    function SvgCycleBars({ data, accent }: { data: any; accent: string }) {
      const bars = data.bars || [];
      const tags = data.tags || [];
      return (
        <svg viewBox="0 0 420 168" className="h-[168px] w-full">
          <rect x="0" y="0" width="420" height="168" rx="22" fill="#F8FAFC" />
          <text x="18" y="24" fontSize="12" fill="#64748B">周期适配度示意</text>
          {bars.slice(0, 3).map((bar: any, index: number) => {
            const x = 110 + index * 92;
            const h = (bar.value || 3) * 20;
            return (
              <g key={index}>
                <rect x={x} y={52} width="42" height="104" rx="14" fill="none" stroke="#D6DEEA" strokeDasharray="6 6" />
                <rect x={x} y={156 - h} width="42" height={h} rx="14" fill={toneColor(bar.tone, accent)} />
                <text x={x + 21} y="164" textAnchor="middle" fontSize="10" fill="#475569">{bar.label}</text>
              </g>
            );
          })}
          {tags.slice(0, 3).map((tag: string, index: number) => (
            <TagPill
              key={index}
              x={98 + index * 98}
              y={146}
              label={tag}
              fill={index === 0 ? '#DBEAFE' : index === 1 ? '#ECFDF5' : '#FEF3C7'}
              textFill={index === 0 ? '#1D4ED8' : index === 1 ? '#047857' : '#92400E'}
              width={86}
            />
          ))}
        </svg>
      );
    }

    function SvgStructuredList({ data, accent }: { data: any; accent: string }) {
      const rows = data.rows || [];
      return (
        <svg viewBox="0 0 420 180" className="h-[180px] w-full">
          <rect x="0" y="0" width="420" height="180" rx="22" fill="#F8FAFC" />
          <text x="18" y="24" fontSize="12" fill="#64748B">资金方向示意</text>
          {rows.slice(0, 5).map((row: any, index: number) => {
            const y = 42 + index * 26;
            const isUp = row.direction === 'up';
            return (
              <g key={index}>
                <rect x="18" y={y} width="384" height="20" rx="10" fill="#FFFFFF" stroke="#E2E8F0" />
                <text x="32" y={y + 13} fontSize="10.5" fill="#334155">{row.label}</text>
                <text x="388" y={y + 13} textAnchor="end" fontSize="12" fill={isUp ? accent : '#F59E0B'}>
                  {isUp ? '↗' : '↘'}
                </text>
              </g>
            );
          })}
        </svg>
      );
    }

    function SvgBarLineNarrative({ data }: { data: any; accent: string }) {
      const bars = data.bars || [];
      const line = data.line || [];
      const tags = data.tags || [];
      const linePath = line.map((point: number, index: number) => {
        const x = 34 + index * 58;
        const y = 114 - point * 0.9;
        return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
      }).join(' ');
      return (
        <svg viewBox="0 0 420 172" className="h-[172px] w-full">
          <rect x="0" y="0" width="420" height="172" rx="22" fill="#F8FAFC" />
          <text x="18" y="24" fontSize="12" fill="#64748B">成交与情绪示意</text>
          {bars.slice(0, 6).map((bar: number, index: number) => {
            const x = 26 + index * 58;
            const h = bar * 0.7;
            return <rect key={index} x={x} y={124 - h} width="24" height={h} rx="8" fill="#2F5BEA" opacity={0.38 + index * 0.08} />;
          })}
          <path d={linePath} stroke="#C9A227" strokeWidth="3.2" fill="none" />
          {tags.slice(0, 3).map((tag: string, index: number) => (
            <TagPill
              key={index}
              x={18 + index * 102}
              y={136}
              label={tag}
              fill={index === 0 ? '#DBEAFE' : index === 1 ? '#FEF3C7' : '#F1F5F9'}
              textFill={index === 0 ? '#1D4ED8' : index === 1 ? '#92400E' : '#334155'}
              width={90}
            />
          ))}
        </svg>
      );
    }

    function SvgComparison({ items, accent }: { items: any[]; accent: string }) {
      return (
        <svg viewBox="0 0 420 128" className="h-[128px] w-full">
          <rect x="0" y="0" width="420" height="128" rx="20" fill="#F8FAFC" />
          {items.slice(0, 4).map((item, index) => {
            const x = 34 + index * 92;
            const value = Number(item.value || 60);
            const h = 24 + value;
            return (
              <g key={index}>
                <rect x={x} y={100 - h} width="42" height={h} rx="12" fill={index % 2 === 0 ? accent : '#AFC4FF'} />
                <text x={x + 21} y="116" textAnchor="middle" fontSize="11" fill="#64748B">{(item.label || '').slice(0, 6)}</text>
              </g>
            );
          })}
        </svg>
      );
    }

    function SvgMiniFlow({ steps, accent }: { steps: string[]; accent: string }) {
      return (
        <svg viewBox="0 0 420 128" className="h-[128px] w-full">
          <rect x="0" y="0" width="420" height="128" rx="20" fill="#F8FAFC" />
          <defs>
            <marker id="mini-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="#94A3B8" />
            </marker>
          </defs>
          {steps.slice(0, 3).map((step, index) => {
            const x = 18 + index * 130;
            return (
              <g key={index}>
                <rect x={x} y="38" width="110" height="44" rx="16" fill={index === 1 ? accent : '#E9EFF8'} />
                <text x={x + 55} y="64" textAnchor="middle" fontSize="12" fill={index === 1 ? '#fff' : '#0F172A'}>
                  {(step || '').slice(0, 10)}
                </text>
                {index < 2 ? <line x1={x + 112} y1="60" x2={x + 128} y2="60" stroke="#94A3B8" strokeWidth="2.5" markerEnd="url(#mini-arrow)" /> : null}
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
        [164, 96],
        [316, 86],
      ];
      return (
        <svg viewBox="0 0 420 144" className="h-[144px] w-full">
          <rect x="0" y="0" width="420" height="144" rx="22" fill="#F8FAFC" />
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

    function SvgDotMatrix({ items, accent }: { items: any[]; accent: string }) {
      return (
        <svg viewBox="0 0 420 128" className="h-[128px] w-full">
          <rect x="0" y="0" width="420" height="128" rx="20" fill="#F8FAFC" />
          {items.slice(0, 4).map((item, row) => {
            const active = Number(item.value || 2);
            return (
              <g key={row} transform={`translate(18, ${20 + row * 24})`}>
                <text x="0" y="10" fontSize="11" fill="#64748B">{item.label || `Item ${row + 1}`}</text>
                {Array.from({ length: 6 }).map((_, col) => (
                  <circle key={col} cx={178 + col * 24} cy={6} r="7" fill={col < active ? accent : '#D7DFEA'} />
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
      if (card.visualType === 'score-grid') return <SvgScoreGrid data={data} accent={accent} />;
      if (card.visualType === 'phase-shift') return <SvgPhaseShift data={data} accent={accent} />;
      if (card.visualType === 'range-position') return <SvgRangePosition data={data} accent={accent} />;
      if (card.visualType === 'theme-pillars') return <SvgThemePillars data={data} accent={accent} />;
      if (card.visualType === 'position-map') return <SvgPositionMap data={data} accent={accent} />;
      if (card.visualType === 'quadrant-signal') return <SvgQuadrantSignal data={data} accent={accent} />;
      if (card.visualType === 'cycle-bars') return <SvgCycleBars data={data} accent={accent} />;
      if (card.visualType === 'structured-list') return <SvgStructuredList data={data} accent={accent} />;
      if (card.visualType === 'bar-line-narrative') return <SvgBarLineNarrative data={data} accent={accent} />;
      if (card.visualType === 'comparison-strip') return <SvgComparison items={data.items || []} accent={accent} />;
      if (card.visualType === 'mini-flow') return <SvgMiniFlow steps={data.steps || []} accent={accent} />;
      if (card.visualType === 'dynamic-svg') return <SvgDynamicDiagram data={data} accent={accent} />;
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
