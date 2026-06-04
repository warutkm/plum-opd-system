'use client';

import React from 'react';
import { InvestigatorReportData } from '../lib/api';
import { AlertCircle, ShieldAlert, BadgeCheck, FileText, Activity } from 'lucide-react';

export default function InvestigatorReport({ report }: { report: InvestigatorReportData }) {
  if (!report || !report.claim_summary) return null;

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm flex flex-col gap-2">
          <div className="text-xs font-semibold text-slate-500 flex items-center gap-2">
            <FileText className="w-4 h-4 text-slate-400" /> Submitted Amount
          </div>
          <div className="text-xl font-bold text-slate-800">₹{report.claim_summary.claim_amount?.toLocaleString()}</div>
        </div>
        
        <div className="p-4 rounded-xl border border-green-200 bg-green-50/50 shadow-sm flex flex-col gap-2">
          <div className="text-xs font-semibold text-green-800 flex items-center gap-2">
            <BadgeCheck className="w-4 h-4 text-green-600" /> Approved Amount
          </div>
          <div className="text-xl font-bold text-green-700">₹{report.claim_summary.approved_amount?.toLocaleString()}</div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm flex flex-col gap-2">
          <div className="text-xs font-semibold text-slate-500 flex items-center gap-2">
            <Activity className="w-4 h-4 text-slate-400" /> Coverage Category
          </div>
          <div className="text-lg font-bold text-slate-700 capitalize">{report.coverage_analysis.primary_category || "N/A"}</div>
        </div>

        <div className={`p-4 rounded-xl border shadow-sm flex flex-col gap-2 ${report.fraud_analysis.fraud_score >= 40 ? 'bg-red-50 border-red-200' : 'bg-white border-slate-200'}`}>
          <div className={`text-xs font-semibold flex items-center gap-2 ${report.fraud_analysis.fraud_score >= 40 ? 'text-red-800' : 'text-slate-500'}`}>
            <ShieldAlert className="w-4 h-4 text-red-500" /> Fraud Score
          </div>
          <div className={`text-xl font-bold ${report.fraud_analysis.fraud_score >= 40 ? 'text-red-600 font-extrabold' : 'text-slate-800'}`}>
            {report.fraud_analysis.fraud_score}/100
          </div>
        </div>
      </div>

      {/* Coverage & Limits */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50">
            <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
              <BadgeCheck className="w-4 h-4 text-blue-600" /> Covered vs Excluded Items
            </h3>
          </div>
          <div className="p-4 space-y-4">
            {report.coverage_analysis.covered_items?.length > 0 ? (
              <div>
                <h4 className="text-xs font-bold text-green-700 uppercase tracking-wider mb-2">Covered Items</h4>
                <ul className="space-y-2">
                  {report.coverage_analysis.covered_items.map((item: any, i: number) => (
                    <li key={i} className="flex justify-between text-sm p-2.5 rounded bg-green-50/50 border border-green-250 text-slate-800">
                      <span className="font-medium">{item.item}</span>
                      <span className="font-semibold text-slate-700">₹{item.amount}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            
            {report.coverage_analysis.excluded_items?.length > 0 ? (
              <div>
                <h4 className="text-xs font-bold text-red-700 uppercase tracking-wider mb-2">Excluded Items</h4>
                <ul className="space-y-2">
                  {report.coverage_analysis.excluded_items.map((item: any, i: number) => (
                    <li key={i} className="flex flex-col text-sm p-2.5 rounded bg-red-50/50 border border-red-200">
                      <div className="flex justify-between font-medium text-slate-800 mb-1">
                        <span>{item.item}</span>
                        <span className="font-semibold text-slate-750">₹{item.amount}</span>
                      </div>
                      <span className="text-xs text-red-600 font-medium">{item.exclusion_reason}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {(!report.coverage_analysis.covered_items?.length && !report.coverage_analysis.excluded_items?.length) && (
              <div className="text-slate-400 text-sm italic text-center py-6">No itemized breakdown details.</div>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50">
            <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-600" /> Financial Breakdown
            </h3>
          </div>
          <div className="p-4">
            <div className="space-y-3">
              <div className="flex justify-between items-center py-2 border-b border-slate-100">
                <span className="text-sm text-slate-500">Capped Covered Base Amount</span>
                <span className="font-semibold text-slate-800">₹{report.limit_analysis.capped_amount?.toLocaleString() || 0}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-100">
                <span className="text-sm text-slate-500">Copay Deductible (10%)</span>
                <span className="font-semibold text-red-600">-₹{report.limit_analysis.copay_amount?.toLocaleString() || 0}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-100">
                <span className="text-sm text-slate-500">Network Hospital Cashless Discount (20%)</span>
                <span className="font-semibold text-green-600">-₹{report.limit_analysis.network_discount_amount?.toLocaleString() || 0}</span>
              </div>
              <div className="flex justify-between items-center py-3 pt-4">
                <span className="font-bold text-slate-800 text-sm">Final Approved Adjudication Payout</span>
                <span className="text-xl font-black text-green-700">₹{report.claim_summary.approved_amount?.toLocaleString() || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Fraud Signals */}
      {report.fraud_analysis.signals?.length > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50/20 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-red-200 bg-red-50/50">
            <h3 className="font-bold text-sm text-red-800 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-650" /> Fraud & Risk Assessment Flags
            </h3>
          </div>
          <div className="p-4">
            <ul className="space-y-3">
              {report.fraud_analysis.signals.map((sig: any, idx: number) => (
                <li key={idx} className="flex flex-col sm:flex-row sm:items-start gap-3 p-3.5 rounded-lg border border-slate-200 bg-white">
                  <span className={`px-2 py-0.5 text-[10px] font-bold rounded uppercase w-fit tracking-wider shrink-0 mt-0.5 text-white
                    ${sig.severity === 'HIGH' || sig.severity === 'CRITICAL' ? 'bg-red-600' : 'bg-amber-500'}`}>
                    {sig.severity}
                  </span>
                  <div>
                    <p className="font-bold text-sm text-slate-800">{sig.signal_type}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{sig.description}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Decision Rationale */}
      {report.decision_rationale && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50">
            <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
              <BadgeCheck className="w-4 h-4 text-blue-600" /> Section 5: Decision Rationale
            </h3>
          </div>
          <div className="p-4 space-y-4">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center p-3 rounded-lg bg-slate-50 border border-slate-200 gap-3">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-0.5">Final Decision</span>
                <span className={`text-base font-extrabold ${report.decision_rationale.decision === 'APPROVED' || report.decision_rationale.decision === 'PARTIAL' ? 'text-green-700' : 'text-red-700'}`}>
                  {report.decision_rationale.decision}
                </span>
              </div>
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-0.5">Engine Confidence Level</span>
                <span className="text-base font-extrabold text-slate-800">
                  {(report.decision_rationale.rule_confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            
            {report.decision_rationale.rejection_reasons?.length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Exclusion / Violation Flags</h4>
                <div className="flex flex-wrap gap-2">
                  {report.decision_rationale.rejection_reasons.map((reason: string, i: number) => (
                    <span key={i} className="px-2.5 py-1 rounded bg-red-50 border border-red-150 text-red-700 text-xs font-mono font-semibold">
                      {reason}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div>
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">Decision Adjudication Notes</h4>
              <p className="text-xs text-slate-600 bg-slate-50 p-3.5 rounded-lg border border-slate-200 leading-relaxed font-mono">
                {report.decision_rationale.notes || "No additional explanation notes generated."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* What-If Analysis */}
      {report.what_if_analysis && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/10 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-blue-200 bg-blue-50/50">
            <h3 className="font-bold text-sm text-blue-800 flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-600" /> Section 6: What-If Analysis & Savings Simulator
            </h3>
          </div>
          <div className="p-4">
            <div className="p-4 rounded-lg border border-slate-200 bg-white shadow-sm flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-600" />
                <h4 className="font-bold text-sm text-slate-800 capitalize">
                  {report.what_if_analysis.scenario?.replace(/_/g, ' ') || "Alternative Hospital Routing"}
                </h4>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed pl-4">
                {report.what_if_analysis.details || "Analyzing alternative claim routing paths..."}
              </p>
              {report.what_if_analysis.potential_saving > 0 && (
                <div className="mt-2 text-xs font-semibold text-green-700 bg-green-50 border border-green-150 p-2.5 rounded w-fit">
                  💰 Potential copay / network saving: ₹{report.what_if_analysis.potential_saving}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Policy References */}
      {report.policy_references?.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50">
            <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-600" /> Policy References Applied
            </h3>
          </div>
          <div className="p-4">
            <div className="flex flex-col gap-3">
              {report.policy_references.map((ref: any, idx: number) => (
                <div key={idx} className="p-3 rounded-lg border border-slate-200 bg-slate-50 flex flex-col gap-1.5">
                  <h4 className="font-bold text-xs text-slate-700 uppercase tracking-wide">{ref.section}</h4>
                  <div className="flex flex-wrap gap-2 pl-2">
                    {ref.rules?.map((rule: string, i: number) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-white border border-slate-300 text-xs text-slate-500 font-medium">
                        {rule}
                      </span>
                    )) || <span className="text-xs text-slate-400 italic">No specific rule sub-clause matches.</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Full AI Report Text */}
      {report.full_report_text && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50">
            <h3 className="font-bold text-sm text-slate-800">Detailed Report Transcript</h3>
          </div>
          <div className="p-6">
            <pre className="whitespace-pre-wrap font-mono text-xs text-slate-600 bg-slate-50 p-4 rounded border border-slate-200 leading-relaxed max-h-[300px] overflow-y-auto">
              {report.full_report_text}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
