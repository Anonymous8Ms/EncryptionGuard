import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import type { Case } from '../services/api';

const riskLevelColor: Record<string, string> = {
  critical: 'text-cobalt',
  high: 'text-jet',
  medium: 'text-deep',
  low: 'text-muted',
};

interface AlertQueueProps {
  cases: Case[];
  loading?: boolean;
}

export default function AlertQueue({ cases, loading }: AlertQueueProps) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="py-24 text-center">
        <div className="inline-block w-6 h-6 border-2 border-jet/20 border-t-jet animate-spin" />
        <p className="mono-label mt-4">Loading alert data...</p>
      </div>
    );
  }

  if (cases.length === 0) {
    return (
      <div className="py-24 text-center">
        <div className="w-16 h-16 border border-border mx-auto mb-6 flex items-center justify-center">
          <div className="w-4 h-4 bg-muted/30" />
        </div>
        <p className="text-2xl font-bold text-jet mb-2">No Active Alerts</p>
        <p className="mono-label">
          System monitoring. No coordinated abuse patterns detected.
        </p>
      </div>
    );
  }

  return (
    <div>
      {cases.map((c, index) => (
        <div
          key={c.id}
          onClick={() => navigate(`/case/${c.id}`)}
          className="list-item"
        >
          <div className="grid grid-cols-12 gap-4 items-start">
            {/* Index */}
            <div className="col-span-1">
              <p className="mono-label">{String(index + 1).padStart(3, '0')}</p>
            </div>

            {/* Main Info */}
            <div className="col-span-6">
              <div className="flex items-center gap-4 mb-2">
                <span className={clsx(
                  'text-5xl font-bold tracking-tight',
                  riskLevelColor[c.risk_level]
                )}>
                  {c.risk_level.toUpperCase()}
                </span>
              </div>
              <div className="flex items-center gap-6 mono-label">
                <span>{c.id}</span>
                <span>{c.merchant_id}</span>
                <span>{c.account_id}</span>
              </div>
            </div>

            {/* Score */}
            <div className="col-span-2 text-right">
              <p className="label mb-2">Risk Score</p>
              <p className={clsx(
                'text-4xl font-black tracking-tight',
                c.risk_score > 0.7 ? 'text-cobalt' : 
                c.risk_score > 0.4 ? 'text-jet' : 'text-muted'
              )}>
                {(c.risk_score * 100).toFixed(0)}%
              </p>
            </div>

            {/* Status & Action */}
            <div className="col-span-3 text-right">
              <p className="label mb-2">{c.status.toUpperCase()}</p>
              <p className="mono-label">
                {c.recommended_action.replace(/_/g, ' ')}
              </p>
              <p className="mono-label mt-2 text-muted">
                {new Date(c.created_at).toLocaleDateString('en-US', { 
                  month: 'short', 
                  day: 'numeric',
                  year: 'numeric'
                })}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
