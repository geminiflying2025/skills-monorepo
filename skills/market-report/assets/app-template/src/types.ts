export interface Metric {
  name: string;
  score: number;
  description: string;
}

export interface Scenario {
  type: 'optimistic' | 'neutral' | 'pessimistic';
  label: string;
  probability: number;
  description: string;
}

export interface MarketSection {
  title: string;
  metrics: Metric[];
  scenarios: Scenario[];
}

export interface ReportData {
  title: string;
  subtitle: string;
  date: string;
  issueCount: number;
  passLine: number;
  sections: MarketSection[];
}
