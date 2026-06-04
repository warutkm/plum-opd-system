'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, FileText, CheckCircle2, AlertCircle, ChevronRight, Activity, Calendar, ShieldCheck, Landmark, User, Info } from 'lucide-react';
import { api } from '../../lib/api';

export default function Home() {
  const router = useRouter();
  const [dragActive, setDragActive] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states matching Point 12: Page 1 (Claim Submission)
  const [memberId, setMemberId] = useState('EMP001');
  const [claimAmount, setClaimAmount] = useState('1500');
  const [treatmentDate, setTreatmentDate] = useState('2024-11-01');
  const [hospitalName, setHospitalName] = useState('Apollo Hospitals');
  const [isCashless, setIsCashless] = useState(true);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files) {
      const newFiles = Array.from(e.dataTransfer.files);
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const onSubmit = async () => {
    if (files.length === 0) {
      setError("Please upload a claim document first.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const formData = new FormData();
      files.forEach((f) => {
        formData.append('files', f);
      });
      formData.append('member_id', memberId);
      formData.append('claim_amount', claimAmount);
      formData.append('treatment_date', treatmentDate);
      formData.append('hospital_name', hospitalName);
      formData.append('is_cashless', isCashless ? 'true' : 'false');

      const response = await api.uploadClaim(formData);
      // Redirect to the newly created claim processing timeline (Page 2)
      router.push(`/claim/${response.claim_id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to submit claim');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center py-12 px-4 md:px-8">
      {/* Header Badge & Title */}
      <div className="text-center max-w-2xl mb-12 animate-fade-in">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold shadow-sm">
          <Activity className="w-3.5 h-3.5 text-blue-400 animate-pulse-glow" />
          <span>AI-Augmented Adjudication Engine</span>
        </div>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-white mb-4 bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-400">
          Submit OPD Claim
        </h1>
        <p className="text-sm md:text-base text-slate-400 max-w-lg mx-auto leading-relaxed">
          Provide claim details and upload medical documents. The multi-agent copilot runs checks and determines payouts in real time.
        </p>
      </div>

      {/* Main Glass Panel */}
      <div className="w-full max-w-4xl glass-card rounded-2xl overflow-hidden grid grid-cols-1 md:grid-cols-2 shadow-2xl border border-white/5 glow-blue animate-slide-in">
        {/* Left Column: Form Details */}
        <div className="p-8 border-b md:border-b-0 md:border-r border-white/5 space-y-6">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <h2 className="text-lg font-bold text-white tracking-wide">Claim Details</h2>
            <Info className="w-4 h-4 text-slate-500" />
          </div>
          
          <div className="space-y-4">
            {/* Member ID */}
            <div>
              <label htmlFor="memberId" className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-slate-400" />
                Member Employee ID
              </label>
              <input
                id="memberId"
                type="text"
                value={memberId}
                onChange={(e) => setMemberId(e.target.value)}
                className="w-full px-4.5 py-3 border border-white/10 rounded-xl bg-slate-900/60 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 placeholder-slate-600 transition-all"
                placeholder="e.g. EMP001"
                required
              />
            </div>

            {/* Claim Amount */}
            <div>
              <label htmlFor="claimAmount" className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                <span>₹</span>
                Total Claimed Amount (INR)
              </label>
              <input
                id="claimAmount"
                type="number"
                value={claimAmount}
                onChange={(e) => setClaimAmount(e.target.value)}
                className="w-full px-4.5 py-3 border border-white/10 rounded-xl bg-slate-900/60 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 placeholder-slate-600 transition-all"
                placeholder="e.g. 1500"
                min="0"
                required
              />
            </div>

            {/* Treatment Date */}
            <div>
              <label htmlFor="treatmentDate" className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                Treatment / Visit Date
              </label>
              <input
                id="treatmentDate"
                type="date"
                value={treatmentDate}
                onChange={(e) => setTreatmentDate(e.target.value)}
                className="w-full px-4.5 py-3 border border-white/10 rounded-xl bg-slate-900/60 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                required
              />
            </div>

            {/* Hospital Name */}
            <div>
              <label htmlFor="hospitalName" className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                <Landmark className="w-3.5 h-3.5 text-slate-400" />
                Hospital / Clinic Name
              </label>
              <input
                id="hospitalName"
                type="text"
                value={hospitalName}
                onChange={(e) => setHospitalName(e.target.value)}
                className="w-full px-4.5 py-3 border border-white/10 rounded-xl bg-slate-900/60 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 placeholder-slate-600 transition-all"
                placeholder="e.g. Apollo Hospitals"
              />
            </div>

            {/* Cashless Checkbox */}
            <div className="flex items-center gap-3 pt-3">
              <div className="relative flex items-center">
                <input
                  id="isCashless"
                  type="checkbox"
                  checked={isCashless}
                  onChange={(e) => setIsCashless(e.target.checked)}
                  className="w-5 h-5 border border-white/20 rounded-md bg-slate-900/60 accent-blue-600 cursor-pointer focus:ring-0 focus:ring-offset-0"
                />
              </div>
              <label htmlFor="isCashless" className="text-sm font-semibold text-slate-300 cursor-pointer select-none">
                Request cashless settlement <span className="text-xs text-slate-500 font-normal">(network hospital only)</span>
              </label>
            </div>
          </div>
        </div>

        {/* Right Column: File Drag & Drop */}
        <div className="p-8 flex flex-col justify-between bg-slate-950/20">
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h2 className="text-lg font-bold text-white tracking-wide">Upload Invoice/Prescription</h2>
              <FileText className="w-4 h-4 text-slate-500" />
            </div>
            
            {/* Drag and Drop box */}
            <div 
              className={`relative rounded-2xl border-2 border-dashed p-8 transition-all duration-350 text-center flex flex-col items-center justify-center min-h-[220px] group
                ${dragActive ? 'border-blue-500 bg-blue-500/10' : 'border-white/10 bg-slate-900/30 hover:border-white/20 hover:bg-slate-900/50'}
                ${files.length > 0 ? 'border-green-500/40 bg-green-500/5 glow-green' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                type="file"
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-15"
                onChange={handleChange}
                accept=".pdf,.png,.jpg,.jpeg"
                disabled={isSubmitting}
                multiple
              />
              
              <div className="flex flex-col items-center justify-center gap-4 w-full">
                {files.length > 0 ? (
                  <div className="w-full flex flex-col gap-2 max-w-[320px] z-20">
                    <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center text-green-400 border border-green-500/20 shadow-lg shadow-green-500/5 mx-auto mb-1">
                      <CheckCircle2 className="w-5 h-5 animate-pulse-glow" />
                    </div>
                    {files.map((f, i) => (
                      <div key={i} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-900 border border-white/5 text-xs text-slate-200 w-full hover:border-white/10">
                        <span className="truncate pr-3 max-w-[200px]">{f.name}</span>
                        <button 
                          type="button" 
                          onClick={(e) => { e.preventDefault(); e.stopPropagation(); removeFile(i); }} 
                          className="text-slate-400 hover:text-white font-bold px-2 py-0.5 rounded bg-white/5 hover:bg-white/10 transition-colors"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <>
                    <div className="w-14 h-14 rounded-full bg-white/5 flex items-center justify-center text-slate-400 border border-white/10 group-hover:text-blue-400 group-hover:border-blue-500/30 group-hover:bg-blue-500/5 transition-all">
                      <Upload className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-slate-200 group-hover:text-white transition-colors">
                        Select or drag documents here
                      </p>
                      <p className="text-xs text-slate-500 mt-1.5">
                        Supports PDF, JPG, PNG (select multiple if needed)
                      </p>
                    </div>
                  </>
                )}
              </div>
            </div>

            {error && (
              <div className="p-4 rounded-xl bg-red-500/10 text-red-400 text-xs border border-red-500/20 flex items-start gap-2.5 shadow-sm shadow-red-500/5">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-400 mt-0.5" />
                <span className="leading-relaxed font-semibold">{error}</span>
              </div>
            )}
          </div>

          <button
            onClick={onSubmit}
            disabled={files.length === 0 || isSubmitting}
            className="w-full mt-8 py-4 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2.5 shadow-lg
              disabled:opacity-50 disabled:cursor-not-allowed
              bg-blue-600 text-white hover:bg-blue-500 shadow-blue-500/10 hover:shadow-blue-500/20"
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2.5">
                <Activity className="w-4 h-4 animate-spin text-white" /> Adjudicating claim via AI multi-agents...
              </span>
            ) : (
              <>
                <span>Submit for Adjudication</span>
                <ChevronRight className="w-4.5 h-4.5" />
              </>
            )}
          </button>
        </div>
      </div>
      
      {/* Policy Helper Quick References */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-14 max-w-4xl w-full">
        {[
          { title: "Consultation Limits", desc: "Consultation fee capped at ₹1500 per visit, with a standard 10% co-pay applied dynamically.", icon: ShieldCheck },
          { title: "Cashless Discounts", desc: "Enjoy a 20% network discount applied automatically on cashless network hospital visits.", icon: Landmark },
          { title: "Exclusion Screenings", desc: "Cosmetic procedures, dental whitening, and weight loss remedies are automatically flagged and rejected.", icon: Info },
        ].map((feat, i) => {
          const Icon = feat.icon;
          return (
            <div key={i} className="p-5 rounded-2xl border border-white/5 bg-slate-900/30 backdrop-blur-md flex flex-col justify-between hover:border-white/10 hover:bg-slate-900/50 transition-all duration-300">
              <div>
                <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center mb-3">
                  <Icon className="w-4 h-4 text-blue-400" />
                </div>
                <h3 className="font-bold text-white text-sm mb-1.5">{feat.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{feat.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
