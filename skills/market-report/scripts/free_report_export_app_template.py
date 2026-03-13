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
        <svg viewBox="0 0 860 140" className="h-[140px] w-full">
          <rect x="0" y="0" width="860" height="140" rx="24" fill="rgba(255,255,255,0.03)" />
          {items.slice(0, 4).map((item, index) => {
            const x = 110 + index * 205;
            const y = index % 2 === 0 ? 44 : 84;
            return (
              <g key={index}>
                {index > 0 ? <line x1={x - 118} y1={index % 2 === 0 ? 84 : 44} x2={x} y2={y} stroke="rgba(255,255,255,0.35)" strokeWidth="3" /> : null}
                <circle cx={x} cy={y} r="18" fill={accent} />
                <circle cx={x} cy={y} r="30" fill={accent} opacity="0.14" />
                <text x={x} y={126} textAnchor="middle" fontSize="22" fill="#CBD5E1">{(item.label || '').slice(0, 8)}</text>
              </g>
            );
          })}
        </svg>
      );
    }

    function SvgScoreGrid({ data, accent }: { data: any; accent: string }) {
      const rows = data.rows || [];
      return (
        <svg viewBox="0 0 860 190" className="h-[190px] w-full">
          <rect x="0" y="0" width="860" height="190" rx="24" fill="#F8FAFC" />
          <text x="28" y="28" fontSize="20" fill="#64748B">宏观温度计（示意）</text>
          <TagPill x={660} y={16} label={data.badge || '观点偏强'} fill="#DBEAFE" textFill="#1D4ED8" width={132} />
          {data.secondaryBadge ? <TagPill x={678} y={50} label={data.secondaryBadge} fill="#FEF3C7" textFill="#92400E" width={112} /> : null}
          {rows.slice(0, 5).map((row: any, index: number) => (
            <g key={index} transform={`translate(28, ${62 + index * 26})`}>
              <text x="0" y="12" fontSize="18" fill="#475569">{row.label}</text>
              {Array.from({ length: 5 }).map((_, dotIndex) => (
                <circle
                  key={dotIndex}
                  cx={520 + dotIndex * 46}
                  cy={8}
                  r="11"
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
        <svg viewBox="0 0 860 196" className="h-[196px] w-full">
          <rect x="0" y="0" width="860" height="196" rx="24" fill="#F8FAFC" />
          <text x="28" y="28" fontSize="20" fill="#64748B">市场主线切换</text>
          <defs>
            <marker id="editorial-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="#94A3B8" />
            </marker>
          </defs>
          {stages.slice(0, 3).map((label: string, index: number) => {
            const x = 30 + index * 265;
            const fill = index === 1 ? '#BFD4FF' : index === 2 ? '#0F204A' : '#E2E8F0';
            const textFill = index === 2 ? '#FFFFFF' : '#0F172A';
            return (
              <g key={index}>
                <rect x={x} y="54" width="200" height="58" rx="20" fill={fill} />
                <text x={x + 100} y="89" textAnchor="middle" fontSize="22" fill={textFill}>{label}</text>
                {index < 2 ? <line x1={x + 212} y1="83" x2={x + 246} y2="83" stroke="#94A3B8" strokeWidth="3" markerEnd="url(#editorial-arrow)" /> : null}
              </g>
            );
          })}
          {tags.slice(0, 4).map((tag: string, index: number) => (
            <TagPill
              key={index}
              x={30 + index * 195}
              y={142}
              label={tag}
              fill={index === 0 ? '#DBEAFE' : index === 1 ? '#E2E8F0' : index === 2 ? '#FEF3C7' : '#ECFDF5'}
              textFill={index === 0 ? '#1D4ED8' : index === 1 ? '#334155' : index === 2 ? '#92400E' : '#047857'}
              width={168}
            />
          ))}
        </svg>
      );
    }

    function SvgRangePosition({ data, accent }: { data: any; accent: string }) {
      const start = data.start || 26;
      const end = data.end || 76;
      const position = 72 + ((start + end) / 2) * 4.4;
      return (
        <svg viewBox="0 0 860 170" className="h-[170px] w-full">
          <rect x="0" y="0" width="860" height="170" rx="24" fill="#F8FAFC" />
          <text x="28" y="28" fontSize="20" fill="#64748B">{data.label || '区间运行示意'}</text>
          <line x1="72" y1="94" x2="790" y2="94" stroke="#CBD5E1" strokeWidth="3" strokeDasharray="10 10" />
          <rect x={72 + start * 4.4} y="72" width={Math.max(160, (end - start) * 4.4)} height="44" rx="22" fill="#CFE0FF" />
          <circle cx={position} cy="94" r="14" fill={accent} />
          <text x={position} y="99" textAnchor="middle" fontSize="12" fill="#FFFFFF">震荡</text>
          <path d="M 72 60 C 210 20, 360 120, 520 56 S 700 46, 790 58" stroke={accent} strokeWidth="4" fill="none" />
          <text x="72" y="54" fontSize="16" fill="#64748B">{data.startLabel || '低位支撑'}</text>
          <text x="790" y="54" textAnchor="end" fontSize="16" fill="#64748B">{data.endLabel || '上行受限'}</text>
          <text x="430" y="146" textAnchor="middle" fontSize="16" fill="#64748B">{data.footnote || '票息 + 区间交易'}</text>
        </svg>
      );
    }

    function SvgThemePillars({ data, accent }: { data: any; accent: string }) {
      const items = data.items || [];
      const tags = data.tags || [];
      return (
        <svg viewBox="0 0 860 184" className="h-[184px] w-full">
          <rect x="0" y="0" width="860" height="184" rx="24" fill="#F8FAFC" />
          <text x="28" y="28" fontSize="20" fill="#64748B">驱动拆解</text>
          {items.slice(0, 3).map((item: any, index: number) => {
            const x = 108 + index * 220;
            return (
              <g key={index}>
                <rect x={x} y={62 + (index === 1 ? 12 : 0)} width="46" height={62 + index * 18} rx="14" fill={toneColor(item.tone, accent)} />
                <rect x={x - 10} y="50" width="66" height="108" rx="18" fill="none" stroke="#D7DFEA" strokeDasharray="8 8" />
                <text x={x + 23} y="174" textAnchor="middle" fontSize="18" fill="#475569">{item.label}</text>
              </g>
            );
          })}
          {tags.slice(0, 4).map((tag: string, index: number) => (
            <TagPill
              key={index}
              x={28 + index * 195}
              y={148}
              label={tag}
              fill={index === 0 ? '#FEF3C7' : index === 1 ? '#DBEAFE' : index === 2 ? '#ECFDF5' : '#F1F5F9'}
              textFill={index === 0 ? '#92400E' : index === 1 ? '#1D4ED8' : index === 2 ? '#047857' : '#334155'}
              width={170}
            />
          ))}
        </svg>
      );
    }

    function SvgPositionMap({ data, accent }: { data: any; accent: string }) {
      const points = data.points || [];
      const tags = data.tags || [];
      return (
        <svg viewBox="0 0 860 208" className="h-[208px] w-full">
          <rect x="0" y="0" width="860" height="208" rx="24" fill="#F8FAFC" />
          <text x="28" y="28" fontSize="20" fill="#64748B">风格热度示意</text>
          <rect x="120" y="42" width="620" height="104" rx="18" fill="#FFFFFF" stroke="#E2E8F0" />
          <line x1="430" y1="54" x2="430" y2="134" stroke="#CBD5E1" strokeWidth="2" />
          <line x1="140" y1="94" x2="720" y2="94" stroke="#CBD5E1" strokeWidth="2" />
          <text x="430" y="58" textAnchor="middle" fontSize="16" fill="#94A3B8">成长</text>
          <text x="430" y="140" textAnchor="middle" fontSize="16" fill="#94A3B8">价值</text>
          <text x="146" y="98" fontSize="16" fill="#94A3B8">小盘</text>
          <text x="656" y="98" fontSize="16" fill="#94A3B8">大盘</text>
          {points.slice(0, 3).map((point: any, index: number) => {
            const x = 120 + (point.x || 0.5) * 620;
            const y = 42 + (point.y || 0.5) * 104;
            return (
              <g key={index}>
                <circle cx={x} cy={y} r={index === 0 ? 18 : 14} fill={toneColor(point.tone, accent)} />
                <text x={x + 22} y={y + 6} fontSize="18" fill="#334155">{point.label}</text>
              </g>
            );
          })}
          {tags.slice(0, 4).map((tag: string, index: number) => (
            <TagPill key={index} x={28 + index * 195} y={162} label={tag} fill="#EFF6FF" textFill="#1D4ED8" width={170} />
          ))}
        </svg>
      );
    }

    function SvgQuadrantSignal({ data }: { data: any; accent: string }) {
      const point = data.point || { x: 0.4, y: 0.3, label: '当前阶段' };
      const tags = data.tags || [];
      return (
        <svg viewBox="0 0 860 208" className="h-[208px] w-full">
          <rect x="0" y="0" width="860" height="208" rx="24" fill="#F8FAFC" />
          <text x="28" y="28" fontSize="20" fill="#64748B">市场中性环境示意</text>
          <rect x="150" y="42" width="560" height="106" rx="18" fill="#FFFFFF" stroke="#E2E8F0" />
          <line x1="430" y1="54" x2="430" y2="136" stroke="#CBD5E1" strokeWidth="2" />
          <line x1="170" y1="95" x2="690" y2="95" stroke="#CBD5E1" strokeWidth="2" />
          <text x="430" y="58" textAnchor="middle" fontSize="16" fill="#94A3B8">风格分化高</text>
          <text x="430" y="142" textAnchor="middle" fontSize="16" fill="#94A3B8">风格分化低</text>
          <text x="176" y="99" fontSize="16" fill="#94A3B8">对冲便宜</text>
          <text x="594" y="99" fontSize="16" fill="#94A3B8">对冲偏贵</text>
          <circle cx={150 + (point.x || 0.4) * 560} cy={42 + (point.y || 0.3) * 106} r="18" fill="#14B8A6" />
          <text x={150 + (point.x || 0.4) * 560 + 24} y={42 + (point.y || 0.3) * 106 + 6} fontSize="18" fill="#334155">{point.label}</text>
          {tags.slice(0, 3).map((tag: string, index: number) => (
            <TagPill
              key={index}
              x={154 + index * 182}
              y={164}
              label={tag}
              fill={index === 0 ? '#DBEAFE' : index === 1 ? '#ECFDF5' : '#FEF3C7'}
              textFill={index === 0 ? '#1D4ED8' : index === 1 ? '#047857' : '#92400E'}
              width={160}
            />
          ))}
        </svg>
      );
    }

    function SvgCycleBars({ data, accent }: { data: any; accent: string }) {
      const bars = data.bars || [];
      const tags = data.tags || [];
      return (
        <svg viewBox="0 0 860 190" className="h-[190px] w-full">
          <rect x="0" y="0" width="860" height="190" rx="24" fill="#F8FAFC" />
          <text x="28" y="28" fontSize="20" fill="#64748B">周期适配度示意</text>
          {bars.slice(0, 3).map((bar: any, index: number) => {
            const x = 176 + index * 170;
            const h = (bar.value || 3) * 24;
            return (
              <g key={index}>
                <rect x={x} y={58} width="72" height="112" rx="18" fill="none" stroke="#D6DEEA" strokeDasharray="8 8" />
                <rect x={x} y={170 - h} width="72" height={h} rx="18" fill={toneColor(bar.tone, accent)} />
                <text x={x + 36} y="182" textAnchor="middle" fontSize="18" fill="#475569">{bar.label}</text>
              </g>
            );
          })}
          {tags.slice(0, 3).map((tag: string, index: number) => (
            <TagPill
              key={index}
              x={150 + index * 190}
              y={146}
              label={tag}
              fill={index === 0 ? '#DBEAFE' : index === 1 ? '#ECFDF5' : '#FEF3C7'}
              textFill={index === 0 ? '#1D4ED8' : index === 1 ? '#047857' : '#92400E'}
              width={170}
            />
          ))}
        </svg>
      );
    }

    function SvgStructuredList({ data, accent }: { data: any; accent: string }) {
      const rows = data.rows || [];
      return (
        <svg viewBox="0 0 860 198" className="h-[198px] w-full">
          <rect x="0" y="0" width="860" height="198" rx="24" fill="#F8FAFC" />
          <text x="28" y="28" fontSize="20" fill="#64748B">资金方向示意</text>
          {rows.slice(0, 5).map((row: any, index: number) => {
            const y = 42 + index * 30;
            const isUp = row.direction === 'up';
            return (
              <g key={index}>
                <rect x="28" y={y} width="804" height="22" rx="11" fill="#FFFFFF" stroke="#E2E8F0" />
                <text x="48" y={y + 15} fontSize="16" fill="#334155">{row.label}</text>
                <text x="812" y={y + 15} textAnchor="end" fontSize="18" fill={isUp ? accent : '#F59E0B'}>
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
        const x = 56 + index * 116;
        const y = 128 - point * 1.2;
        return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
      }).join(' ');
      return (
        <svg viewBox="0 0 860 198" className="h-[198px] w-full">
          <rect x="0" y="0" width="860" height="198" rx="24" fill="#F8FAFC" />
          <text x="28" y="28" fontSize="20" fill="#64748B">成交与情绪示意</text>
          {bars.slice(0, 6).map((bar: number, index: number) => {
            const x = 44 + index * 116;
            const h = bar * 1.0;
            return <rect key={index} x={x} y={146 - h} width="44" height={h} rx="14" fill="#2F5BEA" opacity={0.38 + index * 0.08} />;
          })}
          <path d={linePath} stroke="#C9A227" strokeWidth="5" fill="none" />
          {tags.slice(0, 3).map((tag: string, index: number) => (
            <TagPill
              key={index}
              x={28 + index * 195}
              y={160}
              label={tag}
              fill={index === 0 ? '#DBEAFE' : index === 1 ? '#FEF3C7' : '#F1F5F9'}
              textFill={index === 0 ? '#1D4ED8' : index === 1 ? '#92400E' : '#334155'}
              width={170}
            />
          ))}
        </svg>
      );
    }

    function SvgComparison({ items, accent }: { items: any[]; accent: string }) {
      return (
        <svg viewBox="0 0 860 150" className="h-[150px] w-full">
          <rect x="0" y="0" width="860" height="150" rx="24" fill="#F8FAFC" />
          {items.slice(0, 4).map((item, index) => {
            const x = 72 + index * 190;
            const value = Number(item.value || 60);
            const h = 30 + value;
            return (
              <g key={index}>
                <rect x={x} y={118 - h} width="74" height={h} rx="18" fill={index % 2 === 0 ? accent : '#AFC4FF'} />
                <text x={x + 37} y="138" textAnchor="middle" fontSize="18" fill="#64748B">{(item.label || '').slice(0, 6)}</text>
              </g>
            );
          })}
        </svg>
      );
    }

    function SvgMiniFlow({ steps, accent }: { steps: string[]; accent: string }) {
      return (
        <svg viewBox="0 0 860 150" className="h-[150px] w-full">
          <rect x="0" y="0" width="860" height="150" rx="24" fill="#F8FAFC" />
          <defs>
            <marker id="mini-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="#94A3B8" />
            </marker>
          </defs>
          {steps.slice(0, 3).map((step, index) => {
            const x = 38 + index * 260;
            return (
              <g key={index}>
                <rect x={x} y="42" width="190" height="52" rx="18" fill={index === 1 ? accent : '#E9EFF8'} />
                <text x={x + 95} y="74" textAnchor="middle" fontSize="20" fill={index === 1 ? '#fff' : '#0F172A'}>
                  {(step || '').slice(0, 10)}
                </text>
                {index < 2 ? <line x1={x + 202} y1="68" x2={x + 238} y2="68" stroke="#94A3B8" strokeWidth="3" markerEnd="url(#mini-arrow)" /> : null}
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
        [120, 60],
        [420, 44],
        [310, 128],
        [680, 112],
      ];
      return (
        <svg viewBox="0 0 860 180" className="h-[180px] w-full">
          <rect x="0" y="0" width="860" height="180" rx="24" fill="#F8FAFC" />
          {edges.map((edge: any, index: number) => {
            const from = positions[edge.from] || positions[0];
            const to = positions[edge.to] || positions[1];
            return (
              <g key={index}>
                <path
                  d={`M ${from[0]} ${from[1]} C ${(from[0] + to[0]) / 2} ${from[1] - 24}, ${(from[0] + to[0]) / 2} ${to[1] + 24}, ${to[0]} ${to[1]}`}
                  stroke={accent}
                  strokeWidth="3"
                  fill="none"
                />
                <text x={(from[0] + to[0]) / 2} y={(from[1] + to[1]) / 2 - 10} textAnchor="middle" fontSize="14" fill="#64748B">
                  {edge.label || ''}
                </text>
              </g>
            );
          })}
          {nodes.map((node: any, index: number) => {
            const [x, y] = positions[index] || [80 + index * 60, 60];
            return (
              <g key={index}>
                <circle cx={x} cy={y} r="26" fill={index % 2 === 0 ? accent : '#D7E3FF'} />
                <text x={x} y={y + 5} textAnchor="middle" fontSize="14" fill={index % 2 === 0 ? '#fff' : '#0F172A'}>
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
        <svg viewBox="0 0 860 150" className="h-[150px] w-full">
          <rect x="0" y="0" width="860" height="150" rx="24" fill="#F8FAFC" />
          {items.slice(0, 4).map((item, row) => {
            const active = Number(item.value || 2);
            return (
              <g key={row} transform={`translate(28, ${26 + row * 28})`}>
                <text x="0" y="14" fontSize="18" fill="#64748B">{item.label || `Item ${row + 1}`}</text>
                {Array.from({ length: 6 }).map((_, col) => (
                  <circle key={col} cx={520 + col * 40} cy={8} r="10" fill={col < active ? accent : '#D7DFEA'} />
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
          <div className="mt-6 overflow-hidden rounded-[22px] border border-slate-200 bg-slate-50 px-0 py-0">
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
        <div className="min-h-screen bg-[#EEF2F6] px-4 py-6 text-slate-900">
          <div ref={captureRef} className="mx-auto w-[1080px] overflow-hidden rounded-[28px] bg-[#EEF2F6] shadow-[0_35px_100px_rgba(15,23,42,0.12)]">
            <section className="rounded-t-[28px] bg-[#12233F] px-10 pb-10 pt-10 text-white">
              <div className="text-[12px] font-bold tracking-[0.24em] text-slate-300">FREE REPORT / VIEWPOINT + SCHEMATIC</div>
              <h1 className="mt-4 text-[58px] font-black leading-[1.04] tracking-[-0.05em]">{FREE_REPORT_BRIEF.title}</h1>
              <div className="mt-5 max-w-[920px] text-[24px] font-semibold leading-[1.6] text-white/95">{lead}</div>
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

            <main className="space-y-5 bg-[#EEF2F6] px-6 py-6">
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
