import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchCase } from '../services/api';
import type { CaseDetail as CaseDetailType } from '../services/api';
import GraphView from '../components/GraphView';
import FeedbackButtons from '../components/FeedbackButtons';
import clsx from 'clsx';

const riskLevelConfig: Record<string, { label: string; color: string }> = {
  critical: { label: 'CRITICAL', color: 'text-cobalt' },
  high: { label: 'HIGH', color: 'text-jet' },
  medium: { label: 'MEDIUM', color: 'text-deep' },
  low: { label: 'LOW', color: 'text-muted' },
};

export default function CaseDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState<CaseDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) return;

    const loadCase = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchCase(caseId);
        setCaseData(data);
      } catch (err) {
        setError('Failed to load case details. Please try again.');
        console.error('Error loading case:', err);
      } finally {
        setLoading(false);
      }
    };

    loadCase();
  }, [caseId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block w-6 h-6 border-2 border-jet/20 border-t-jet animate-spin" />
          <p className="mono-label mt-4">Loading case data...</p>
        </div>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border border-border mx-auto mb-6 flex items-center justify-center">
            <div className="w-4 h-4 bg-cobalt" />
          </div>
          <p className="text-2xl font-bold text-jet mb-2">Case Not Found</p>
          <p className="mono-label mb-8">{error || 'The requested case does not exist.'}</p>
          <button
            onClick={() => navigate('/')}
            className="btn-primary"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const shapValues = caseData.shap_values && typeof caseData.shap_values === 'object'
    ? caseData.shap_values
    : {};

  const sortedShapValues = Object.entries(shapValues)
    .map(([feature, value]) => ({ feature, value: typeof value === 'number' ? value : 0 }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  const maxShapValue = Math.max(
    ...sortedShapValues.map((s) => Math.abs(s.value)),
    0.01
  );

  const graphEvidence = caseData.graph_evidence && typeof caseData.graph_evidence === 'object'
    ? caseData.graph_evidence
    : { nodes: [], edges: [] };

  const riskConfig = riskLevelConfig[caseData.risk_level] || riskLevelConfig.low;

  return (
    <div className="min-h-screen bg-cream">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-cream/95 backdrop-blur-sm border-b border-border h-20">
        <div className="grid-12 h-full max-w-[1440px] mx-auto px-8">
          <div className="col-span-3 flex items-center">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-3 group"
            >
              <div className="w-8 h-8 border border-jet flex items-center justify-center group-hover:bg-jet group-hover:text-cream transition-colors">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </div>
              <span className="label">Back to Dashboard</span>
            </button>
          </div>

          <div className="col-span-6 flex items-center justify-center">
            <span className="mono-label">Case Analysis — {caseData.id}</span>
          </div>

          <div className="col-span-3 flex items-center justify-end">
            <div className="status-indicator">
              <div className="status-dot active" />
              <span className="mono-label">{(caseData.status || 'unknown').toUpperCase()}</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-20 border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto min-h-[60vh]">
          {/* Sidebar */}
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label mb-6">Case Details</p>
              <div className="space-y-4">
                <div>
                  <p className="mono-label">Merchant</p>
                  <p className="text-lg font-bold text-jet mt-1">{caseData.merchant_id || 'unknown'}</p>
                </div>
                <div>
                  <p className="mono-label">Account</p>
                  <p className="text-lg font-bold text-jet mt-1">{caseData.account_id || 'unknown'}</p>
                </div>
                <div>
                  <p className="mono-label">Model Version</p>
                  <p className="text-lg font-bold text-jet mt-1">{caseData.model_version || 'v5.0'}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Main */}
          <div className="col-span-9 px-16 py-16 flex flex-col justify-between">
            <div>
              <p className="label mb-6">Coordinated Abuse Detection</p>
              <h1 className="text-9xl font-black leading-compressed tracking-tight text-jet">
                CASE
                <br />
                <span className={riskConfig.color}>{riskConfig.label}</span>
              </h1>
            </div>

            <div className="mt-16">
              <p className="label mb-4">Risk Score</p>
              <div className="flex items-end gap-4">
                <p className={clsx(
                  'text-[10rem] font-black leading-none tracking-tight',
                  (caseData.risk_score || 0) > 0.7 ? 'text-cobalt' :
                  (caseData.risk_score || 0) > 0.4 ? 'text-jet' : 'text-muted'
                )}>
                  {((caseData.risk_score || 0) * 100).toFixed(0)}
                </p>
                <p className="text-4xl font-bold text-muted mb-8">%</p>
              </div>
              <p className="mono-label mt-4">
                RECOMMENDED: {(caseData.recommended_action || 'unknown').replace(/_/g, ' ').toUpperCase()}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* AI Analysis */}
      {caseData.llm_summary && (
        <section className="border-b border-border">
          <div className="grid-12 max-w-[1440px] mx-auto">
            <div className="col-span-3 border-r border-border px-8 py-16">
              <div className="sticky top-32">
                <p className="label">AI Analysis</p>
                <p className="mono-label mt-4">MiMo v2.5-pro</p>
              </div>
            </div>
            <div className="col-span-9 px-16 py-16">
              <p className="text-xl text-deep leading-relaxed">
                {caseData.llm_summary}
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Network Graph */}
      <section className="border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto">
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label">Network Graph</p>
              <p className="mono-label mt-4">Neo4j Visualization</p>
            </div>
          </div>
          <div className="col-span-9 px-16 py-16">
            <GraphView graphData={graphEvidence} />
          </div>
        </div>
      </section>

      {/* SHAP Values */}
      <section className="border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto">
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label">Feature Impact</p>
              <p className="mono-label mt-4">SHAP Attribution</p>
            </div>
          </div>
          <div className="col-span-9 px-16 py-16">
            <div className="space-y-1">
              {sortedShapValues.slice(0, 8).map((shap, index) => (
                <div key={shap.feature} className="list-item">
                  <div className="grid grid-cols-12 gap-4 items-center">
                    <div className="col-span-1">
                      <p className="mono-label">{String(index + 1).padStart(2, '0')}</p>
                    </div>
                    <div className="col-span-4">
                      <p className="text-lg font-bold text-jet">{shap.feature}</p>
                    </div>
                    <div className="col-span-5">
                      <div className="h-2 bg-border overflow-hidden">
                        <div
                          className={clsx(
                            'h-full',
                            shap.value >= 0 ? 'bg-cobalt' : 'bg-jet'
                          )}
                          style={{ width: `${(Math.abs(shap.value) / maxShapValue) * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="col-span-2 text-right">
                      <p className="mono-label">{shap.value.toFixed(4)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Feedback */}
      <section className="border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto">
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label">Analyst Decision</p>
              <p className="mono-label mt-4">Manual Review</p>
            </div>
          </div>
          <div className="col-span-9 px-16 py-16">
            <FeedbackButtons caseId={caseData.id} />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-jet text-cream">
        <div className="grid-12 max-w-[1440px] mx-auto px-8 py-12">
          <div className="col-span-3">
            <p className="text-lg font-bold tracking-tight uppercase">EncryptionGuard</p>
          </div>
          <div className="col-span-6 flex items-center justify-center">
            <p className="mono-label text-cream/40">v5.0 — Coordinated Abuse Detection</p>
          </div>
          <div className="col-span-3 flex items-center justify-end">
            <button onClick={() => navigate('/')} className="mono-label text-cream/60 hover:text-cream transition-colors">
              ← Back to Dashboard
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
