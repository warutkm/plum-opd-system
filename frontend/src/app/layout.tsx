'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Plus_Jakarta_Sans } from 'next/font/google';
import { FileText, LayoutDashboard, Sparkles } from 'lucide-react';
import './globals.css';

const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  display: 'swap',
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname();

  return (
    <html lang="en" className="dark">
      <body className={`${jakarta.className} antialiased min-h-screen text-slate-100`}>
        {/* Navigation Bar */}
        <nav className="fixed top-0 left-0 right-0 h-16 border-b border-white/5 bg-[#090d16]/70 backdrop-blur-xl z-50 flex items-center px-6 md:px-12 justify-between">
          <div className="flex items-center gap-3 font-extrabold text-lg text-white tracking-tight">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-650 flex items-center justify-center text-white text-base shadow-lg shadow-blue-500/25 border border-white/10">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-350">
              Plum Adjudication <span className="text-blue-500 text-xs font-semibold px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 ml-1">CO-PILOT</span>
            </span>
          </div>
          
          <div className="flex gap-1 md:gap-4 text-sm font-semibold">
            <Link 
              href="/" 
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 ${pathname === '/' ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-sm shadow-blue-500/5' : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'}`}
            >
              <FileText className="w-4 h-4" />
              <span>Submit Claim</span>
            </Link>
            <Link 
              href="/dashboard" 
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 ${pathname === '/dashboard' ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-sm shadow-blue-500/5' : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'}`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </Link>
          </div>
        </nav>
        
        <main className="pt-16 min-h-screen">
          {children}
        </main>
      </body>
    </html>
  );
}
