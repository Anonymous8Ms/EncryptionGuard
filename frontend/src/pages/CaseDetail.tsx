import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchCase } from '../services/api';
import type { CaseDetail as CaseDetailType } from '../services/api';
import GraphView from '../components/GraphView';
import FeedbackButtons from '../components/FeedbackButtons';

const riskLevelBadgeColors: Record<string, string> = {
  critical: 'bg-red-500 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-500 text-white',
  low: 'bg-green-500 text-white',
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
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent"></div>
          <p className="mt-2 text-gray-500">Loading case details...</p>
        </div>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error || 'Case not found'}</p>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Convert shap_values Record<string, number> to sorted array for the bar chart
  const sortedShapValues = Object.entries(caseData.shap_values)
    .map(([feature, value]) => ({ feature, value }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  const maxShapValue = Math.max(
    ...sortedShapValues.map((s) => Math.abs(s.value)),
    0.01
  );

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-gray-900 font-mono">{caseData.id}</h1>
              <span className={`px-3 py-1 rounded-full text-sm font-bold ${riskLevelBadgeColors[caseData.risk_level]}`}>
                {caseData.risk_level.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 space-y-6">
        {/* Risk Assessment Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk Assessment</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm text-gray-500">Risk Score</p>
              <p className="text-3xl font-bold text-gray-900">
                {(caseData.risk_score * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Recommended Action</p>
              <p className="text-lg font-medium text-gray-900">{caseData.recommended_action}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Model Version</p>
              <p className="text-lg font-medium text-gray-900">{caseData.model_version}</p>
            </div>
          </div>
        </div>

        {/* LLM Summary Card (if available) */}
        {caseData.llm_summary && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">LLM Analysis Summary</h2>
            <p className="text-gray-700 whitespace-pre-wrap">{caseData.llm_summary}</p>
          </div>
        )}

        {/* Graph View */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Transaction Graph</h2>
          <GraphView graphData={caseData.graph_evidence} />
        </div>

        {/* SHAP Values Bar Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">SHAP Feature Importance</h2>
          <div className="space-y-3">
            {sortedShapValues.map((shap) => (
              <div key={shap.feature} className="flex items-center gap-4">
                <div className="w-40 text-sm text-gray-700 text-right truncate" title={shap.feature}>
                  {shap.feature}
                </div>
                <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${shap.value >= 0 ? 'bg-indigo-500' : 'bg-red-400'}`}
                    style={{ width: `${(Math.abs(shap.value) / maxShapValue) * 100}%` }}
                  />
                </div>
                <div className="w-16 text-sm font-mono text-gray-600">
                  {shap.value.toFixed(4)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Feedback Buttons */}
        <div className="bg-white rounded-lg shadow p-6">
          <FeedbackButtons caseId={caseData.id} />
        </div>
      </main>
    </div>
  );
}
