import { useState, useEffect } from 'react';
import { fetchCases } from '../services/api';
import type { Case } from '../services/api';
import AlertQueue from '../components/AlertQueue';

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
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">EncryptionGuard</h1>
                <p className="text-sm text-gray-500">Investigator Dashboard</p>
              </div>
            </div>
            <div className="text-sm text-gray-500">
              {total} total cases
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {/* Filters */}
        <div className="mb-6 flex flex-wrap gap-4">
          <div>
            <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              id="status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="investigating">Investigating</option>
              <option value="escalated">Escalated</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          
          <div>
            <label htmlFor="risk_level" className="block text-sm font-medium text-gray-700 mb-1">
              Risk Level
            </label>
            <select
              id="risk_level"
              value={riskLevelFilter}
              onChange={(e) => setRiskLevelFilter(e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            >
              <option value="">All Risk Levels</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Alert Queue */}
        <AlertQueue cases={cases} loading={loading} />
      </main>
    </div>
  );
}
