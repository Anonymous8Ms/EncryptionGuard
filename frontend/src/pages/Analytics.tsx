import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchCases } from '../services/api';
import type { Case } from '../services/api';
import clsx from 'clsx';

export default function Analytics() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await fetchCases({ limit: 1000 });
        setCases(data.cases);
      } catch (err) {
        console.error('Error loading analytics:', err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  // Compute analytics
  const totalCases = cases.length;
  const criticalCases = cases.filter(c => c.risk_level === 'critical').length;
  const highCases = cases.filter(c => c.risk_level === 'high').length;
  const mediumCases = cases.filter(c => c.risk_level === 'medium').length;
  const lowCases = cases.filter(c => c.risk_level === 'low').length;

  const openCases = cases.filter(c => c.status === 'open').length;
  const investigatingCases = cases.filter(c => c.status === 'investigating').length;
  const resolvedCases = cases.filter(c => c.status === 'resolved').length;
  const dismissedCases = cases.filter(c => c.status === 'dismissed').length;

  const avgRiskScore = cases.length > 0 
    ? cases.reduce((sum, c) => sum + c.risk_score, 0) / cases.length 
    : 0;

  // Group by merchant
  const merchantCounts: Record<string, number> = {};
  cases.forEach(c => {
    merchantCounts[c.merchant_id] = (merchantCounts[c.merchant_id] || 0) + 1;
  });
  const topMerchants = Object.entries(merchantCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);

  // Group by recommended action
  const actionCounts: Record<string, number> = {};
  cases.forEach(c => {
    actionCounts[c.recommended_action] = (actionCounts[c.recommended_action] || 0) + 1;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block w-6 h-6 border-2 border-jet/20 border-t-jet animate-spin" />
          <p className="mono-label mt-4">Loading analytics...</p>
        </div>
      </div>
    );
  }

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
            <span className="mono-label">System Analytics</span>
          </div>

          <div className="col-span-3 flex items-center justify-end">
            <div className="status-indicator">
              <div className="status-dot active" />
              <span className="mono-label">Live Data</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-20 border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto min-h-[40vh]">
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label">Overview</p>
              <p className="mono-label mt-4">System-wide metrics and patterns</p>
            </div>
          </div>

          <div className="col-span-9 px-16 py-16">
            <h1 className="text-8xl font-black leading-compressed tracking-tight text-jet">
              ANALYTICS
            </h1>
            <p className="mono-label mt-8">
              Real-time analysis of {totalCases} monitored cases across {Object.keys(merchantCounts).length} merchants.
            </p>
          </div>
        </div>
      </section>

      {/* Key Metrics */}
      <section className="border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto">
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label">Key Metrics</p>
            </div>
          </div>

          <div className="col-span-9">
            <div className="grid grid-cols-4 divide-x divide-border">
              <div className="px-12 py-16">
                <p className="label mb-4">Total Cases</p>
                <p className="text-6xl font-black text-jet tracking-tight">{totalCases}</p>
              </div>
              <div className="px-12 py-16">
                <p className="label mb-4">Avg Risk Score</p>
                <p className="text-6xl font-black text-cobalt tracking-tight">
                  {(avgRiskScore * 100).toFixed(0)}%
                </p>
              </div>
              <div className="px-12 py-16">
                <p className="label mb-4">Open Cases</p>
                <p className="text-6xl font-black text-jet tracking-tight">{openCases}</p>
              </div>
              <div className="px-12 py-16">
                <p className="label mb-4">Critical</p>
                <p className="text-6xl font-black text-cobalt tracking-tight">{criticalCases}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Risk Distribution */}
      <section className="border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto">
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label">Risk Distribution</p>
            </div>
          </div>

          <div className="col-span-9 px-16 py-16">
            <div className="space-y-1">
              {[
                { label: 'CRITICAL', count: criticalCases, color: 'bg-cobalt' },
                { label: 'HIGH', count: highCases, color: 'bg-jet' },
                { label: 'MEDIUM', count: mediumCases, color: 'bg-deep' },
                { label: 'LOW', count: lowCases, color: 'bg-muted' },
              ].map((item, index) => (
                <div key={item.label} className="list-item">
                  <div className="grid grid-cols-12 gap-4 items-center">
                    <div className="col-span-1">
                      <p className="mono-label">{String(index + 1).padStart(2, '0')}</p>
                    </div>
                    <div className="col-span-3">
                      <p className="text-2xl font-bold text-jet">{item.label}</p>
                    </div>
                    <div className="col-span-6">
                      <div className="h-3 bg-border overflow-hidden">
                        <div
                          className={clsx('h-full', item.color)}
                          style={{ width: `${totalCases > 0 ? (item.count / totalCases) * 100 : 0}%` }}
                        />
                      </div>
                    </div>
                    <div className="col-span-2 text-right">
                      <p className="text-2xl font-bold text-jet">{item.count}</p>
                      <p className="mono-label">
                        {totalCases > 0 ? ((item.count / totalCases) * 100).toFixed(1) : 0}%
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Status Distribution */}
      <section className="border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto">
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label">Status Breakdown</p>
            </div>
          </div>

          <div className="col-span-9 px-16 py-16">
            <div className="grid grid-cols-3 gap-px bg-border border border-border">
              <div className="bg-cream p-8">
                <p className="mono-label mb-4">01</p>
                <p className="text-4xl font-black text-jet mb-2">{openCases}</p>
                <p className="text-lg font-bold text-jet">Open</p>
                <p className="mono-label mt-2">Awaiting review</p>
              </div>
              <div className="bg-cream p-8">
                <p className="mono-label mb-4">02</p>
                <p className="text-4xl font-black text-cobalt mb-2">{investigatingCases}</p>
                <p className="text-lg font-bold text-jet">Investigating</p>
                <p className="mono-label mt-2">Under analysis</p>
              </div>
              <div className="bg-cream p-8">
                <p className="mono-label mb-4">03</p>
                <p className="text-4xl font-black text-muted mb-2">{resolvedCases}</p>
                <p className="text-lg font-bold text-jet">Resolved</p>
                <p className="mono-label mt-2">Confirmed cases</p>
              </div>
              <div className="bg-cream p-8">
                <p className="mono-label mb-4">04</p>
                <p className="text-4xl font-black text-muted mb-2">{dismissedCases}</p>
                <p className="text-lg font-bold text-jet">Dismissed</p>
                <p className="mono-label mt-2">False positives</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Top Merchants */}
      <section className="border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto">
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label">Top Merchants</p>
              <p className="mono-label mt-4">By case volume</p>
            </div>
          </div>

          <div className="col-span-9 px-16 py-16">
            <div className="space-y-1">
              {topMerchants.map(([merchantId, count], index) => (
                <div key={merchantId} className="list-item">
                  <div className="grid grid-cols-12 gap-4 items-center">
                    <div className="col-span-1">
                      <p className="mono-label">{String(index + 1).padStart(2, '0')}</p>
                    </div>
                    <div className="col-span-6">
                      <p className="text-lg font-bold text-jet font-mono">{merchantId}</p>
                    </div>
                    <div className="col-span-3">
                      <div className="h-2 bg-border overflow-hidden">
                        <div
                          className="h-full bg-cobalt"
                          style={{ width: `${(count / topMerchants[0][1]) * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="col-span-2 text-right">
                      <p className="text-2xl font-bold text-jet">{count}</p>
                      <p className="mono-label">cases</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Recommended Actions */}
      <section className="border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto">
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label">Actions Taken</p>
              <p className="mono-label mt-4">Recommended responses</p>
            </div>
          </div>

          <div className="col-span-9 px-16 py-16">
            <div className="grid grid-cols-2 gap-px bg-border border border-border">
              {Object.entries(actionCounts).map(([action, count]) => (
                <div key={action} className="bg-cream p-8">
                  <p className="mono-label mb-4">{action.replace(/_/g, ' ').toUpperCase()}</p>
                  <p className="text-4xl font-black text-jet">{count}</p>
                </div>
              ))}
            </div>
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
            <p className="mono-label text-cream/40">v5.0 — Analytics Dashboard</p>
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
