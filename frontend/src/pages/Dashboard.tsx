import { useState, useEffect } from 'react';
import { fetchCases } from '../services/api';
import type { Case } from '../services/api';
import AlertQueue from '../components/AlertQueue';
import StatsPanel from '../components/StatsPanel';

export default function Dashboard() {
  const [cases, setCases] = useState<Case[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [riskLevelFilter, setRiskLevelFilter] = useState('');

  useEffect(() => {
    const loadCases = async () => {
      setLoading(true);
      setError(null);
      try {
        const filters: { status?: string; risk_level?: string } = {};
        if (statusFilter) filters.status = statusFilter;
        if (riskLevelFilter) filters.risk_level = riskLevelFilter;
        
        const data = await fetchCases(filters);
        setCases(data.cases);
        setTotal(data.total);
      } catch (err) {
        setError('Failed to load cases. Please try again.');
        console.error('Error loading cases:', err);
      } finally {
        setLoading(false);
      }
    };

    loadCases();
  }, [statusFilter, riskLevelFilter]);

  return (
    <div className="min-h-screen bg-cream">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-cream/95 backdrop-blur-sm border-b border-border h-20">
        <div className="grid-12 h-full max-w-[1440px] mx-auto px-8">
          {/* Logo - Columns 1-3 */}
          <div className="col-span-3 flex items-center">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-jet" />
              <span className="text-lg font-bold tracking-tight text-jet uppercase">
                EncryptionGuard
              </span>
            </div>
          </div>

          {/* Status - Columns 4-9 */}
          <div className="col-span-6 flex items-center justify-center">
            <div className="status-indicator">
              <div className="status-dot active" />
              <span className="mono-label">System Active — {total} Cases Monitored</span>
            </div>
          </div>

          {/* Nav Links - Columns 10-12 */}
          <div className="col-span-3 flex items-center justify-end gap-8">
            <a href="/" className="label hover:text-jet transition-colors">
              Dashboard
            </a>
            <a href="/analytics" className="label hover:text-jet transition-colors">
              Analytics
            </a>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-20 border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto min-h-[85vh]">
          {/* Sidebar - Columns 1-3 */}
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <div className="w-4 h-4 bg-jet mb-6" />
              <p className="label">Manifesto</p>
              <p className="mono-label mt-4 leading-relaxed">
                Real-time coordinated refund abuse detection through graph analysis and machine learning.
              </p>
            </div>
          </div>

          {/* Main - Columns 4-12 */}
          <div className="col-span-9 px-16 py-16 flex flex-col justify-between">
            <div>
              <h1 className="text-[8rem] font-black leading-compressed tracking-tight text-jet">
                FRAUD
                <br />
                <span className="text-cobalt">INTEL</span>
              </h1>
              <p className="mono-label mt-8 max-w-md">
                Identifying coordinated abuse rings across merchant networks using graph analysis, velocity scoring, and ML-powered risk assessment.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-16 mt-16">
              <div>
                <p className="text-deep text-lg leading-relaxed">
                  EncryptionGuard monitors refund patterns in real-time, detecting suspicious connections between accounts, devices, and payment tokens.
                </p>
              </div>
              <div className="flex flex-col gap-4">
                <button
                  className="btn-primary w-full"
                  onClick={() => document.getElementById('alert-queue')?.scrollIntoView({ behavior: 'smooth' })}
                >
                  View Active Cases
                </button>
                <button
                  className="btn-secondary w-full"
                  onClick={() => window.open('https://encryptionguard.onrender.com/docs', '_blank')}
                >
                  System Documentation
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto">
          {/* Sidebar */}
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label">Metrics</p>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="col-span-9">
            <StatsPanel total={total} cases={cases} />
          </div>
        </div>
      </section>

      {/* System Section */}
      <section className="border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto">
          {/* Sidebar */}
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label">System</p>
            </div>
          </div>

          {/* Content */}
          <div className="col-span-9 px-16 py-16">
            <h2 className="text-7xl font-bold leading-tight tracking-tighter text-jet mb-16">
              COORDINATED
              <br />
              ABUSE
              <br />
              DETECTION
            </h2>

            <div className="grid grid-cols-3 gap-px bg-border border border-border">
              <div className="bg-cream p-8">
                <p className="mono-label mb-4">01</p>
                <h3 className="text-xl font-bold text-jet mb-3">Graph Analysis</h3>
                <p className="text-deep text-sm leading-relaxed">
                  Neo4j-powered relationship mapping identifies connected entities across accounts, devices, and payment tokens.
                </p>
              </div>
              <div className="bg-cream p-8">
                <p className="mono-label mb-4">02</p>
                <h3 className="text-xl font-bold text-jet mb-3">ML Scoring</h3>
                <p className="text-deep text-sm leading-relaxed">
                  XGBoost model with SHAP explainability provides real-time risk scoring with full feature attribution.
                </p>
              </div>
              <div className="bg-cream p-8">
                <p className="mono-label mb-4">03</p>
                <h3 className="text-xl font-bold text-jet mb-3">Velocity Checks</h3>
                <p className="text-deep text-sm leading-relaxed">
                  Redis-powered rolling window counters detect abnormal refund patterns across 24h, 7d, and 30d windows.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Alert Queue Section */}
      <section id="alert-queue" className="border-b border-border">
        <div className="grid-12 max-w-[1440px] mx-auto">
          {/* Sidebar */}
          <div className="col-span-3 border-r border-border px-8 py-16">
            <div className="sticky top-32">
              <p className="label">Alert Queue</p>
              <p className="mono-label mt-4">{cases.length} active alerts</p>
            </div>
          </div>

          {/* Controls + Queue */}
          <div className="col-span-9 px-16 py-16">
            {/* Filters */}
            <div className="flex items-center gap-8 mb-8 pb-8 border-b border-border">
              <div>
                <label className="label block mb-3">Status</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-cream border border-border px-4 py-3 font-mono text-sm focus:outline-none focus:border-cobalt w-48"
                >
                  <option value="">All Statuses</option>
                  <option value="open">Open</option>
                  <option value="investigating">Investigating</option>
                  <option value="escalated">Escalated</option>
                  <option value="closed">Closed</option>
                </select>
              </div>
              
              <div>
                <label className="label block mb-3">Risk Level</label>
                <select
                  value={riskLevelFilter}
                  onChange={(e) => setRiskLevelFilter(e.target.value)}
                  className="bg-cream border border-border px-4 py-3 font-mono text-sm focus:outline-none focus:border-cobalt w-48"
                >
                  <option value="">All Risk Levels</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              <div className="ml-auto">
                <p className="label mb-3">Total Cases</p>
                <p className="text-5xl font-black text-jet">{total}</p>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="border border-red-300 bg-red-50 px-6 py-4 mb-8">
                <p className="mono-label text-red-600">{error}</p>
              </div>
            )}

            {/* Alert Queue */}
            <AlertQueue cases={cases} loading={loading} />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-jet text-cream">
        <div className="grid-12 max-w-[1440px] mx-auto px-8 py-16">
          <div className="col-span-3">
            <p className="text-lg font-bold tracking-tight uppercase mb-4">EncryptionGuard</p>
            <p className="text-cream/60 text-sm">Coordinated Abuse Detection System</p>
          </div>
          <div className="col-span-6 flex items-center justify-center">
            <p className="mono-label text-cream/40">
              v5.0 — Powered by XGBoost, Neo4j, and MiMo AI
            </p>
          </div>
          <div className="col-span-3 flex items-center justify-end">
            <p className="mono-label text-cream/40">
              © 2026 Xiaomi
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
