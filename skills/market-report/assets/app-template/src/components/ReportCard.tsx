import React from 'react';
import { motion } from 'motion/react';
import { Metric, Scenario, MarketSection } from '../types';
import { TrendingUp, TrendingDown, Minus, AlertCircle } from 'lucide-react';

interface ReportCardProps {
  section: MarketSection;
  accentColor?: string;
}

const ScoreBadge = ({ score }: { score: number }) => {
  return (
    <span className="text-slate-800">
      <span className="text-xl font-extrabold italic tracking-tighter">{score}</span>
      <span className="text-xs font-medium text-slate-400 ml-1">/100分</span>
    </span>
  );
};

const ScenarioIcon = ({ type }: { type: Scenario['type'] }) => {
  switch (type) {
    case 'optimistic': return <div className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.5)]" />;
    case 'neutral': return <div className="w-2 h-2 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.5)]" />;
    case 'pessimistic': return <div className="w-2 h-2 rounded-full bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.5)]" />;
  }
};

const ScenarioLabelColor = (type: Scenario['type']) => {
  switch (type) {
    case 'optimistic': return 'text-amber-600 bg-amber-50';
    case 'neutral': return 'text-blue-600 bg-blue-50';
    case 'pessimistic': return 'text-red-600 bg-red-50';
  }
};

export const ReportCard: React.FC<ReportCardProps> = ({ section, accentColor = '#F59E0B' }) => {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className="bg-white rounded-xl shadow-[0_2px_15px_-3px_rgba(0,0,0,0.07),0_4px_6px_-2px_rgba(0,0,0,0.05)] border border-slate-100 overflow-hidden flex flex-col h-full"
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-50 flex items-center gap-3">
        <div 
          className="w-1 h-6 rounded-full" 
          style={{ backgroundColor: accentColor }}
        />
        <h3 className="text-xl font-black text-slate-800 tracking-tight">
          {section.title}
        </h3>
      </div>

      {/* Metrics */}
      <div className="p-5 space-y-6 flex-grow">
        {section.metrics.map((metric, idx) => (
          <div key={idx} className="group">
            <div className="flex items-baseline mb-1.5">
              <span className="w-16 text-lg font-black text-slate-800 group-hover:text-amber-600 transition-colors shrink-0">{metric.name}</span>
              <ScoreBadge score={metric.score} />
            </div>
            <p className="text-[13px] text-slate-500 leading-relaxed text-justify font-medium">
              {metric.description}
            </p>
          </div>
        ))}
      </div>

      {/* Scenarios */}
      <div className="px-5 py-5 bg-slate-50/30 border-t border-slate-50">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-sm font-black text-slate-800 uppercase tracking-wider">情境推演</span>
        </div>
        <div className="space-y-4">
          {section.scenarios.map((scenario, idx) => (
            <div key={idx} className="relative pl-4 border-l-2 border-slate-100">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-tighter ${ScenarioLabelColor(scenario.type)}`}>
                    {scenario.label}
                  </span>
                  <span className="text-sm font-black text-slate-700">{scenario.probability}%</span>
                </div>
              </div>
              <p className="text-[12px] text-slate-500 leading-snug font-medium">
                {scenario.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
};
