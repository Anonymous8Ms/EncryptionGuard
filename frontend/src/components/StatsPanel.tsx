import type { Case } from '../services/api';

interface StatsPanelProps {
  total: number;
  cases: Case[];
}

export default function StatsPanel({ total, cases }: StatsPanelProps) {
  const criticalCount = cases.filter(c => c.risk_level === 'critical').length;
  const highCount = cases.filter(c => c.risk_level === 'high').length;
  const openCount = cases.filter(c => c.status === 'open').length;

  return (
    <div className="grid grid-cols-4 divide-x divide-border">
      <div className="px-12 py-16">
        <p className="label mb-4">Total Cases</p>
        <p className="text-6xl font-black text-jet tracking-tight">{total}</p>
      </div>
      <div className="px-12 py-16">
        <p className="label mb-4">Critical</p>
        <p className="text-6xl font-black text-cobalt tracking-tight">{criticalCount}</p>
      </div>
      <div className="px-12 py-16">
        <p className="label mb-4">High Risk</p>
        <p className="text-6xl font-black text-jet tracking-tight">{highCount}</p>
      </div>
      <div className="px-12 py-16">
        <p className="label mb-4">Open</p>
        <p className="text-6xl font-black text-jet tracking-tight">{openCount}</p>
      </div>
    </div>
  );
}
