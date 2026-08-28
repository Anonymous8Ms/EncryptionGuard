import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

export interface Case {
  id: string;
  merchant_id: string;
  account_id: string;
  risk_score: number;
  risk_level: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'investigating' | 'resolved' | 'dismissed';
  recommended_action: string;
  created_at: string;
}

export interface GraphNode {
  id: string;
  type: 'account' | 'device' | 'ip' | 'token' | 'order' | 'payment' | 'refund';
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  properties: Record<string, unknown>;
}

export interface GraphEvidence {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface CaseDetail extends Case {
  evidence: Record<string, unknown>;
  graph_evidence: GraphEvidence;
  shap_values: Record<string, number>;
  model_version: string;
  llm_summary: string;
}

export interface CasesResponse {
  cases: Case[];
  total: number;
}

export interface FeedbackData {
  case_id: string;
  feedback: 'confirm_abuse' | 'legitimate' | 'need_more_evidence';
  analyst_notes?: string;
}

export async function fetchCases(filters?: {
  status?: string;
  risk_level?: string;
  limit?: number;
  offset?: number;
}): Promise<CasesResponse> {
  const params = new URLSearchParams();
  if (filters?.status) params.append('status', filters.status);
  if (filters?.risk_level) params.append('risk_level', filters.risk_level);
  if (filters?.limit) params.append('limit', filters.limit.toString());
  if (filters?.offset) params.append('offset', filters.offset.toString());

  const { data } = await api.get<CasesResponse>(`/cases?${params.toString()}`);
  return data;
}

export async function fetchCase(caseId: string): Promise<CaseDetail> {
  const { data } = await api.get<CaseDetail>(`/cases/${caseId}`);
  return data;
}

export async function submitFeedback(feedbackData: FeedbackData): Promise<{ status: string }> {
  const { data } = await api.post<{ status: string }>('/feedback', feedbackData);
  return data;
}
