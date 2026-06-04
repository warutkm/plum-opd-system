'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, FileText, CheckCircle2, AlertCircle, ChevronRight, Activity } from 'lucide-react';
import { api } from '../../lib/api';

export default function Home() {
  const router = useRouter();
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
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
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const onSubmit = async () => {
    if (!file) {
      setError("Please upload a claim document first.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('files', file);
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
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col items-center py-12 px-4">
      {/* Header */}
      <div className="text-center max-w-2xl mb-10 mt-6">
        <div className="inline-flex items-center justify-center px-3 py-1 mb-4 rounded-full bg-slate-200 text-slate-800 text-xs font-semibold">
          <Activity className="w-3.5 h-3.5 mr-1.5 text-blue-600" />
          OPD Claims Adjudication Copilot
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-3">
          Submit OPD Claim
        </h1>
        <p className="text-sm text-slate-600">
          Fill in the claim metadata and upload your invoice or prescription. The adjudication engine will parse documents and run rule checks instantly.
        </p>
      </div>

      {/* Main Container */}
      <div className="w-full max-w-4xl bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden grid grid-cols-1 md:grid-cols-2">
        {/* Left Column: Form Details */}
        <div className="p-8 border-b md:border-b-0 md:border-r border-slate-200 space-y-5">
          <h2 className="text-lg font-bold text-slate-900 border-b pb-2">Claim Metadata</h2>
          
          <div className="space-y-4">
            {/* Member ID */}
            <div>
              <label htmlFor="memberId" className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Member Employee ID
              </label>
              <input
                id="memberId"
                type="text"
                value={memberId}
                onChange={(e) => setMemberId(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-slate-50 text-sm focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g. EMP001"
                required
              />
            </div>

            {/* Claim Amount */}
            <div>
              <label htmlFor="claimAmount" className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Total Claimed Amount (₹)
              </label>
              <input
                id="claimAmount"
                type="number"
                value={claimAmount}
                onChange={(e) => setClaimAmount(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-slate-50 text-sm focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g. 1500"
                min="0"
                required
              />
            </div>

            {/* Treatment Date */}
            <div>
              <label htmlFor="treatmentDate" className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Treatment / Visit Date
              </label>
              <input
                id="treatmentDate"
                type="date"
                value={treatmentDate}
                onChange={(e) => setTreatmentDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-slate-50 text-sm focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>

            {/* Hospital Name */}
            <div>
              <label htmlFor="hospitalName" className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Hospital / Provider Name
              </label>
              <input
                id="hospitalName"
                type="text"
                value={hospitalName}
                onChange={(e) => setHospitalName(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-slate-50 text-sm focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g. Apollo Hospitals"
              />
            </div>

            {/* Cashless Checkbox */}
            <div className="flex items-center gap-2 pt-2">
              <input
                id="isCashless"
                type="checkbox"
                checked={isCashless}
                onChange={(e) => setIsCashless(e.target.checked)}
                className="w-4 h-4 border border-slate-300 rounded accent-blue-600 cursor-pointer"
              />
              <label htmlFor="isCashless" className="text-sm font-medium text-slate-700 cursor-pointer">
                Request cashless settlement (network hospital only)
              </label>
            </div>
          </div>
        </div>

        {/* Right Column: File Drag & Drop */}
        <div className="p-8 flex flex-col justify-between bg-slate-50/50">
          <div className="space-y-5">
            <h2 className="text-lg font-bold text-slate-900 border-b pb-2">Medical Documents</h2>
            
            {/* Drag and Drop box */}
            <div 
              className={`relative rounded-xl border-2 border-dashed p-8 transition-all text-center flex flex-col items-center justify-center min-h-[200px]
                ${dragActive ? 'border-blue-500 bg-blue-50/50' : 'border-slate-300 bg-white hover:border-slate-400'}
                ${file ? 'border-green-500/50 bg-green-50/30' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                type="file"
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                onChange={handleChange}
                accept=".pdf,.png,.jpg,.jpeg"
                disabled={isSubmitting}
              />
              
              <div className="flex flex-col items-center justify-center gap-3">
                {file ? (
                  <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center text-green-700 mb-1 border border-green-200">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                ) : (
                  <div className="w-12 h-12 rounded-full flex items-center justify-center mb-1 bg-slate-100 text-slate-400 border border-slate-200">
                    <Upload className="w-6 h-6" />
                  </div>
                )}
                
                <div>
                  <p className="text-sm font-semibold text-slate-800">
                    {file ? file.name : 'Select or drag document here'}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : 'Supports PDF, JPG, PNG up to 10MB'}
                  </p>
                </div>
              </div>
            </div>

            {error && (
              <div className="p-3.5 rounded-lg bg-red-50 text-red-700 text-xs border border-red-200 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-500" /> {error}
              </div>
            )}
          </div>

          <button
            onClick={onSubmit}
            disabled={!file || isSubmitting}
            className="w-full mt-6 py-3.5 rounded-lg font-semibold text-sm transition-all flex items-center justify-center gap-2
              disabled:opacity-50 disabled:cursor-not-allowed
              bg-blue-600 text-white hover:bg-blue-700 shadow-sm"
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2">
                <Activity className="w-4 h-4 animate-spin" /> Adjudicating Claim...
              </span>
            ) : (
              <>Submit for Adjudication <ChevronRight className="w-4 h-4" /></>
            )}
          </button>
        </div>
      </div>
      
      {/* Policy Helper Quick References */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-12 max-w-4xl w-full">
        {[
          { title: "Consultation limit", desc: "Capped at ₹1500 with a standard 10% co-pay." },
          { title: "Cashless discount", desc: "20% network discount applied automatically on cashless network hospital visits." },
          { title: "Excluded items", desc: "Cosmetic procedures, dental whitening, and weight loss are strictly excluded." },
        ].map((feat, i) => (
          <div key={i} className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm flex flex-col justify-between">
            <h3 className="font-semibold text-slate-800 text-sm mb-1">{feat.title}</h3>
            <p className="text-xs text-slate-500 leading-relaxed">{feat.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

