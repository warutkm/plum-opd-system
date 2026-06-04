'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ClaimDecisionOutput } from '../../../lib/api';
import { Search, ShieldAlert, CheckCircle2, XCircle, ArrowRight, Activity } from 'lucide-react';

export default function DashboardPage() {
  const router = useRouter();
  const [claims, setClaims] = useState<ClaimDecisionOutput[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function fetchClaims() {
      try {
        setLoading(true);
        const data = await api.listClaims();
        setClaims(data || []);
      } catch (err: any) {
        setError(err.message || 'Failed to load claims');
      } finally {
        setLoading(false);
      }
    }
    fetchClaims();
  }, []);

  const filteredClaims = claims.filter(c => 
    c.claim_id.toLowerCase().includes(search.toLowerCase()) ||
    c.decision.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total: claims.length,
    manual: claims.filter(c => c.decision === 'MANUAL_REVIEW').length,
    approved: claims.filter(c => c.decision === 'APPROVED').length,
    rejected: claims.filter(c => c.decision === 'REJECTED').length,
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-800 font-sans">Adjuster Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">Review flagged claims, audit system logs, and oversee automated decisions.</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Total Claims</div>
          <div className="text-3xl font-bold text-slate-800">{stats.total}</div>
        </div>
        <div className="p-5 rounded-xl border border-amber-200 bg-amber-50/50 shadow-sm animate-pulse">
          <div className="text-xs font-semibold text-amber-800 uppercase tracking-wider mb-1">Needs Manual Review</div>
          <div className="text-3xl font-bold text-amber-700">{stats.manual}</div>
        </div>
        <div className="p-5 rounded-xl border border-green-200 bg-green-50/50 shadow-sm">
          <div className="text-xs font-semibold text-green-800 uppercase tracking-wider mb-1">Auto-Approved</div>
          <div className="text-3xl font-bold text-green-700">{stats.approved}</div>
        </div>
        <div className="p-5 rounded-xl border border-red-200 bg-red-50/50 shadow-sm">
          <div className="text-xs font-semibold text-red-800 uppercase tracking-wider mb-1">Auto-Rejected</div>
          <div className="text-3xl font-bold text-red-700">{stats.rejected}</div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search claim ID or status..."
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg bg-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Claims List Table */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 flex flex-col items-center justify-center text-slate-400">
            <Activity className="w-8 h-8 animate-spin mb-4 text-blue-600" />
            Loading claims list...
          </div>
        ) : error ? (
          <div className="p-12 text-center text-red-600 font-medium">{error}</div>
        ) : filteredClaims.length === 0 ? (
          <div className="p-12 text-center text-slate-400">No claim records found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-slate-500 uppercase bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-4 font-semibold">Claim ID</th>
                  <th className="px-6 py-4 font-semibold">Decision</th>
                  <th className="px-6 py-4 font-semibold">Approved Amount</th>
                  <th className="px-6 py-4 font-semibold">Confidence</th>
                  <th className="px-6 py-4 font-semibold">Fraud Score</th>
                  <th className="px-6 py-4 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredClaims.map((claim) => (
                  <tr key={claim.claim_id} className="hover:bg-slate-50/50 transition-colors group">
                    <td className="px-6 py-4 font-semibold text-slate-700">{claim.claim_id}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border
                        ${claim.decision === 'APPROVED' ? 'bg-green-50 text-green-700 border-green-200' : 
                          claim.decision === 'REJECTED' ? 'bg-red-50 text-red-700 border-red-200' :
                          claim.decision === 'MANUAL_REVIEW' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                          'bg-blue-50 text-blue-700 border-blue-200'}`}>
                        {claim.decision === 'APPROVED' && <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />}
                        {claim.decision === 'REJECTED' && <XCircle className="w-3.5 h-3.5 text-red-600" />}
                        {claim.decision === 'MANUAL_REVIEW' && <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />}
                        {claim.decision}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-semibold text-slate-800">₹{claim.approved_amount?.toLocaleString() || 0}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-full h-1.5 bg-slate-100 rounded-full max-w-[80px] border border-slate-200">
                          <div className={`h-full rounded-full ${claim.confidence_score >= 0.8 ? 'bg-green-600' : claim.confidence_score >= 0.5 ? 'bg-amber-500' : 'bg-red-500'}`} style={{ width: `${claim.confidence_score * 100}%` }} />
                        </div>
                        <span className="text-xs text-slate-500">{(claim.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`font-semibold ${claim.fraud_score >= 70 ? 'text-red-600 font-bold' : claim.fraud_score >= 40 ? 'text-amber-600' : 'text-green-600'}`}>
                        {claim.fraud_score.toFixed(0)}/100
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => router.push(`/claim/${claim.claim_id}`)}
                        className="inline-flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-blue-600 hover:text-white hover:border-blue-600 text-slate-600 text-xs font-semibold transition-all shadow-sm"
                      >
                        Audit Details <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
