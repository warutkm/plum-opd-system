'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api, ClaimDecisionOutput, InvestigatorReportData, TraceEntry } from '../../../../lib/api';
import TraceLedgerTimeline from '../../../../components/TraceLedgerTimeline';
import InvestigatorReport from '../../../../components/InvestigatorReport';
import { Activity, CheckCircle2, XCircle, AlertTriangle, ArrowLeft, Send, ShieldAlert, BadgeCheck, FileText } from 'lucide-react';

const PIPELINE_STEPS = [
  { id: 'upload', label: 'Gateway Check & Upload', desc: 'Validates file type, size, and initializes Claim ID' },
  { id: 'extraction', label: 'Multimodal AI Extraction', desc: 'Gemini parses patient, provider, treatment date, and bill items' },
  { id: 'validation', label: 'Normalization & Cross-Validation', desc: 'Standardizes inputs and matches patient/provider IDs' },
  { id: 'coverage', label: 'Coverage Verification', desc: 'Performs rule checks on eligibility, waiting periods, and exclusions' },
  { id: 'fraud', label: 'Rule-Based Fraud Check', desc: 'Screens for same-day duplicates, billing loops, and registration mismatches' },
  { id: 'vector_fraud', label: 'Vector Similarity Fraud Check', desc: 'Embeds and queries historical claims for semantic fraud patterns' },
  { id: 'decision', label: 'Adjudication Decision Generator', desc: 'Computes limits, deductibles, co-pays, and final confidence score' }
];

export default function ClaimResultPage() {
  const params = useParams();
  const router = useRouter();
  const claimId = params.id as string;
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [decision, setDecision] = useState<ClaimDecisionOutput | null>(null);
  const [report, setReport] = useState<InvestigatorReportData | null>(null);
  const [activeTab, setActiveTab] = useState<'timeline' | 'report'>('timeline');

  // Simulated real-time timeline steps
  const [simStep, setSimStep] = useState(0);
  const [dataReady, setDataReady] = useState(false);

  // RAG Policy Assistant state
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'assistant'; text: string; sources?: any[] }[]>([
    { role: 'assistant', text: 'Hi! I am your RAG Policy Assistant. You can ask me questions about this claim, our coverage rules, or why certain items were excluded.' }
  ]);
  const [chatLoading, setChatLoading] = useState(false);

  // Adjuster Manual Override state
  const [overrideDecision, setOverrideDecision] = useState<'APPROVED' | 'REJECTED'>('APPROVED');
  const [overrideAmount, setOverrideAmount] = useState('');
  const [adjusterNotes, setAdjusterNotes] = useState('');
  const [adjusterId, setAdjusterId] = useState('ADJ_001');
  const [submittingOverride, setSubmittingOverride] = useState(false);
  const [overrideSuccess, setOverrideSuccess] = useState<string | null>(null);
  const [overrideError, setOverrideError] = useState<string | null>(null);

  // 1. Fetch backend claim data immediately
  useEffect(() => {
    async function fetchData() {
      try {
        const [decisionData, reportData] = await Promise.all([
          api.getClaimStatus(claimId),
          fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/claims/${claimId}/report`)
            .then(res => res.json())
            .catch(() => null)
        ]);
        
        setDecision(decisionData);
        setReport(reportData);
        setDataReady(true);
      } catch (err: any) {
        setError(err.message || 'Failed to load claim data');
        setDataReady(true); // Don't block loading state on error
      }
    }
    if (claimId) fetchData();
  }, [claimId]);

  // 2. Simulated real-time progress runner (600ms per step)
  useEffect(() => {
    if (simStep < PIPELINE_STEPS.length) {
      const timer = setTimeout(() => {
        setSimStep(prev => prev + 1);
      }, 600);
      return () => clearTimeout(timer);
    } else if (dataReady) {
      // Transition to final decision view when simulation is done and backend data is loaded
      setLoading(false);
    }
  }, [simStep, dataReady]);

  // Handle RAG Chat submit
  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    const msg = chatInput;
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', text: msg }]);
    setChatLoading(true);
    try {
      const response = await api.askPolicy(msg, claimId);
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        text: response.answer, 
        sources: response.sources 
      }]);
    } catch (err: any) {
      setChatMessages(prev => [...prev, { role: 'assistant', text: `Error: ${err.message || 'Failed to query policy assistant'}` }]);
    } finally {
      setChatLoading(false);
    }
  };

  // Handle Manual Override
  const handleApplyOverride = async (decisionOverride?: 'APPROVED' | 'REJECTED') => {
    setSubmittingOverride(true);
    setOverrideSuccess(null);
    setOverrideError(null);
    try {
      const dec = decisionOverride || overrideDecision;
      await api.reviewClaim(claimId, {
        override_decision: dec,
        override_amount: overrideAmount ? parseFloat(overrideAmount) : null,
        adjuster_notes: adjusterNotes || `Manual override applied: ${dec}`,
        adjuster_id: adjusterId
      });
      setOverrideSuccess(`Override applied successfully. Claim decision updated to ${dec}.`);
      
      // Refetch latest claim status to update view
      const updated = await api.getClaimStatus(claimId);
      setDecision(updated);
      
      // Also refetch report if possible
      const reportRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/claims/${claimId}/report`)
        .then(res => res.json())
        .catch(() => null);
      if (reportRes) setReport(reportRes);
    } catch (err: any) {
      setOverrideError(err.message || 'Failed to apply manual override');
    } finally {
      setSubmittingOverride(false);
    }
  };

  // Rendering simulated loading state
  if (loading) {
    return (
      <div className="min-h-[85vh] max-w-2xl mx-auto px-4 py-12 flex flex-col justify-center">
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center mx-auto mb-4">
            <Activity className="w-6 h-6 text-blue-600 animate-spin" />
          </div>
          <h2 className="text-2xl font-bold text-slate-800">Processing Claim Pipeline</h2>
          <p className="text-slate-500 text-sm mt-1">Executing AI agents and rule engine in sequence...</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          {PIPELINE_STEPS.map((step, idx) => {
            const isCompleted = simStep > idx;
            const isActive = simStep === idx;
            return (
              <div key={step.id} className={`flex items-start gap-3 transition-opacity duration-300 ${isCompleted ? 'opacity-100' : isActive ? 'opacity-100' : 'opacity-40'}`}>
                <div className="mt-0.5 shrink-0">
                  {isCompleted ? (
                    <div className="w-5 h-5 rounded-full bg-green-100 border border-green-300 text-green-700 flex items-center justify-center font-bold text-xs">✓</div>
                  ) : isActive ? (
                    <div className="w-5 h-5 rounded-full bg-blue-100 border border-blue-300 flex items-center justify-center">
                      <div className="w-2 h-2 rounded-full bg-blue-600 animate-ping" />
                    </div>
                  ) : (
                    <div className="w-5 h-5 rounded-full bg-slate-100 border border-slate-200" />
                  )}
                </div>
                <div>
                  <h4 className={`text-sm font-semibold ${isActive ? 'text-blue-600 font-bold' : 'text-slate-800'}`}>{step.label}</h4>
                  <p className="text-xs text-slate-500">{step.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (error || !decision) {
    return (
      <div className="min-h-[80vh] flex flex-col items-center justify-center p-4">
        <XCircle className="w-12 h-12 text-red-600 mb-4" />
        <h2 className="text-xl font-bold text-slate-800">Error Loading Claim</h2>
        <p className="text-slate-500 mt-1">{error || 'Claim details could not be retrieved'}</p>
        <button onClick={() => router.push('/')} className="mt-6 px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded-lg text-sm font-medium transition-colors">
          Go Back
        </button>
      </div>
    );
  }

  // Decision badges configurations
  const statusConfig = {
    APPROVED: { icon: CheckCircle2, color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200', text: 'Approved' },
    REJECTED: { icon: XCircle, color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200', text: 'Rejected' },
    PARTIAL: { icon: AlertTriangle, color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', text: 'Partially Approved' },
    MANUAL_REVIEW: { icon: ShieldAlert, color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', text: 'Requires Manual Review' },
    PENDING: { icon: Activity, color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', text: 'Pending' },
  };

  // Standardize decision string for matching
  const decisionStatus = decision.decision || 'PENDING';
  const currentStatus = statusConfig[decisionStatus] || statusConfig.PENDING;
  const StatusIcon = currentStatus.icon;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <button 
        onClick={() => router.push('/')}
        className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-800 transition-colors mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Upload
      </button>

      {/* Hero Header Card */}
      <div className={`p-8 rounded-xl border ${currentStatus.bg} ${currentStatus.border} mb-8 flex flex-col md:flex-row items-center justify-between gap-6`}>
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-white flex items-center justify-center border shadow-sm shrink-0">
            <StatusIcon className={`w-7 h-7 ${currentStatus.color}`} />
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
              Claim ID: {decision.claim_id}
            </div>
            <h1 className={`text-2xl md:text-3xl font-bold tracking-tight ${currentStatus.color}`}>
              {currentStatus.text}
            </h1>
          </div>
        </div>
        
        <div className="flex gap-8 bg-white p-4 rounded-lg border border-slate-200 shadow-sm shrink-0">
          <div>
            <div className="text-xs font-medium text-slate-500 mb-1">Confidence Score</div>
            <div className="text-2xl font-bold text-slate-800">{(decision.confidence_score * 100).toFixed(0)}%</div>
          </div>
          <div className="border-r border-slate-200 my-1" />
          <div>
            <div className="text-xs font-medium text-slate-500 mb-1">Fraud Score</div>
            <div className={`text-2xl font-bold ${decision.fraud_score >= 40 ? 'text-red-600' : 'text-slate-800'}`}>
              {decision.fraud_score.toFixed(0)}/100
            </div>
          </div>
        </div>
      </div>

      {/* Manual Review Adjuster Action Panel */}
      {decisionStatus === 'MANUAL_REVIEW' && (
        <div className="bg-amber-50/50 border border-amber-200 rounded-xl p-6 mb-8 shadow-sm">
          <h3 className="font-bold text-base text-amber-800 mb-2 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-600" />
            Adjuster Review Panel — Override Decision Required
          </h3>
          <p className="text-xs text-slate-600 mb-4">
            This claim was automatically flagged for manual review due to low confidence or critical fraud alerts. Enter the final decision and write audit notes.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Override Decision</label>
              <select 
                value={overrideDecision} 
                onChange={(e: any) => setOverrideDecision(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded p-2 bg-white"
              >
                <option value="APPROVED">Approve Claim</option>
                <option value="REJECTED">Reject Claim</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Approved Amount (₹)</label>
              <input 
                type="number"
                value={overrideAmount}
                onChange={(e) => setOverrideAmount(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded p-2"
                placeholder={`Default: ₹${decision.approved_amount}`}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Adjuster Employee ID</label>
              <input 
                type="text"
                value={adjusterId}
                onChange={(e) => setAdjusterId(e.target.value)}
                className="w-full text-sm border border-slate-300 rounded p-2"
              />
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-xs font-semibold text-slate-600 mb-1">Adjuster Justification Notes</label>
            <textarea
              value={adjusterNotes}
              onChange={(e) => setAdjusterNotes(e.target.value)}
              className="w-full text-sm border border-slate-300 rounded p-2 h-20"
              placeholder="Provide a reason for overriding this claim decision..."
            />
          </div>

          {overrideSuccess && (
            <div className="mb-4 p-3 bg-green-100 border border-green-200 text-green-700 text-xs rounded-lg font-medium">
              {overrideSuccess}
            </div>
          )}
          {overrideError && (
            <div className="mb-4 p-3 bg-red-100 border border-red-200 text-red-700 text-xs rounded-lg font-medium">
              {overrideError}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => handleApplyOverride('APPROVED')}
              disabled={submittingOverride}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded text-sm font-semibold transition-colors disabled:opacity-50"
            >
              Approve Claim
            </button>
            <button
              onClick={() => handleApplyOverride('REJECTED')}
              disabled={submittingOverride}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-semibold transition-colors disabled:opacity-50"
            >
              Reject Claim
            </button>
            <button
              onClick={() => handleApplyOverride('MANUAL_REVIEW')}
              disabled={submittingOverride}
              className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded text-sm font-semibold transition-colors disabled:opacity-50 border border-slate-300"
            >
              Re-flag Claim
            </button>
          </div>
        </div>
      )}

      {/* Confidence Breakdown Panel */}
      {decision.confidence_breakdown && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 mb-8 shadow-sm">
          <h3 className="font-semibold text-base text-slate-800 mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-600" />
            Confidence Score Breakdown
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Extraction Confidence */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between">
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Extraction Confidence (40%)
                </div>
                <div className="text-xs text-slate-500 mb-3">
                  Measures data parsing completeness and validation success.
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xl font-bold text-slate-800">{(decision.confidence_breakdown.extraction_confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-blue-600 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${decision.confidence_breakdown.extraction_confidence * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Rule Confidence */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between">
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Rule Confidence (40%)
                </div>
                <div className="text-xs text-slate-500 mb-3">
                  Drops if soft limits are exceeded or pre-auth guidelines are violated.
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xl font-bold text-slate-800">{(decision.confidence_breakdown.rule_confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-blue-600 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${decision.confidence_breakdown.rule_confidence * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Fraud & Doc Quality */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between">
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                  Fraud & Doc Quality (20%)
                </div>
                <div className="text-xs text-slate-500 mb-3">
                  Factored down by high fraud scores or missing documents.
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xl font-bold text-slate-800">{(decision.confidence_breakdown.fraud_doc_quality * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-blue-600 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${decision.confidence_breakdown.fraud_doc_quality * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 p-3 bg-slate-100 rounded-lg border border-slate-200 text-xs text-slate-500 text-center">
            Weighted Score Formula: <span className="font-semibold text-slate-700">0.40 × Extraction</span> + <span className="font-semibold text-slate-700">0.40 × Rule</span> + <span className="font-semibold text-slate-700">0.20 × Fraud/Doc Quality</span>.
            {decision.fraud_score >= 40 && (
              <span className="text-red-600 font-semibold block mt-1">
                ⚠️ Fraud Score ({decision.fraud_score}) is $\ge$ 40. Final confidence is capped at 65%.
              </span>
            )}
          </div>
        </div>
      )}

      {/* Main Content Grid: Tabs and Chat */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Columns: Tabs and Data */}
        <div className="lg:col-span-2 space-y-6">
          {/* Tab Selector */}
          <div className="flex border-b border-slate-200">
            <button
              className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors -mb-px ${activeTab === 'timeline' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'}`}
              onClick={() => setActiveTab('timeline')}
            >
              Processing Timeline
            </button>
            {report && (
              <button
                className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors -mb-px ${activeTab === 'report' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'}`}
                onClick={() => setActiveTab('report')}
              >
                Investigator Report
              </button>
            )}
          </div>

          {/* Tab Panes */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm min-h-[400px]">
            {activeTab === 'timeline' && (
              <div>
                <div className="mb-6 p-4 rounded-lg bg-slate-50 border border-slate-200">
                  <h3 className="font-bold text-slate-800 text-sm mb-1">Immutable Trace Ledger</h3>
                  <p className="text-xs text-slate-500">Every agent interaction and deterministic rule check is logged sequentially for 100% auditability.</p>
                </div>
                <TraceLedgerTimeline traces={decision.trace_summary} />
              </div>
            )}
            
            {activeTab === 'report' && report && (
              <InvestigatorReport report={report} />
            )}
          </div>
        </div>

        {/* Right 1 Column: RAG Policy Assistant Chat */}
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col h-[520px]">
            <div className="border-b border-slate-200 pb-3 mb-4">
              <h3 className="font-bold text-slate-800 flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-600" />
                Ask Policy Assistant
              </h3>
              <p className="text-xs text-slate-500">Query policy guidelines related to this claim</p>
            </div>

            {/* Chat message history */}
            <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-1 text-sm">
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`p-3 rounded-lg max-w-[90%] leading-relaxed ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-800 border border-slate-200'}`}>
                    {msg.text}
                  </div>
                  
                  {/* Citations */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-1 flex flex-col gap-1 max-w-[90%]">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">References:</span>
                      {msg.sources.map((src, sIdx) => (
                        <div key={sIdx} className="text-[11px] text-slate-500 bg-slate-50 p-1.5 rounded border border-slate-200 font-mono leading-tight">
                          <span className="font-bold text-slate-700">{src.source}: </span>
                          <span>{src.chunk_text.slice(0, 100)}...</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              
              {chatLoading && (
                <div className="flex items-center gap-2 text-slate-400 italic text-xs">
                  <Activity className="w-3.5 h-3.5 animate-spin" /> Querying knowledge base...
                </div>
              )}
            </div>

            {/* Chat Input form */}
            <form onSubmit={handleSendChat} className="flex gap-2 pt-2 border-t border-slate-150">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask about waiting periods, rules..."
                className="flex-1 border border-slate-300 rounded p-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                disabled={chatLoading}
              />
              <button
                type="submit"
                className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors flex items-center justify-center disabled:opacity-50"
                disabled={chatLoading}
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
