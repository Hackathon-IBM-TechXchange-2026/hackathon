import React, { useState } from 'react';
import { ShieldCheck, Check, GitMerge, AlertCircle, X, Sparkles, UserCheck } from 'lucide-react';

export default function HumanApprovalModal({ isOpen, onClose, onApprove, isApproved }) {
  const [comments, setComments] = useState('');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="glow-card max-w-xl w-full rounded-2xl p-6 border border-zinc-700 space-y-6 shadow-2xl relative">
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-400 hover:text-white p-1 rounded-lg bg-zinc-800/60"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3">
          <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
            <ShieldCheck className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Quality Gatekeeper Release Sign-off</h3>
            <p className="text-xs text-zinc-400">Agent 05 validation passed • Human-In-The-Loop Final Merge Gate</p>
          </div>
        </div>

        {/* Verification Checklist */}
        <div className="space-y-2 bg-zinc-900/70 p-4 rounded-xl border border-zinc-800 text-xs">
          <div className="text-zinc-400 font-semibold uppercase text-[11px] mb-2">Automated Gates Verified:</div>
          <div className="flex items-center justify-between text-zinc-300">
            <span className="flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-400" /> 01 - Change Impact & Dependency Map
            </span>
            <span className="text-emerald-400 font-mono font-semibold">PASSED</span>
          </div>
          <div className="flex items-center justify-between text-zinc-300">
            <span className="flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-400" /> 02 - Code Review & Security Audit (0 Critical)
            </span>
            <span className="text-emerald-400 font-mono font-semibold">PASSED</span>
          </div>
          <div className="flex items-center justify-between text-zinc-300">
            <span className="flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-400" /> 03 - API & Architecture Docs Synchronized
            </span>
            <span className="text-emerald-400 font-mono font-semibold">SYNCED</span>
          </div>
          <div className="flex items-center justify-between text-zinc-300">
            <span className="flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-400" /> 04 - Test Suites (13/13 passing, 98.5% coverage)
            </span>
            <span className="text-emerald-400 font-mono font-semibold">PASSED</span>
          </div>
        </div>

        {/* Human Feedback Note */}
        <div>
          <label className="block text-xs font-semibold text-zinc-300 mb-1.5">
            Developer Approval Notes (Optional)
          </label>
          <textarea
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            placeholder="e.g. Verified PIX business logic and fee parameters. Approved for production deployment."
            rows={2}
            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-3 text-xs text-zinc-200 focus:outline-none focus:border-blue-500 font-sans resize-none"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-white bg-zinc-800/80 hover:bg-zinc-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onApprove(comments);
              onClose();
            }}
            disabled={isApproved}
            className={`px-5 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all shadow-lg ${
              isApproved 
                ? 'bg-emerald-600/50 text-emerald-200 cursor-not-allowed'
                : 'bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white glow-green'
            }`}
          >
            {isApproved ? (
              <>
                <UserCheck className="w-4 h-4" /> Change Approved & Merged
              </>
            ) : (
              <>
                <GitMerge className="w-4 h-4" /> Confirm Human Sign-off & Merge
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

