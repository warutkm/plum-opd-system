'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api, ClaimDecisionOutput, InvestigatorReportData, TraceEntry } from '../../../../lib/api';
import TraceLedgerTimeline from '../../../../components/TraceLedgerTimeline';
import InvestigatorReport from '../../../../components/InvestigatorReport';
import { Activity, CheckCircle2, XCircle, AlertTriangle, ArrowLeft, Send, ShieldAlert, BadgeCheck, FileText, User, ChevronRight } from 'lucide-react';

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
      <div className="min-h-[85vh] max-w-2xl mx-auto px-4 py-16 flex flex-col justify-center animate-fade-in">
        <div className="text-center mb-10">
          <div className="w-14 h-14 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto mb-4 glow-blue">
            <Activity className="w-6 h-6 text-blue-400 animate-spin" />
          </div>
          <h2 className="text-2xl font-bold text-white tracking-wide">Processing Claim Pipeline</h2>
          <p className="text-slate-400 text-sm mt-1.5 leading-relaxed">Executing AI extraction agents and deterministic rule engines...</p>
        </div>

        <div className="glass-card border border-white/5 rounded-2xl p-8 space-y-5 glow-blue shadow-2xl">
          {PIPELINE_STEPS.map((step, idx) => {
            const isCompleted = simStep > idx;
            const isActive = simStep === idx;
            return (
              <div key={step.id} className={`flex items-start gap-4 transition-all duration-300 ${isCompleted ? 'opacity-100' : isActive ? 'opacity-100 scale-[1.01]' : 'opacity-25'}`}>
                <div className="mt-0.5 shrink-0">
                  {isCompleted ? (
                    <div className="w-5 h-5 rounded-full bg-green-500/20 border border-green-500/35 text-green-400 flex items-center justify-center font-bold text-xs">✓</div>
                  ) : isActive ? (
                    <div className="w-5 h-5 rounded-full bg-blue-500/20 border border-blue-500/35 flex items-center justify-center">
                      <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse-glow" />
                    </div>
                  ) : (
                    <div className="w-5 h-5 rounded-full bg-slate-900/80 border border-white/10" />
                  )}
                </div>
                <div>
                  <h4 className={`text-sm font-bold tracking-wide ${isActive ? 'text-blue-400' : 'text-slate-200'}`}>{step.label}</h4>
                  <p className="text-xs text-slate-450 mt-0.5 leading-relaxed">{step.desc}</p>
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
        <XCircle className="w-14 h-14 text-red-500 mb-4" />
        <h2 className="text-xl font-bold text-white">Error Loading Claim</h2>
        <p className="text-slate-400 text-sm mt-1">{error || 'Claim details could not be retrieved'}</p>
        <button onClick={() => router.push('/')} className="mt-6 px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-sm font-semibold transition-colors border border-white/5">
          Go Back
        </button>
      </div>
    );
  }

  // Decision badges configurations (customized for beautiful dark mode glows)
  const statusConfig = {
    APPROVED: { icon: CheckCircle2, color: 'text-green-450', bg: 'bg-green-500/5 glow-green', border: 'border-green-500/25', text: 'Approved' },
    REJECTED: { icon: XCircle, color: 'text-red-450', bg: 'bg-red-500/5 glow-red', border: 'border-red-500/25', text: 'Rejected' },
    PARTIAL: { icon: AlertTriangle, color: 'text-amber-450', bg: 'bg-amber-500/5 glow-amber', border: 'border-amber-500/25', text: 'Partially Approved' },
    MANUAL_REVIEW: { icon: ShieldAlert, color: 'text-amber-450', bg: 'bg-amber-500/5 glow-amber', border: 'border-amber-500/25', text: 'Requires Manual Review' },
    PENDING: { icon: Activity, color: 'text-blue-450', bg: 'bg-blue-500/5 glow-blue', border: 'border-blue-500/25', text: 'Pending' },
  };

  // Standardize decision string for matching
  const decisionStatus = decision.decision || 'PENDING';
  const currentStatus = statusConfig[decisionStatus] || statusConfig.PENDING;
  const StatusIcon = currentStatus.icon;

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 py-10 animate-fade-in">
      <button 
        onClick={() => router.push('/')}
        className="flex items-center gap-2 text-sm font-semibold text-slate-400 hover:text-white transition-colors mb-6 group"
      >
        <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" /> Back to Upload
      </button>

      {/* Hero Header Card */}
      <div className={`p-8 rounded-2xl border ${currentStatus.bg} ${currentStatus.border} mb-8 flex flex-col md:flex-row items-center justify-between gap-6 shadow-2xl`}>
        <div className="flex items-center gap-5">
          <div className="w-14 h-14 rounded-full bg-slate-950/80 flex items-center justify-center border border-white/5 shadow-inner shrink-0">
            <StatusIcon className={`w-7 h-7 ${currentStatus.color}`} />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">
              Claim ID: {decision.claim_id}
            </div>
            <h1 className={`text-2xl md:text-3xl font-extrabold tracking-wide ${currentStatus.color}`}>
              {currentStatus.text}
            </h1>
          </div>
        </div>
        
        <div className="flex gap-8 bg-slate-950/40 p-4 px-6 rounded-xl border border-white/5 shadow-inner shrink-0 w-full md:w-auto justify-around">
          <div>
            <div className="text-xs font-bold text-slate-400 mb-1">Confidence Score</div>
            <div className="text-2xl font-extrabold text-white">{((decision.confidence_score ?? 0) * 100).toFixed(0)}%</div>
          </div>
          <div className="border-r border-white/5 my-1.5" />
          <div>
            <div className="text-xs font-bold text-slate-400 mb-1">Fraud Score</div>
            <div className={`text-2xl font-extrabold ${(decision.fraud_score ?? 0) >= 40 ? 'text-red-400' : 'text-white'}`}>
              {(decision.fraud_score ?? 0).toFixed(0)}/100
            </div>
          </div>
        </div>
      </div>

      {/* Manual Review Adjuster Action Panel */}
      {decisionStatus === 'MANUAL_REVIEW' && (
        <div className="bg-amber-500/5 border border-amber-500/25 rounded-2xl p-6 mb-8 shadow-2xl glow-amber animate-pulse-glow">
          <h3 className="font-bold text-base text-amber-400 mb-2 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-400 animate-pulse" />
            Adjuster Review Panel — Action Required
          </h3>
          <p className="text-xs text-slate-300 mb-5 leading-relaxed">
            This claim was automatically flagged due to lower AI extraction confidence or suspicious fraud indicators. Review details below, input final decisions, and log justification overrides.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-5">
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">Override Decision</label>
              <select 
                value={overrideDecision} 
                onChange={(e: any) => setOverrideDecision(e.target.value)}
                className="w-full text-sm border border-white/10 rounded-xl p-3 bg-slate-950/80 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              >
                <option value="APPROVED">Approve Claim</option>
                <option value="REJECTED">Reject Claim</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">Approved Amount (₹)</label>
              <input 
                type="number"
                value={overrideAmount}
                onChange={(e) => setOverrideAmount(e.target.value)}
                className="w-full text-sm border border-white/10 rounded-xl p-3 bg-slate-950/80 text-white placeholder-slate-650 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                placeholder={`Default: ₹${decision.approved_amount ?? 0}`}
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">Adjuster ID</label>
              <input 
                type="text"
                value={adjusterId}
                onChange={(e) => setAdjusterId(e.target.value)}
                className="w-full text-sm border border-white/10 rounded-xl p-3 bg-slate-950/80 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
            </div>
          </div>

          <div className="mb-5">
            <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">Override Justification Notes</label>
            <textarea
              value={adjusterNotes}
              onChange={(e) => setAdjusterNotes(e.target.value)}
              className="w-full text-sm border border-white/10 rounded-xl p-3 bg-slate-950/80 text-white placeholder-slate-600 h-20 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              placeholder="Provide clinical rationale or policy exception justifications for overriding this decision..."
            />
          </div>

          {overrideSuccess && (
            <div className="mb-5 p-3.5 bg-green-500/10 border border-green-500/20 text-green-400 text-xs rounded-xl font-semibold shadow-sm">
              {overrideSuccess}
            </div>
          )}
          {overrideError && (
            <div className="mb-5 p-3.5 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-xl font-semibold shadow-sm">
              {overrideError}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => handleApplyOverride('APPROVED')}
              disabled={submittingOverride}
              className="px-5 py-2.5 bg-green-600 hover:bg-green-500 text-white rounded-xl text-xs font-bold transition-all disabled:opacity-50"
            >
              Approve Claim
            </button>
            <button
              onClick={() => handleApplyOverride('REJECTED')}
              disabled={submittingOverride}
              className="px-5 py-2.5 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-bold transition-all disabled:opacity-50"
            >
              Reject Claim
            </button>
            <button
              onClick={() => handleApplyOverride('MANUAL_REVIEW')}
              disabled={submittingOverride}
              className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-bold transition-all disabled:opacity-50 border border-white/5"
            >
              Re-flag Claim
            </button>
          </div>
        </div>
      )}

      {/* Confidence Breakdown Panel */}
      {decision.confidence_breakdown && (
        <div className="glass-card border border-white/5 rounded-2xl p-6 mb-8 shadow-2xl glow-blue">
          <h3 className="font-bold text-base text-white mb-5 flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-blue-400" />
            Adjudication Confidence Analysis
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Extraction Confidence */}
            <div className="p-4 rounded-xl bg-slate-950/40 border border-white/5 flex flex-col justify-between">
              <div>
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                  Extraction Confidence (40%)
                </div>
                <div className="text-[11px] text-slate-500 mb-4 leading-relaxed">
                  Measures multimodal document data parsing integrity & validations.
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-lg font-extrabold text-white">{((decision.confidence_breakdown.extraction_confidence ?? 0) * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-white/5">
                  <div 
                    className="bg-blue-500 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${(decision.confidence_breakdown.extraction_confidence ?? 0) * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Rule Confidence */}
            <div className="p-4 rounded-xl bg-slate-950/40 border border-white/5 flex flex-col justify-between">
              <div>
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                  Rule Confidence (40%)
                </div>
                <div className="text-[11px] text-slate-500 mb-4 leading-relaxed">
                  Reflects alignment with limits, wait periods, and coverage rules.
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-lg font-extrabold text-white">{((decision.confidence_breakdown.rule_confidence ?? 0) * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-white/5">
                  <div 
                    className="bg-blue-500 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${(decision.confidence_breakdown.rule_confidence ?? 0) * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Fraud & Doc Quality */}
            <div className="p-4 rounded-xl bg-slate-950/40 border border-white/5 flex flex-col justify-between">
              <div>
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                  Fraud & Doc Quality (20%)
                </div>
                <div className="text-[11px] text-slate-500 mb-4 leading-relaxed">
                  Drops in the presence of suspect claims, duplicate scans, or blurred bills.
                </div>
              </div>
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-lg font-extrabold text-white">{((decision.confidence_breakdown.fraud_doc_quality ?? 0) * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-white/5">
                  <div 
                    className="bg-blue-500 h-full rounded-full transition-all duration-500" 
                    style={{ width: `${(decision.confidence_breakdown.fraud_doc_quality ?? 0) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="mt-5 p-3.5 bg-slate-950/60 rounded-xl border border-white/5 text-[11px] text-slate-500 text-center leading-relaxed">
            Weighted Score Formula: <span className="font-semibold text-slate-350">0.40 × Extraction</span> + <span className="font-semibold text-slate-350">0.40 × Rule</span> + <span className="font-semibold text-slate-350">0.20 × Fraud/Doc Quality</span>.
            {(decision.fraud_score ?? 0) >= 40 && (
              <span className="text-red-400 font-bold block mt-1.5">
                ⚠️ Severe Fraud Score ({decision.fraud_score}) detected. Adjudication confidence is capped at 65%.
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
          <div className="flex border-b border-white/5 gap-2">
            <button
              className={`px-5 py-3.5 text-sm font-bold border-b-2 transition-all -mb-px flex items-center gap-2 ${activeTab === 'timeline' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-450 hover:text-slate-200'}`}
              onClick={() => setActiveTab('timeline')}
            >
              <Activity className="w-4 h-4" />
              <span>Processing Timeline</span>
            </button>
            {report && (
              <button
                className={`px-5 py-3.5 text-sm font-bold border-b-2 transition-all -mb-px flex items-center gap-2 ${activeTab === 'report' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-450 hover:text-slate-200'}`}
                onClick={() => setActiveTab('report')}
              >
                <FileText className="w-4 h-4" />
                <span>Investigator Report</span>
              </button>
            )}
          </div>

          {/* Tab Panes */}
          <div className="glass-card border border-white/5 rounded-2xl p-6 shadow-2xl min-h-[420px]">
            {activeTab === 'timeline' && (
              <div>
                <div className="mb-6 p-4 rounded-xl bg-slate-950/40 border border-white/5 flex items-start gap-2.5">
                  <BadgeCheck className="w-4.5 h-4.5 text-blue-400 shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-bold text-white text-sm">Immutable Trace Ledger</h3>
                    <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">Continuous audit log of agent interactions and policy checks executed for this claim.</p>
                  </div>
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
          <div className="glass-card border border-white/5 rounded-2xl p-5 shadow-2xl flex flex-col h-[540px] glow-blue">
            <div className="border-b border-white/5 pb-3.5 mb-4">
              <h3 className="font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-400" />
                Ask Policy Assistant
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">Query the OPD policy document regarding this claim decision</p>
            </div>

            {/* Chat message history */}
            <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-1 text-xs">
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`p-3.5 rounded-xl max-w-[85%] leading-relaxed ${msg.role === 'user' ? 'bg-blue-600 text-white font-semibold' : 'bg-slate-950/70 text-slate-200 border border-white/5 shadow-inner'}`}>
                    {msg.text}
                  </div>
                  
                  {/* Citations */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 flex flex-col gap-1.5 max-w-[85%] w-full">
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">References:</span>
                      {msg.sources.map((src, sIdx) => (
                        <div key={sIdx} className="text-[10px] text-slate-400 bg-slate-950/45 p-2 rounded-lg border border-white/5 font-mono leading-normal shadow-sm">
                          <span className="font-bold text-blue-400">{src.source}: </span>
                          <span className="italic">"{src.chunk_text.slice(0, 110)}..."</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              
              {chatLoading && (
                <div className="flex items-center gap-2 text-slate-450 italic text-xs">
                  <Activity className="w-3.5 h-3.5 animate-spin text-blue-400" /> Vector search on policy terms...
                </div>
              )}
            </div>

            {/* Chat Input form */}
            <form onSubmit={handleSendChat} className="flex gap-2 pt-3.5 border-t border-white/5">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask about dental limits, co-pay..."
                className="flex-1 border border-white/10 rounded-xl px-3 py-2.5 text-xs bg-slate-950 text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                disabled={chatLoading}
              />
              <button
                type="submit"
                className="p-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl transition-all flex items-center justify-center disabled:opacity-50"
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
