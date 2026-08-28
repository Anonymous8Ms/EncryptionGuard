import { useNavigate } from 'react-router-dom';
import { AlertTriangle, ChevronRight } from 'lucide-react';
import clsx from 'clsx';
import type { Case } from '../services/api';

const riskLevelColors: Record<string, string> = {
  critical: 'bg-red-100 border-red-500 text-red-800',
  high: 'bg-orange-100 border-orange-500 text-orange-800',
  medium: 'bg-yellow-100 border-yellow-500 text-yellow-800',
  low: 'bg-green-100 border-green-500 text-green-800',
};

const riskLevelBadge: Record<string, string> = {
  critical: 'bg-red-500 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-500 text-white',
  low: 'bg-green-500 text-white',
};

interface AlertQueueProps {
  cases: Case[];
  loading?: boolean;
}

export default function AlertQueue({ cases, loading }: AlertQueueProps) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        <span className="ml-3 text-gray-500">Loading alerts...</span>
      </div>
    );
  }

  if (cases.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <AlertTriangle className="mx-auto h-12 w-12 mb-4 opacity-50" />
        <p className="text-lg">No alerts found</p>
        <p className="text-sm">Adjust filters or check back later</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {cases.map((c) => (
        <div
          key={c.id}
          onClick={() => navigate(`/case/${c.id}`)}
          className={clsx(
            'border-l-4 rounded-lg p-4 cursor-pointer hover:shadow-md transition-shadow',
            'bg-white shadow-sm',
            riskLevelColors[c.risk_level]
          )}
        >
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span
                  className={clsx(
                    'px-2 py-0.5 rounded-full text-xs font-bold uppercase',
                    riskLevelBadge[c.risk_level]
                  )}
                >
                  {c.risk_level}
                </span>
                <span className="text-sm font-mono text-gray-600">{c.id}</span>
                <span
                  className={clsx(
                    'px-2 py-0.5 rounded text-xs',
                    c.status === 'open'
                      ? 'bg-blue-100 text-blue-700'
                      : c.status === 'investigating'
                      ? 'bg-purple-100 text-purple-700'
                      : 'bg-gray-100 text-gray-700'
                  )}
                >
                  {c.status}
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <span>Merchant: {c.merchant_id}</span>
                <span>Account: {c.account_id}</span>
                <span>Risk Score: {(c.risk_score * 100).toFixed(1)}%</span>
              </div>
              <p className="text-sm text-gray-500 mt-1">{c.recommended_action}</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="text-right text-xs text-gray-400">
                {new Date(c.created_at).toLocaleString()}
              </div>
              <ChevronRight className="h-5 w-5 text-gray-400" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
