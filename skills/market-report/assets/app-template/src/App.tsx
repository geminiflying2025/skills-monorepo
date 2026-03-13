import React, { useState, useRef } from 'react';
import { REPORT_DATA } from './constants';
import { ReportCard } from './components/ReportCard';
import { Calendar, FileText, ShieldAlert, Upload, Download, Loader2 } from 'lucide-react';
import { toPng } from 'html-to-image';
import { ReportData } from './types';
import * as mammoth from 'mammoth';
import { parseReportText } from './lib/api';

export default function App() {
  const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\//g, '.');
  const randomIssueCount = useRef(Math.floor(Math.random() * (210 - 180 + 1)) + 180);
  
  // Generate 7 unique colors
  const accentColors = useRef<string[]>([]);
  if (accentColors.current.length === 0) {
    const colors = [
      '#F27D26', // Brand Orange
      '#0EA5E9', // Sky Blue
      '#6366F1', // Indigo
      '#EC4899', // Pink
      '#8B5CF6', // Violet
      '#06B6D4', // Cyan
      '#F59E0B', // Amber
    ];
    // Shuffle
    accentColors.current = [...colors].sort(() => Math.random() - 0.5);
  }

  const [reportData, setReportData] = useState<ReportData>({
    ...REPORT_DATA,
    title: "全市场研报",
    subtitle: "挖矿炼金",
    date: today,
    issueCount: randomIssueCount.current
  });
  const [isParsing, setIsParsing] = useState(false);
  const captureRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDownload = async () => {
    if (captureRef.current === null) return;
    try {
      const dataUrl = await toPng(captureRef.current, { 
        cacheBust: true, 
        backgroundColor: '#F8F9FA',
        pixelRatio: 2,
        filter: (node: any) => {
          // Exclude buttons and file input from capture
          if (node.classList?.contains('no-capture')) return false;
          return true;
        }
      });
      const link = document.createElement('a');
      link.download = `market-report-${reportData.date}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('Download failed', err);
    }
  };

  const parseWithAI = async (text: string) => {
    setIsParsing(true);
    try {
      const parsed = await parseReportText(text);

      if (parsed && Array.isArray(parsed.sections)) {
        setReportData(prev => ({
          ...prev,
          ...parsed,
          title: "全市场研报",
          subtitle: "挖矿炼金",
          date: parsed.date || prev.date,
          issueCount: parsed.issueCount || prev.issueCount,
          passLine: parsed.passLine || prev.passLine
        }));
      } else {
        console.error('Parsed JSON missing sections:', parsed);
        throw new Error('解析结果格式不正确，缺少 sections 栏目数据');
      }
    } catch (err) {
      console.error('AI Parsing failed', err);
      alert(`AI 解析失败: ${err instanceof Error ? err.message : '未知错误'}`);
    } finally {
      setIsParsing(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const fileName = file.name.toLowerCase();
    
    if (fileName.endsWith('.json')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const parsed = JSON.parse(e.target?.result as string);
          if (parsed && Array.isArray(parsed.sections)) {
            setReportData(prev => ({
              ...parsed,
              title: "全市场研报",
              subtitle: "挖矿炼金",
              date: prev.date,
              issueCount: prev.issueCount
            }));
          } else {
            alert('JSON 格式不正确，必须包含 sections 数组');
          }
        } catch (err) {
          alert('JSON 解析失败，请检查文件格式');
        }
      };
      reader.readAsText(file);
    } else if (fileName.endsWith('.docx') || fileName.endsWith('.doc')) {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const arrayBuffer = e.target?.result as ArrayBuffer;
        try {
          const result = await mammoth.extractRawText({ arrayBuffer });
          await parseWithAI(result.value);
        } catch (err) {
          alert('Word 文档解析失败，请确保是 .docx 格式');
        }
      };
      reader.readAsArrayBuffer(file);
    } else {
      // .txt, .md or other text files
      const reader = new FileReader();
      reader.onload = async (e) => {
        const content = e.target?.result as string;
        await parseWithAI(content);
      };
      reader.readAsText(file);
    }
  };

  return (
    <div className="min-h-screen bg-slate-200 flex justify-center overflow-x-hidden">
      <div 
        ref={captureRef} 
        className="bg-[#F8F9FA] w-full max-w-[1200px] min-h-screen shadow-2xl py-12 px-12"
      >
        {/* Top Banner / Header */}
        <header className="mb-12">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-8">
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <h1 className="text-7xl font-[900] tracking-tighter italic flex items-baseline leading-none">
                  <span className="text-slate-900">全市场研报</span>
                  <span className="text-[#F27D26] ml-3">挖矿炼金</span>
                </h1>
              </div>
              
              <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
                <div className="flex items-center gap-2 text-slate-400 font-bold text-xs uppercase tracking-widest">
                  <Calendar className="w-4 h-4" />
                  {reportData.date}
                </div>
                <div className="flex items-center gap-2 text-slate-400 font-bold text-xs uppercase tracking-widest">
                  <FileText className="w-4 h-4" />
                  本期参考研报{reportData.issueCount}篇
                </div>
                <div className="flex items-center gap-2 text-slate-400 font-bold text-xs uppercase tracking-widest">
                  <ShieldAlert className="w-4 h-4" />
                  及格线: {reportData.passLine}分
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 no-capture">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".json,.txt,.md,.doc,.docx"
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isParsing}
                className="flex items-center gap-2 px-5 py-3 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-700 hover:bg-slate-50 transition-all shadow-sm disabled:opacity-50 active:scale-95"
              >
                {isParsing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                {isParsing ? 'AI 解析中...' : '上传文档'}
              </button>
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 px-5 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg shadow-slate-300 active:scale-95"
              >
                <Download className="w-4 h-4" />
                下载图片
              </button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main>
          {/* Grid Layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {reportData.sections?.map((section, index) => {
              // Only the last section (Commodities) is full width
              const isFullWidth = index === (reportData.sections?.length || 0) - 1;
              return (
                <div key={index} className={isFullWidth ? "md:col-span-2" : ""}>
                  <ReportCard 
                    section={section} 
                    accentColor={accentColors.current[index % accentColors.current.length]} 
                  />
                </div>
              );
            })}
          </div>
        </main>
      </div>
    </div>
  );
}
