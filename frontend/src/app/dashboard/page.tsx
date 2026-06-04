'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ClaimDecisionOutput } from '../../../lib/api';
import { Search, ShieldAlert, CheckCircle2, XCircle, ArrowRight, Activity, HelpCircle } from 'lucide-react';

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
    <div className="max-w-7xl mx-auto px-4 md:px-8 py-10 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-350">
            Adjuster Dashboard
          </h1>
          <p className="text-sm text-slate-400 mt-1.5 leading-relaxed">
            Monitor incoming claims, audit automated decision outputs, and override pending items requiring manual review.
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-10">
        {/* Total Claims */}
        <div className="p-6 rounded-2xl border border-white/5 bg-slate-900/30 backdrop-blur-md hover:border-white/10 transition-all glow-blue">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Total Claims</div>
          <div className="flex items-baseline gap-2">
            <div className="text-4xl font-extrabold text-white">{stats.total}</div>
            <span className="text-xs text-slate-500 font-medium">processed</span>
          </div>
        </div>

        {/* Manual Review */}
        <div className="p-6 rounded-2xl border border-amber-500/20 bg-amber-500/5 hover:border-amber-500/35 transition-all glow-amber relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-full blur-2xl group-hover:bg-amber-500/10 transition-all" />
          <div className="text-xs font-bold text-amber-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping" />
            Needs Manual Review
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-4xl font-extrabold text-amber-400">{stats.manual}</div>
            <span className="text-xs text-amber-500/80 font-medium">flagged</span>
          </div>
        </div>

        {/* Auto-Approved */}
        <div className="p-6 rounded-2xl border border-green-500/10 bg-green-500/5 hover:border-green-500/25 transition-all glow-green">
          <div className="text-xs font-bold text-green-400 uppercase tracking-wider mb-2">Auto-Approved</div>
          <div className="flex items-baseline gap-2">
            <div className="text-4xl font-extrabold text-green-400">{stats.approved}</div>
            <span className="text-xs text-green-500/80 font-medium">claims</span>
          </div>
        </div>

        {/* Auto-Rejected */}
        <div className="p-6 rounded-2xl border border-red-500/10 bg-red-500/5 hover:border-red-500/25 transition-all glow-red">
          <div className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2">Auto-Rejected</div>
          <div className="flex items-baseline gap-2">
            <div className="text-4xl font-extrabold text-red-400">{stats.rejected}</div>
            <span className="text-xs text-red-500/80 font-medium">claims</span>
          </div>
        </div>
      </div>

      {/* Search Controls */}
      <div className="flex gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input 
            type="text" 
            placeholder="Search claim ID or decision status..."
            className="w-full pl-11 pr-4 py-3 border border-white/10 rounded-xl bg-slate-900/60 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 placeholder-slate-600 transition-all"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Claims List Table Card */}
      <div className="rounded-2xl border border-white/5 bg-slate-900/30 backdrop-blur-md shadow-2xl overflow-hidden">
        {loading ? (
          <div className="p-20 flex flex-col items-center justify-center text-slate-400">
            <Activity className="w-9 h-9 animate-spin mb-4 text-blue-500" />
            <p className="text-sm font-semibold">Loading system claim records...</p>
          </div>
        ) : error ? (
          <div className="p-20 text-center text-red-400 font-semibold">{error}</div>
        ) : filteredClaims.length === 0 ? (
          <div className="p-20 text-center text-slate-500">No claim records matched your query.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-slate-400 uppercase bg-slate-950/60 border-b border-white/5">
                <tr>
                  <th className="px-6 py-4 font-bold tracking-wider">Claim ID</th>
                  <th className="px-6 py-4 font-bold tracking-wider">Decision</th>
                  <th className="px-6 py-4 font-bold tracking-wider">Approved Amount</th>
                  <th className="px-6 py-4 font-bold tracking-wider">Confidence Score</th>
                  <th className="px-6 py-4 font-bold tracking-wider">Fraud Risk</th>
                  <th className="px-6 py-4 font-bold tracking-wider text-right">Audit Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 bg-slate-900/10">
                {filteredClaims.map((claim) => (
                  <tr key={claim.claim_id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-6 py-4.5 font-mono font-bold text-white text-xs tracking-wider">{claim.claim_id}</td>
                    <td className="px-6 py-4.5">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs font-bold border
                        ${claim.decision === 'APPROVED' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 
                          claim.decision === 'REJECTED' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                          claim.decision === 'MANUAL_REVIEW' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-sm shadow-amber-500/5' :
                          'bg-blue-500/10 text-blue-400 border-blue-500/20'}`}>
                        {claim.decision === 'APPROVED' && <CheckCircle2 className="w-3.5 h-3.5 text-green-400 animate-pulse-glow" />}
                        {claim.decision === 'REJECTED' && <XCircle className="w-3.5 h-3.5 text-red-400" />}
                        {claim.decision === 'MANUAL_REVIEW' && <ShieldAlert className="w-3.5 h-3.5 text-amber-400 animate-pulse" />}
                        {claim.decision === 'PARTIAL' && <HelpCircle className="w-3.5 h-3.5 text-blue-400" />}
                        {claim.decision}
                      </span>
                    </td>
                    <td className="px-6 py-4.5 font-bold text-white text-sm">₹{claim.approved_amount?.toLocaleString() || 0}</td>
                    <td className="px-6 py-4.5">
                      <div className="flex items-center gap-3">
                        <div className="w-full h-2 bg-slate-950 rounded-full max-w-[90px] border border-white/5 overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all duration-500 ${claim.confidence_score >= 0.8 ? 'bg-green-500 glow-green' : claim.confidence_score >= 0.5 ? 'bg-amber-500' : 'bg-red-500'}`} 
                            style={{ width: `${claim.confidence_score * 100}%` }} 
                          />
                        </div>
                        <span className="text-xs text-slate-400 font-bold font-mono">{(claim.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4.5">
                      <span className={`font-mono font-bold text-xs ${claim.fraud_score >= 70 ? 'text-red-400' : claim.fraud_score >= 40 ? 'text-amber-400' : 'text-green-400'}`}>
                        {claim.fraud_score.toFixed(0)}/100
                      </span>
                    </td>
                    <td className="px-6 py-4.5 text-right">
                      <button 
                        onClick={() => router.push(`/claim/${claim.claim_id}`)}
                        className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl border border-white/10 bg-slate-950/60 hover:bg-blue-600 hover:text-white hover:border-blue-600 text-slate-300 text-xs font-bold transition-all shadow-sm"
                      >
                        <span>Audit Details</span>
                        <ArrowRight className="w-3.5 h-3.5" />
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
