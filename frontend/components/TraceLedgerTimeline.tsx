'use client';

import React from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Clock, PlayCircle } from 'lucide-react';
import { TraceEntry } from '../lib/api';

const statusConfig = {
  PASS: { icon: CheckCircle2, color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200' },
  FAIL: { icon: AlertCircle, color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200' },
  WARNING: { icon: AlertTriangle, color: 'text-amber-750', bg: 'bg-amber-50', border: 'border-amber-200' },
  SKIP: { icon: PlayCircle, color: 'text-slate-400', bg: 'bg-slate-50', border: 'border-slate-200' },
  ERROR: { icon: AlertCircle, color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200' },
  PENDING: { icon: Clock, color: 'text-blue-600 animate-pulse', bg: 'bg-blue-50', border: 'border-blue-200' },
};

const formatStepName = (step: string) => {
  return step.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
};

export default function TraceLedgerTimeline({ traces }: { traces: TraceEntry[] }) {
  if (!traces || traces.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-slate-400 bg-white border border-slate-200 rounded-lg shadow-sm">
        <Clock className="w-8 h-8 mb-4 opacity-50" />
        <p>No trace ledger data available yet.</p>
      </div>
    );
  }

  return (
    <div className="relative space-y-4 before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-slate-200">
      {traces.map((trace, index) => {
        const config = statusConfig[trace.status] || statusConfig.PENDING;
        const Icon = config.icon;
        
        return (
          <div key={index} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
            {/* Icon */}
            <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${config.bg} ${config.border} ${config.color} shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow-sm z-10 bg-white`}>
              <Icon className="w-4 h-4" />
            </div>
            
            {/* Card */}
            <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-xl border border-slate-200 bg-white shadow-sm transition-all hover:shadow-md">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-bold text-slate-800 text-sm tracking-tight">{formatStepName(trace.step)}</h4>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${config.bg} ${config.color} ${config.border}`}>
                  {trace.status}
                </span>
              </div>
              
              {trace.details && Object.keys(trace.details).length > 0 && (
                <div className="mt-3 p-3 bg-slate-50 rounded-lg text-xs font-mono text-slate-655 overflow-x-auto border border-slate-200">
                  {Object.entries(trace.details).map(([key, val]) => (
                    <div key={key} className="flex flex-col sm:flex-row sm:gap-2 mb-1 last:mb-0">
                      <span className="font-semibold text-slate-700">{key}:</span>
                      <span className="truncate">{typeof val === 'object' ? JSON.stringify(val) : String(val)}</span>
                    </div>
                  ))}
                </div>
              )}
              
              {trace.duration_ms !== undefined && (
                <div className="mt-3 text-[11px] text-slate-400 flex items-center gap-1.5 font-medium">
                  <Clock className="w-3.5 h-3.5" />
                  Processed in {trace.duration_ms}ms
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
