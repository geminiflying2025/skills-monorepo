import type { ReportData } from '../types';

export async function parseReportText(text: string): Promise<ReportData> {
  const response = await fetch('/api/parse-report', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  });

  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.detail || '解析服务暂时不可用');
  }

  return payload satisfies ReportData;
}
