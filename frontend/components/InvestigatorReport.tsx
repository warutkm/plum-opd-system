'use client';

import React from 'react';
import { InvestigatorReportData } from '../lib/api';
import { AlertCircle, ShieldAlert, BadgeCheck, FileText, Activity } from 'lucide-react';

export default function InvestigatorReport({ report }: { report: InvestigatorReportData }) {
  if (!report || !report.claim_summary) return null;

  return (
    <div className="space-y-6 animate-fade-in text-slate-250">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl border border-white/5 bg-slate-900/40 backdrop-blur-md shadow-lg flex flex-col gap-2.5">
          <div className="text-xs font-bold text-slate-400 flex items-center gap-2">
            <FileText className="w-4 h-4 text-slate-500" /> Submitted Amount
          </div>
          <div className="text-xl font-extrabold text-white">₹{report.claim_summary.claim_amount?.toLocaleString()}</div>
        </div>
        
        <div className="p-5 rounded-2xl border border-green-500/20 bg-green-500/5 shadow-lg flex flex-col gap-2.5 glow-green animate-pulse-glow">
          <div className="text-xs font-bold text-green-400 flex items-center gap-2">
            <BadgeCheck className="w-4 h-4 text-green-400" /> Approved Amount
          </div>
          <div className="text-xl font-extrabold text-green-450">₹{report.claim_summary.approved_amount?.toLocaleString()}</div>
        </div>

        <div className="p-5 rounded-2xl border border-white/5 bg-slate-900/40 backdrop-blur-md shadow-lg flex flex-col gap-2.5">
          <div className="text-xs font-bold text-slate-400 flex items-center gap-2">
            <Activity className="w-4 h-4 text-slate-500" /> Coverage Category
          </div>
          <div className="text-lg font-extrabold text-blue-400 capitalize">{report.coverage_analysis.primary_category || "N/A"}</div>
        </div>

        <div className={`p-5 rounded-2xl border shadow-lg flex flex-col gap-2.5 ${report.fraud_analysis.fraud_score >= 40 ? 'bg-red-500/5 border-red-500/25 glow-red' : 'bg-slate-900/40 border-white/5'}`}>
          <div className={`text-xs font-bold flex items-center gap-2 ${report.fraud_analysis.fraud_score >= 40 ? 'text-red-400' : 'text-slate-400'}`}>
            <ShieldAlert className="w-4 h-4 text-red-400" /> Fraud Score
          </div>
          <div className={`text-xl font-extrabold ${report.fraud_analysis.fraud_score >= 40 ? 'text-red-450 font-black' : 'text-white'}`}>
            {report.fraud_analysis.fraud_score}/100
          </div>
        </div>
      </div>

      {/* Coverage & Limits */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-white/5 bg-slate-900/30 backdrop-blur-md shadow-lg overflow-hidden">
          <div className="p-4 border-b border-white/5 bg-slate-950/60">
            <h3 className="font-bold text-xs tracking-wider uppercase text-white flex items-center gap-2.5">
              <BadgeCheck className="w-4 h-4 text-blue-400" /> Covered vs Excluded Items
            </h3>
          </div>
          <div className="p-5 space-y-4">
            {report.coverage_analysis.covered_items?.length > 0 ? (
              <div>
                <h4 className="text-[10px] font-bold text-green-400 uppercase tracking-widest mb-2.5">Covered Items</h4>
                <ul className="space-y-2">
                  {report.coverage_analysis.covered_items.map((item: any, i: number) => (
                    <li key={i} className="flex justify-between text-xs p-3 rounded-xl bg-green-500/5 border border-green-500/10 text-slate-200">
                      <span className="font-semibold">{item.item}</span>
                      <span className="font-extrabold text-green-400">₹{item.amount}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            
            {report.coverage_analysis.excluded_items?.length > 0 ? (
              <div>
                <h4 className="text-[10px] font-bold text-red-400 uppercase tracking-widest mb-2.5">Excluded Items</h4>
                <ul className="space-y-2">
                  {report.coverage_analysis.excluded_items.map((item: any, i: number) => (
                    <li key={i} className="flex flex-col text-xs p-3 rounded-xl bg-red-500/5 border border-red-500/10 gap-1.5">
                      <div className="flex justify-between font-semibold text-slate-200">
                        <span>{item.item}</span>
                        <span className="font-extrabold text-red-400">₹{item.amount}</span>
                      </div>
                      <span className="text-[11px] text-red-400 font-bold">{item.exclusion_reason}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {(!report.coverage_analysis.covered_items?.length && !report.coverage_analysis.excluded_items?.length) && (
              <div className="text-slate-500 text-xs italic text-center py-6">No itemized breakdown details.</div>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-white/5 bg-slate-900/30 backdrop-blur-md shadow-lg overflow-hidden">
          <div className="p-4 border-b border-white/5 bg-slate-950/60">
            <h3 className="font-bold text-xs tracking-wider uppercase text-white flex items-center gap-2.5">
              <Activity className="w-4 h-4 text-blue-400" /> Financial Breakdown
            </h3>
          </div>
          <div className="p-5">
            <div className="space-y-3.5 text-xs">
              <div className="flex justify-between items-center py-2 border-b border-white/5">
                <span className="text-slate-400">Capped Covered Base Amount</span>
                <span className="font-bold text-white">₹{report.limit_analysis.capped_amount?.toLocaleString() || 0}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-white/5">
                <span className="text-slate-400">Copay Deductible (10%)</span>
                <span className="font-bold text-red-400">-₹{report.limit_analysis.copay_amount?.toLocaleString() || 0}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-white/5">
                <span className="text-slate-400">Network Hospital Cashless Discount (20%)</span>
                <span className="font-bold text-green-400">-₹{report.limit_analysis.network_discount_amount?.toLocaleString() || 0}</span>
              </div>
              <div className="flex justify-between items-center py-3.5 pt-4">
                <span className="font-bold text-white">Final Approved Adjudication Payout</span>
                <span className="text-lg font-extrabold text-green-450">₹{report.claim_summary.approved_amount?.toLocaleString() || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Fraud Signals */}
      {report.fraud_analysis.signals?.length > 0 && (
        <div className="rounded-2xl border border-red-500/25 bg-red-500/5 shadow-lg overflow-hidden glow-red animate-pulse-glow">
          <div className="p-4 border-b border-red-500/25 bg-red-950/40">
            <h3 className="font-bold text-xs tracking-wider uppercase text-red-400 flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 text-red-400" /> Fraud & Risk Assessment Flags
            </h3>
          </div>
          <div className="p-5">
            <ul className="space-y-3">
              {report.fraud_analysis.signals.map((sig: any, idx: number) => (
                <li key={idx} className="flex flex-col sm:flex-row sm:items-start gap-3.5 p-4 rounded-xl border border-white/5 bg-slate-950/70">
                  <span className={`px-2 py-1 text-[9px] font-extrabold rounded-lg uppercase w-fit tracking-widest shrink-0 text-white text-center
                    ${sig.severity === 'HIGH' || sig.severity === 'CRITICAL' ? 'bg-red-600/20 text-red-400 border border-red-550/30' : 'bg-amber-500/20 text-amber-400 border border-amber-550/30'}`}>
                    {sig.severity}
                  </span>
                  <div>
                    <p className="font-bold text-xs text-white uppercase tracking-wider">{sig.signal_type}</p>
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">{sig.description}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Decision Rationale */}
      {report.decision_rationale && (
        <div className="rounded-2xl border border-white/5 bg-slate-900/30 backdrop-blur-md shadow-lg overflow-hidden">
          <div className="p-4 border-b border-white/5 bg-slate-950/60">
            <h3 className="font-bold text-xs tracking-wider uppercase text-white flex items-center gap-2.5">
              <BadgeCheck className="w-4 h-4 text-blue-400" /> Section 5: Decision Rationale
            </h3>
          </div>
          <div className="p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center p-4 rounded-xl bg-slate-950/60 border border-white/5 gap-4">
              <div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block mb-1">Final Decision</span>
                <span className={`text-base font-extrabold tracking-wide ${report.decision_rationale.decision === 'APPROVED' || report.decision_rationale.decision === 'PARTIAL' ? 'text-green-450' : 'text-red-450'}`}>
                  {report.decision_rationale.decision}
                </span>
              </div>
              <div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block mb-1">Engine Confidence Level</span>
                <span className="text-base font-extrabold text-white font-mono">
                  {(report.decision_rationale.rule_confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            
            {report.decision_rationale.rejection_reasons?.length > 0 && (
              <div>
                <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Exclusion / Violation Flags</h4>
                <div className="flex flex-wrap gap-2.5">
                  {report.decision_rationale.rejection_reasons.map((reason: string, i: number) => (
                    <span key={i} className="px-2.5 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-mono font-bold tracking-wider">
                      {reason}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div>
              <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Decision Adjudication Notes</h4>
              <p className="text-xs text-slate-355 bg-slate-950/60 p-4 rounded-xl border border-white/5 leading-relaxed font-mono">
                {report.decision_rationale.notes || "No additional explanation notes generated."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* What-If Analysis */}
      {report.what_if_analysis && (
        <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 shadow-lg overflow-hidden glow-blue">
          <div className="p-4 border-b border-blue-500/25 bg-blue-950/40">
            <h3 className="font-bold text-xs tracking-wider uppercase text-blue-400 flex items-center gap-2.5">
              <Activity className="w-4 h-4 text-blue-400" /> Section 6: What-If Analysis & Savings Simulator
            </h3>
          </div>
          <div className="p-5">
            <div className="p-4 rounded-xl border border-white/5 bg-slate-950/60 shadow-sm flex flex-col gap-2.5">
              <div className="flex items-center gap-2.5">
                <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse-glow" />
                <h4 className="font-bold text-xs uppercase tracking-wider text-white">
                  {report.what_if_analysis.scenario?.replace(/_/g, ' ') || "Alternative Hospital Routing"}
                </h4>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed pl-4.5">
                {report.what_if_analysis.details || "Analyzing alternative claim routing paths..."}
              </p>
              {report.what_if_analysis.potential_saving > 0 && (
                <div className="mt-2 text-xs font-bold text-green-400 bg-green-500/10 border border-green-500/20 px-3 py-2 rounded-xl w-fit ml-4.5">
                  💰 Potential copay / network saving: ₹{report.what_if_analysis.potential_saving}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Policy References */}
      {report.policy_references?.length > 0 && (
        <div className="rounded-2xl border border-white/5 bg-slate-900/30 backdrop-blur-md shadow-lg overflow-hidden">
          <div className="p-4 border-b border-white/5 bg-slate-950/60">
            <h3 className="font-bold text-xs tracking-wider uppercase text-white flex items-center gap-2.5">
              <FileText className="w-4 h-4 text-blue-400" /> Policy References Applied
            </h3>
          </div>
          <div className="p-5">
            <div className="flex flex-col gap-3">
              {report.policy_references.map((ref: any, idx: number) => (
                <div key={idx} className="p-4 rounded-xl border border-white/5 bg-slate-950/60 flex flex-col gap-2.5">
                  <h4 className="font-bold text-xs text-white uppercase tracking-wider">{ref.section}</h4>
                  <div className="flex flex-wrap gap-2 pl-2">
                    {ref.rules?.map((rule: string, i: number) => (
                      <span key={i} className="px-2.5 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs text-slate-400 font-bold">
                        {rule}
                      </span>
                    )) || <span className="text-xs text-slate-500 italic">No specific rule sub-clause matches.</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Full AI Report Text */}
      {report.full_report_text && (
        <div className="rounded-2xl border border-white/5 bg-slate-900/30 backdrop-blur-md shadow-lg overflow-hidden">
          <div className="p-4 border-b border-white/5 bg-slate-950/60">
            <h3 className="font-bold text-xs tracking-wider uppercase text-white">Detailed Report Transcript</h3>
          </div>
          <div className="p-5">
            <pre className="whitespace-pre-wrap font-mono text-[10px] text-slate-300 bg-slate-950/90 p-4 rounded-xl border border-white/5 leading-relaxed max-h-[300px] overflow-y-auto scrollbar-thin">
              {report.full_report_text}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
