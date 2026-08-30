import React from 'react';
import { TrendingDown, Zap, Clock, ShieldCheck, Award, FlaskConical, Timer } from 'lucide-react';

const DEFAULT_TOTALS = {
  traditional_human_minutes: 100,
  changeflow_automated_total_seconds: 0,
  changeflow_human_minutes: 8,
  effort_saved_minutes: 0,
  effort_saved_percentage: 0,
  speedup_factor: "0x"
};

const DEFAULT_ESTIMATED = {
  manual_baseline_minutes: 100,
  human_review_minutes: 8,
  effort_saved_minutes: 0,
  effort_saved_percentage: 0,
  speedup_factor: "0x"
};

const DEFAULT_MEASURED = {
  pipeline_wall_clock_seconds: 0,
  automation_total_seconds: 0,
  coverage_percentage: 0,
  readiness_score: 0
};

export default function MetricsBadge({ benchmarkData, live }) {
  const data = benchmarkData || { workflow_comparison: [], totals: DEFAULT_TOTALS };
  const totals = data.totals || DEFAULT_TOTALS;
  const estimated = data.estimated || DEFAULT_ESTIMATED;
  const measured = data.measured || DEFAULT_MEASURED;
  const liveInfo = live || {};

  const EstCard = ({ children }) => (
    <div className="relative rounded-xl p-5 border-2 border-dashed border-blue-500/50 bg-blue-950/10">
      <span className="absolute top-2 right-2 text-[9px] font-black bg-blue-500/30 text-blue-200 px-1.5 py-0.5 rounded uppercase tracking-wider">
        Estimativa
      </span>
      {children}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Measured vs Estimated real-data strip */}
      <div className="glow-card rounded-xl p-4 bg-zinc-950/60 border-l-4 border-emerald-500">
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <div className="space-y-1">
            <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
              <Timer className="w-4 h-4" /> Dados reais (medidos) x Estimativas (baseline de referência)
            </h4>
            <p className="text-xs text-zinc-400">
              <strong className="text-emerald-300">REAIS, medidos nesta execução:</strong> pipeline{' '}
              <strong className="font-mono text-emerald-300">{measured.pipeline_wall_clock_seconds}s</strong> · automação{' '}
              <strong className="font-mono">{measured.automation_total_seconds}s</strong> ·{' '}
              <strong className="font-mono">{measured.tests?.tests_passed}/{measured.tests?.tests_executed}</strong> testes ·{' '}
              <strong className="font-mono">{measured.coverage_percentage}%</strong> cobertura · review{' '}
              <strong className="font-mono">{measured.reviewer_score}/100</strong> · readiness{' '}
              <strong className="font-mono">{measured.readiness_score}</strong>.
            </p>
            <p className="text-xs text-blue-300/80">
              <strong className="text-blue-300">ESTIMATIVAS (baseline de referência, NÃO medidos):</strong>{' '}
              -{estimated.effort_saved_percentage}% de redução e {estimated.speedup_factor} assumem {estimated.manual_baseline_minutes} min manuais →
              {estimated.human_review_minutes} min de revisão humana do benchmark. Apenas o tempo de automação é real.
            </p>
          </div>
        </div>
      </div>

      {/* High-Level Impact Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <EstCard>
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Human Effort Reduction</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-4xl font-extrabold text-white tracking-tight">-{estimated.effort_saved_percentage}%</span>
              </div>
              <p className="text-xs text-zinc-400 mt-2">
                {estimated.manual_baseline_minutes} min manual → {estimated.human_review_minutes} min revisão (baseline)
              </p>
            </div>
            <div className="p-3 bg-blue-500/10 rounded-xl text-blue-400"><Zap className="w-6 h-6" /></div>
          </div>
        </EstCard>

        <EstCard>
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Speedup Multiplier</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-4xl font-extrabold text-blue-300 tracking-tight">{estimated.speedup_factor}</span>
              </div>
              <p className="text-xs text-zinc-400 mt-2">
                automação real medida: <strong className="text-emerald-400">{measured.automation_total_seconds}s</strong> (pipeline {measured.pipeline_wall_clock_seconds}s)
              </p>
            </div>
            <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-400"><Clock className="w-6 h-6" /></div>
          </div>
        </EstCard>

        <EstCard>
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Time Saved / PR</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-4xl font-extrabold text-indigo-300 tracking-tight">{estimated.effort_saved_minutes} min</span>
              </div>
              <p className="text-xs text-zinc-400 mt-2">~{(estimated.effort_saved_minutes / 60).toFixed(1)}h/change (vs baseline)</p>
            </div>
            <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-400"><Award className="w-6 h-6" /></div>
          </div>
        </EstCard>

        <div className="relative glow-card rounded-xl p-5 border-2 border-emerald-500/60 bg-emerald-950/10">
          <span className="absolute top-2 right-2 text-[9px] font-black bg-emerald-500/30 text-emerald-200 px-1.5 py-0.5 rounded uppercase tracking-wider">
            Medido
          </span>
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Quality Gate (medido)</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-4xl font-extrabold text-amber-300 tracking-tight">{liveInfo.readiness ?? measured.readiness_score ?? '--'}</span>
              </div>
              <p className="text-xs text-zinc-400 mt-2">
                <strong className="text-amber-300">{liveInfo.coverage ?? measured.coverage_percentage}%</strong> cobertura ·{' '}
                <strong className="text-emerald-400">{liveInfo.testsPassed ?? measured.tests?.tests_passed ?? '-'}/{liveInfo.testsTotal ?? measured.tests?.tests_executed ?? '-'}</strong> testes · reviewer{' '}
                {measured.reviewer_score}/100 · docs {measured.docs_synced ?? 0}
              </p>
            </div>
            <div className="p-3 bg-amber-500/10 rounded-xl text-amber-400"><ShieldCheck className="w-6 h-6" /></div>
          </div>
        </div>
      </div>

      {/* Visual Comparison Bar */}
      <div className="glow-card rounded-xl p-6">
        <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
          <span>Workflow Execution Comparison: Manual (referência) vs ChangeFlow (medido)</span>
        </h3>
        <p className="text-sm text-zinc-400 mb-6">
          O tempo manual é a referência do benchmark; o tempo de automação é cronometrado nesta execução.
        </p>

        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-xs font-semibold text-zinc-300 mb-1">
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-sm bg-rose-500/80 inline-block"></span>
                Traditional Manual Process (baseline de referência)
              </span>
              <span className="text-rose-400 font-mono">{totals.traditional_human_minutes} Minutes</span>
            </div>
            <div className="w-full h-8 bg-zinc-800 rounded-lg overflow-hidden flex p-1">
              <div className="h-full bg-gradient-to-r from-rose-600 to-rose-400 rounded text-[10px] font-bold text-white flex items-center justify-center" style={{ width: '100%' }}>
                {totals.traditional_human_minutes} min (referência, não medido)
              </div>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs font-semibold text-zinc-300 mb-1">
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-sm bg-blue-500 inline-block"></span>
                ChangeFlow (automação medida + revisão humana)
              </span>
              <span className="text-emerald-400 font-mono">{totals.changeflow_human_minutes} min revisão (est.) + {totals.changeflow_automated_total_seconds}s (medido)</span>
            </div>
            <div className="w-full h-8 bg-zinc-800 rounded-lg overflow-hidden flex p-1">
              <div style={{ width: `${Math.min(100, (totals.changeflow_human_minutes / totals.traditional_human_minutes) * 100)}%` }}
                   className="h-full bg-gradient-to-r from-blue-600 via-indigo-500 to-emerald-400 rounded text-[10px] font-bold text-white flex items-center justify-center">
                {totals.changeflow_human_minutes}m (est.)
              </div>
              <div className="h-full flex items-center px-3 text-xs text-emerald-400 font-medium">
                ⚡ {totals.changeflow_automated_total_seconds}s de automação real
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Granular Step-by-Step Table */}
      <div className="glow-card rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-800 flex justify-between items-center">
          <h4 className="font-semibold text-white text-sm">Granular Breakdown by Stage</h4>
          <span className="text-xs bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full font-mono">tempos de automação medidos nesta execução</span>
        </div>
        {data.workflow_comparison.length === 0 ? (
          <p className="px-6 py-8 text-sm text-zinc-400">Rode o pipeline para ver o breakdown real por estágio.</p>
        ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-zinc-300">
            <thead className="bg-zinc-900/70 text-xs uppercase font-semibold text-zinc-400">
              <tr>
                <th className="px-6 py-3">Workflow Step</th>
                <th className="px-6 py-3">Manual (referência)</th>
                <th className="px-6 py-3">ChangeFlow (medido)</th>
                <th className="px-6 py-3">Automation Persona</th>
                <th className="px-6 py-3 text-right">Automação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 font-mono text-xs">
              {data.workflow_comparison.map((row, idx) => (
                <tr key={idx} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-6 py-3.5 font-sans font-medium text-white flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                    {row.step}
                  </td>
                  <td className="px-6 py-3.5 text-zinc-400">{row.traditional_manual_minutes} min <span className="text-zinc-600">(ref.)</span></td>
                  <td className="px-6 py-3.5 text-emerald-400">
                    {row.changeflow_human_minutes > 0
                      ? <> {row.changeflow_human_minutes} min <span className="text-zinc-500">(est.)</span> </>
                      : <> {row.changeflow_automated_seconds}s <span className="text-zinc-500">(medido)</span> </>}
                  </td>
                  <td className="px-6 py-3.5 font-sans text-zinc-300">{row.automation_type}</td>
                  <td className="px-6 py-3.5 text-right">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${row.effort_reduction_percentage === 100 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>
                      {row.effort_reduction_percentage === 100 ? '100% Autonomous' : `-${100 - row.effort_reduction_percentage}%`}
                    </span>
                  </td>
                </tr>
              ))}
              <tr className="bg-zinc-900/90 font-bold font-sans text-sm text-white">
                <td className="px-6 py-4">Total</td>
                <td className="px-6 py-4 text-rose-400 font-mono">{totals.traditional_human_minutes} min <span className="text-zinc-500 font-normal text-xs">(est.)</span></td>
                <td className="px-6 py-4 text-emerald-400 font-mono">{totals.changeflow_human_minutes} min <span className="text-zinc-500 font-normal text-xs">(est.)</span> + {totals.changeflow_automated_total_seconds}s <span className="text-zinc-500 font-normal text-xs">(medido)</span></td>
                <td className="px-6 py-4 text-zinc-300 font-normal">Redução estimada (baseline)</td>
                <td className="px-6 py-4 text-right text-emerald-400 font-mono text-base">-{estimated.effort_saved_percentage}% <span className="text-zinc-500 font-normal text-xs">est.</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        )}
      </div>
    </div>
  );
}