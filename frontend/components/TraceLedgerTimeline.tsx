'use client';

import React from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Clock, PlayCircle } from 'lucide-react';
import { TraceEntry } from '../lib/api';

const statusConfig = {
  PASS: { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-500/15', border: 'border-green-500/25' },
  FAIL: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-500/15', border: 'border-red-500/25' },
  WARNING: { icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-500/15', border: 'border-amber-500/25' },
  SKIP: { icon: PlayCircle, color: 'text-slate-400', bg: 'bg-slate-900/60', border: 'border-white/10' },
  ERROR: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-500/15', border: 'border-red-500/25' },
  PENDING: { icon: Clock, color: 'text-blue-400 animate-pulse', bg: 'bg-blue-500/15', border: 'border-blue-500/25' },
};

const formatStepName = (step: string) => {
  return step.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
};

export default function TraceLedgerTimeline({ traces }: { traces: TraceEntry[] }) {
  if (!traces || traces.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-slate-500 bg-slate-950/40 border border-white/5 rounded-2xl shadow-inner">
        <Clock className="w-8 h-8 mb-4 opacity-40 animate-pulse" />
        <p className="text-xs font-semibold">No audit traces found for this claim.</p>
      </div>
    );
  }

  return (
    <div className="relative space-y-5 before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-white/10">
      {traces.map((trace, index) => {
        const config = statusConfig[trace.status] || statusConfig.PENDING;
        const Icon = config.icon;
        
        return (
          <div key={index} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group animate-slide-in">
            {/* Icon */}
            <div className={`flex items-center justify-center w-10 h-10 rounded-full border ${config.bg} ${config.border} ${config.color} shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow-lg shadow-black/40 z-10 bg-slate-950`}>
              <Icon className="w-4 h-4" />
            </div>
            
            {/* Card */}
            <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-5 rounded-2xl border border-white/5 bg-slate-900/40 backdrop-blur-md shadow-lg hover:border-white/15 transition-all">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-bold text-white text-xs tracking-wider">{formatStepName(trace.step)}</h4>
                <span className={`text-[9px] font-extrabold px-2 py-0.5 rounded border ${config.bg} ${config.color} ${config.border} tracking-wide`}>
                  {trace.status}
                </span>
              </div>
              
              {trace.details && Object.keys(trace.details).length > 0 && (
                <div className="mt-3.5 p-3.5 bg-slate-950/80 rounded-xl text-[10px] font-mono text-slate-300 overflow-x-auto border border-white/5 leading-relaxed scrollbar-thin">
                  {Object.entries(trace.details).map(([key, val]) => (
                    <div key={key} className="flex flex-col sm:flex-row sm:gap-2.5 mb-1.5 last:mb-0">
                      <span className="font-bold text-blue-400 shrink-0">{key}:</span>
                      <span className="truncate">{typeof val === 'object' ? JSON.stringify(val) : String(val)}</span>
                    </div>
                  ))}
                </div>
              )}
              
              {trace.duration_ms !== undefined && (
                <div className="mt-3.5 text-[10px] text-slate-500 flex items-center gap-1.5 font-bold font-mono">
                  <Clock className="w-3.5 h-3.5 text-slate-500" />
                  PROCESSED IN {trace.duration_ms}MS
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
