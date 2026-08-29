import React from 'react';
import { AlertTriangle, CheckCircle2, FileCode, Network, Server, FileText, FlaskConical, Layers } from 'lucide-react';

export default function ImpactViewer({ impactData }) {
  const data = impactData || {
    files_changed: 2,
    total_additions: 6,
    total_deletions: 1,
    risk_level: "HIGH",
    blast_radius_score: 85.0,
    impacted_components: [
      "sample-app/src/repository/payment.repository.ts",
      "sample-app/src/services/payment.service.ts"
    ],
    affected_apis: [
      {
        endpoint: "POST /api/v1/payments",
        method: "POST",
        reason: "Payment core processing logic or repository modified"
      }
    ],
    affected_tests: [
      "sample-app/tests/unit/payment.service.test.ts",
      "sample-app/tests/integration/payment.flow.test.ts"
    ],
    affected_docs: [
      "sample-app/docs/API.md",
      "sample-app/docs/ARCHITECTURE.md"
    ],
    summary: "Change affects 2 files (6 additions, 1 deletions). Risk assessed as HIGH with blast radius 85.0/100."
  };

  const getRiskColor = (level) => {
    switch (level?.toUpperCase()) {
      case 'HIGH': return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      case 'MEDIUM': return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'LOW': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      default: return 'bg-zinc-800 text-zinc-300 border-zinc-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Blast Radius & Risk Assessment */}
      <div className="glow-card rounded-xl p-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-6 border-b border-zinc-800">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <Network className="w-5 h-5 text-blue-400" />
                Change Impact & Dependency Graph
              </h3>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${getRiskColor(data.risk_level)}`}>
                {data.risk_level} RISK
              </span>
            </div>
            <p className="text-sm text-zinc-400">{data.summary}</p>
          </div>

          <div className="flex items-center gap-6 bg-zinc-900/80 px-5 py-3 rounded-xl border border-zinc-800">
            <div>
              <div className="text-[11px] text-zinc-400 uppercase font-semibold">Blast Radius</div>
              <div className="text-2xl font-black text-amber-400 font-mono">{data.blast_radius_score} <span className="text-xs text-zinc-500">/ 100</span></div>
            </div>
            <div className="w-px h-8 bg-zinc-800"></div>
            <div>
              <div className="text-[11px] text-zinc-400 uppercase font-semibold">Diff Delta</div>
              <div className="text-sm font-mono font-bold mt-1">
                <span className="text-emerald-400">+{data.total_additions}</span>
                <span className="text-zinc-500 mx-1">/</span>
                <span className="text-rose-400">-{data.total_deletions}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Multi-tier Dependency Mapping */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
          {/* Tier 1: Modified Source Code */}
          <div className="bg-zinc-900/50 rounded-xl p-4 border border-zinc-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-400 flex items-center gap-1.5">
                <FileCode className="w-4 h-4" /> Modified Code
              </span>
              <span className="text-xs bg-blue-500/20 text-blue-300 font-mono px-2 py-0.5 rounded">
                {data.impacted_components?.length || 0} files
              </span>
            </div>
            <div className="space-y-2">
              {data.impacted_components?.map((item, idx) => (
                <div key={idx} className="p-2.5 rounded-lg bg-zinc-800/60 border border-zinc-700/40 text-xs font-mono text-zinc-300 break-all hover:border-blue-500/50 transition-colors">
                  {item.split('/').pop()}
                  <div className="text-[10px] text-zinc-500 mt-0.5 truncate">{item}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Tier 2: Affected APIs */}
          <div className="bg-zinc-900/50 rounded-xl p-4 border border-zinc-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                <Server className="w-4 h-4" /> Affected Endpoints
              </span>
              <span className="text-xs bg-amber-500/20 text-amber-300 font-mono px-2 py-0.5 rounded">
                {data.affected_apis?.length || 0} APIs
              </span>
            </div>
            <div className="space-y-2">
              {data.affected_apis?.map((api, idx) => (
                <div key={idx} className="p-2.5 rounded-lg bg-zinc-800/60 border border-zinc-700/40 text-xs space-y-1 hover:border-amber-500/50 transition-colors">
                  <div className="font-mono font-bold text-amber-300 flex items-center gap-1">
                    <span className="bg-amber-500/20 text-[10px] px-1.5 py-0.5 rounded text-amber-300">{api.method || 'POST'}</span>
                    {api.endpoint || api}
                  </div>
                  {api.reason && <p className="text-[11px] text-zinc-400">{api.reason}</p>}
                </div>
              ))}
            </div>
          </div>

          {/* Tier 3: Affected Test Suites */}
          <div className="bg-zinc-900/50 rounded-xl p-4 border border-zinc-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <FlaskConical className="w-4 h-4" /> Target Test Suites
              </span>
              <span className="text-xs bg-emerald-500/20 text-emerald-300 font-mono px-2 py-0.5 rounded">
                {data.affected_tests?.length || 0} suites
              </span>
            </div>
            <div className="space-y-2">
              {data.affected_tests?.map((test, idx) => (
                <div key={idx} className="p-2.5 rounded-lg bg-zinc-800/60 border border-zinc-700/40 text-xs font-mono text-zinc-300 break-all hover:border-emerald-500/50 transition-colors">
                  {test.split('/').pop()}
                  <div className="text-[10px] text-emerald-400/80 mt-0.5">● Auto-targeted by Agent 04</div>
                </div>
              ))}
            </div>
          </div>

          {/* Tier 4: Affected Documentation */}
          <div className="bg-zinc-900/50 rounded-xl p-4 border border-zinc-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                <FileText className="w-4 h-4" /> Documentation
              </span>
              <span className="text-xs bg-indigo-500/20 text-indigo-300 font-mono px-2 py-0.5 rounded">
                {data.affected_docs?.length || 0} docs
              </span>
            </div>
            <div className="space-y-2">
              {data.affected_docs?.map((doc, idx) => (
                <div key={idx} className="p-2.5 rounded-lg bg-zinc-800/60 border border-zinc-700/40 text-xs font-mono text-zinc-300 break-all hover:border-indigo-500/50 transition-colors">
                  {doc.split('/').pop()}
                  <div className="text-[10px] text-indigo-400/80 mt-0.5">● Auto-synced by Agent 03</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

