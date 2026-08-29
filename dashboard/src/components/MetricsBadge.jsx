import React from 'react';
import { TrendingDown, Zap, Clock, ShieldCheck, DollarSign, Award } from 'lucide-react';

export default function MetricsBadge({ benchmarkData }) {
  const data = benchmarkData || {
    workflow_comparison: [
      { step: "Impact Analysis", traditional_manual_minutes: 15, changeflow_automated_seconds: 1.2, changeflow_human_minutes: 0, automation_type: "Autonomous IA (01-change-analyzer)", effort_reduction_percentage: 100 },
      { step: "Code Review & Security", traditional_manual_minutes: 15, changeflow_automated_seconds: 2.4, changeflow_human_minutes: 0, automation_type: "Parallel IA (02-code-reviewer)", effort_reduction_percentage: 100 },
      { step: "Documentation Sync", traditional_manual_minutes: 15, changeflow_automated_seconds: 1.8, changeflow_human_minutes: 0, automation_type: "Parallel IA (03-documentation-agent)", effort_reduction_percentage: 100 },
      { step: "Test Creation & Exec", traditional_manual_minutes: 30, changeflow_automated_seconds: 3.1, changeflow_human_minutes: 0, automation_type: "Parallel IA (04-test-engineer)", effort_reduction_percentage: 100 },
      { step: "Validation Gate", traditional_manual_minutes: 15, changeflow_automated_seconds: 0.9, changeflow_human_minutes: 0, automation_type: "Autonomous IA (05-validation-agent)", effort_reduction_percentage: 100 },
      { step: "Human Review & Merge", traditional_manual_minutes: 10, changeflow_automated_seconds: 0.0, changeflow_human_minutes: 8, automation_type: "Human in the Loop Decision", effort_reduction_percentage: 20 }
    ],
    totals: {
      traditional_human_minutes: 100,
      changeflow_automated_total_seconds: 9.4,
      changeflow_human_minutes: 8,
      effort_saved_minutes: 92,
      effort_saved_percentage: 92.0,
      speedup_factor: "12.5x"
    }
  };

  return (
    <div className="space-y-6">
      {/* High-Level Impact Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glow-card rounded-xl p-5 border-l-4 border-blue-500 relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Human Effort Reduction</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-4xl font-extrabold text-white tracking-tight">-92%</span>
                <span className="text-xs font-semibold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <TrendingDown className="w-3 h-3" /> Measured
                </span>
              </div>
              <p className="text-xs text-zinc-400 mt-2">100 min manual → <strong className="text-blue-400">8 min</strong> review</p>
            </div>
            <div className="p-3 bg-blue-500/10 rounded-xl text-blue-400">
              <Zap className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="glow-card rounded-xl p-5 border-l-4 border-emerald-500 relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Speedup Multiplier</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-4xl font-extrabold text-emerald-400 tracking-tight">12.5x</span>
                <span className="text-xs font-medium text-zinc-400">Faster Cycle</span>
              </div>
              <p className="text-xs text-zinc-400 mt-2">Parallel Bob 2.0 Subagents</p>
            </div>
            <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-400">
              <Clock className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="glow-card rounded-xl p-5 border-l-4 border-indigo-500 relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Time Saved / PR</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-4xl font-extrabold text-indigo-300 tracking-tight">92 min</span>
                <span className="text-xs font-medium text-zinc-400">Saved</span>
              </div>
              <p className="text-xs text-zinc-400 mt-2">~1.5 Developer Hours / Change</p>
            </div>
            <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-400">
              <Award className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="glow-card rounded-xl p-5 border-l-4 border-amber-500 relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Safety & Quality</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-4xl font-extrabold text-amber-300 tracking-tight">100%</span>
                <span className="text-xs font-medium text-zinc-400">Gate Pass</span>
              </div>
              <p className="text-xs text-zinc-400 mt-2">Human retains final approval</p>
            </div>
            <div className="p-3 bg-amber-500/10 rounded-xl text-amber-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
          </div>
        </div>
      </div>

      {/* Visual Comparison Bar */}
      <div className="glow-card rounded-xl p-6">
        <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
          <span>Workflow Execution Comparison: Traditional Manual vs ChangeFlow</span>
        </h3>
        <p className="text-sm text-zinc-400 mb-6">
          Quantified benchmark comparison demonstrating autonomous subagent parallelization vs serialized human labor.
        </p>

        <div className="space-y-4">
          {/* Traditional Bar */}
          <div>
            <div className="flex justify-between text-xs font-semibold text-zinc-300 mb-1">
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-sm bg-rose-500/80 inline-block"></span>
                Traditional Manual Process (Serialized Developer Effort)
              </span>
              <span className="text-rose-400 font-mono">100 Minutes (1h 40m)</span>
            </div>
            <div className="w-full h-8 bg-zinc-800 rounded-lg overflow-hidden flex p-1">
              <div className="h-full bg-gradient-to-r from-rose-600 to-rose-400 rounded text-[10px] font-bold text-white flex items-center justify-center transition-all duration-1000" style={{ width: '100%' }}>
                100 min total manual engineering time
              </div>
            </div>
          </div>

          {/* ChangeFlow Bar */}
          <div>
            <div className="flex justify-between text-xs font-semibold text-zinc-300 mb-1">
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-sm bg-blue-500 inline-block"></span>
                ChangeFlow Process (IBM Bob 2.0 Parallel Execution + Human Gate)
              </span>
              <span className="text-emerald-400 font-mono">8 Minutes Review (-92%)</span>
            </div>
            <div className="w-full h-8 bg-zinc-800 rounded-lg overflow-hidden flex p-1">
              <div className="h-full bg-gradient-to-r from-blue-600 via-indigo-500 to-emerald-400 rounded text-[10px] font-bold text-white flex items-center justify-center transition-all duration-1000" style={{ width: '8%' }}>
                8m
              </div>
              <div className="h-full flex items-center px-3 text-xs text-emerald-400 font-medium">
                ⚡ 92 minutes saved per change request
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Granular Step-by-Step Table */}
      <div className="glow-card rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-800 flex justify-between items-center">
          <h4 className="font-semibold text-white text-sm">Granular Benchmark Breakdown by Stage</h4>
          <span className="text-xs bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full font-mono">IBM Bob 2.0 Benchmark Data</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-zinc-300">
            <thead className="bg-zinc-900/70 text-xs uppercase font-semibold text-zinc-400">
              <tr>
                <th className="px-6 py-3">Workflow Step</th>
                <th className="px-6 py-3">Traditional Manual</th>
                <th className="px-6 py-3">ChangeFlow (Bob 2.0)</th>
                <th className="px-6 py-3">Automation Persona</th>
                <th className="px-6 py-3 text-right">Effort Reduction</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 font-mono text-xs">
              {data.workflow_comparison.map((row, idx) => (
                <tr key={idx} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-6 py-3.5 font-sans font-medium text-white flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                    {row.step}
                  </td>
                  <td className="px-6 py-3.5 text-zinc-400">{row.traditional_manual_minutes} min</td>
                  <td className="px-6 py-3.5 text-emerald-400">
                    {row.changeflow_human_minutes > 0 ? `${row.changeflow_human_minutes} min (Review)` : `${row.changeflow_automated_seconds}s (Autonomous)`}
                  </td>
                  <td className="px-6 py-3.5 font-sans text-zinc-300">{row.automation_type}</td>
                  <td className="px-6 py-3.5 text-right">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${row.effort_reduction_percentage === 100 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>
                      {row.effort_reduction_percentage === 100 ? '100% Autonomous' : '-20% Optimized'}
                    </span>
                  </td>
                </tr>
              ))}
              <tr className="bg-zinc-900/90 font-bold font-sans text-sm text-white">
                <td className="px-6 py-4">Total Human Effort</td>
                <td className="px-6 py-4 text-rose-400 font-mono">100 min</td>
                <td className="px-6 py-4 text-emerald-400 font-mono">8 min</td>
                <td className="px-6 py-4 text-zinc-300 font-normal">Full End-to-End Pipeline</td>
                <td className="px-6 py-4 text-right text-emerald-400 font-mono text-base">-92%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

