'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname();

  return (
    <html lang="en">
      <body className="antialiased font-sans bg-slate-50 text-slate-900">
        {/* Navigation Bar */}
        <nav className="fixed top-0 left-0 right-0 h-16 border-b border-slate-200 bg-white/90 backdrop-blur-md z-50 flex items-center px-6">
          <div className="flex items-center gap-2 font-bold text-lg text-slate-800 tracking-tight">
            <div className="w-6 h-6 rounded-md bg-blue-600 flex items-center justify-center text-white text-sm">P</div>
            Plum OPD
          </div>
          <div className="ml-auto flex gap-6 text-sm font-medium">
            <Link 
              href="/" 
              className={`transition-colors duration-150 ${pathname === '/' ? 'text-blue-600 font-semibold' : 'text-slate-500 hover:text-slate-800'}`}
            >
              Submit Claim
            </Link>
            <Link 
              href="/dashboard" 
              className={`transition-colors duration-150 ${pathname === '/dashboard' ? 'text-blue-600 font-semibold' : 'text-slate-500 hover:text-slate-800'}`}
            >
              Adjuster Dashboard
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

