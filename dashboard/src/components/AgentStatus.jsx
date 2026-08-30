import React, { useState } from 'react';
import { 
  Bot, 
  CheckCircle2, 
  Clock, 
  ShieldCheck, 
  FileText, 
  FlaskConical, 
  Scale, 
  Search, 
  ChevronRight, 
  ChevronDown, 
  AlertCircle,
  Sparkles,
  Terminal
} from 'lucide-react';

function buildAgents(agentsData) {
  if (!agentsData) return [];
  const analyzer = agentsData.analyzer || {};
  const reviewer = agentsData.reviewer || {};
  const documentation = agentsData.documentation || {};
  const tester = agentsData.tester || {};
  const validation = agentsData.validation || {};
  const impact = analyzer.data || {};

  const fmtSec = (s) => (s === undefined || s === null ? '-' : `${Number(s).toFixed(3)}s`);

  return [
    {
      id: '01-change-analyzer',
      name: 'Change Analyzer Agent',
      role: 'Impact Analysis & Blast Radius',
      icon: Search,
      color: 'blue',
      status: analyzer.status || 'WAITING',
      duration: fmtSec(analyzer.duration_seconds),
      summary: impact.summary || 'No run data available yet.',
      details: {
        blastRadius: `${impact.blast_radius_score ?? '?'}/100 (${impact.risk_level ?? '?'})`,
        filesChanged: impact.files_changed ?? 0,
        impactedComponents: impact.impacted_components ?? [],
        endpoints: (impact.affected_apis ?? []).map((a) => `${a.method} ${a.endpoint}`),
        targetTestSuites: impact.affected_tests ?? [],
        affectedDocs: impact.affected_docs ?? []
      }
    },
    {
      id: '02-code-reviewer',
      name: 'Code Reviewer Agent',
      role: 'Static Security & Standards Audit',
      icon: ShieldCheck,
      color: 'emerald',
      status: reviewer.status || 'WAITING',
      duration: fmtSec(reviewer.duration_seconds),
      summary: reviewer.summary || 'No run data available yet.',
      details: {
        score: `${reviewer.score ?? '?'}/100`,
        filesScanned: reviewer.files_scanned ?? [],
        findings: (reviewer.findings ?? []).map((f) => `${f.severity}: ${f.message} (${f.file}:${f.line})`),
        passedChecks: (reviewer.passed_checks ?? []).map((c) => `✓ ${c.message}`)
      }
    },
    {
      id: '03-documentation-agent',
      name: 'Documentation Agent',
      role: 'Docs & OpenAPI Sync',
      icon: FileText,
      color: 'indigo',
      status: documentation.status || 'WAITING',
      duration: fmtSec(documentation.duration_seconds),
      summary: `${documentation.total_doc_files_modified ?? 0} files updated, ${(documentation.new_identifiers ?? []).length} new identifiers documented.`,
      details: {
        newIdentifiers: documentation.new_identifiers ?? [],
        updatedFiles: (documentation.docs_updated ?? []).map((u) => `${u.change_type}: ${u.file}`),
        syncStatus: documentation.sync_status ?? 'UNKNOWN'
      }
    },
    {
      id: '04-test-engineer',
      name: 'Test Engineer Agent',
      role: 'Test Generation & Runner',
      icon: FlaskConical,
      color: 'purple',
      status: tester.status || 'WAITING',
      duration: fmtSec(tester.execution_time_seconds ?? tester.duration_seconds),
      summary: tester.summary || 'No run data available yet.',
      details: {
        tests: `${tester.tests_passed ?? 0} / ${tester.tests_executed ?? 0} passing`,
        coverage: `${tester.coverage_percentage ?? 0}% statement coverage`,
        coverageDetail: tester.coverage?.overall || null,
        testSuites: (tester.test_suites ?? []).map((s) => `${s.suite.split('/').pop()} → ${s.passed} passed / ${s.failed} failed`)
      }
    },
    {
      id: '05-validation-agent',
      name: 'Validation Agent',
      role: 'Quality Gatekeeper & Sign-off',
      icon: Scale,
      color: 'amber',
      status: validation.status || 'WAITING',
      duration: fmtSec(validation.duration_seconds),
      summary: validation.summary_verdict || 'No run data available yet.',
      details: {
        readinessScore: `${validation.readiness_score ?? '?'} / 100`,
        checklist: validation.checklists || null,
        gateVerdict: validation.gate_status || 'UNKNOWN',
        savings: validation.metrics?.totals
          ? `${validation.metrics.totals.effort_saved_percentage}% de redução (ESTIMADO, baseline de referência) · automação real medida: ${validation.metrics.totals.changeflow_automated_total_seconds}s`
          : 'N/A'
      }
    }
  ];
}

export default function AgentStatus({ agentsData, activePhase }) {
  const [expandedAgent, setExpandedAgent] = useState('02-code-reviewer');
  const agents = buildAgents(agentsData);

  const getStatusBadge = (status) => {
    switch (status) {
      case 'COMPLETED':
      case 'PASSED':
      case 'SYNCHRONIZED':
      case 'READY_FOR_HUMAN_REVIEW':
        return (
          <span className="flex items-center gap-1 text-xs font-bold text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded-full border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" /> {status}
          </span>
        );
      case 'BLOCKED':
      case 'FAILED':
        return (
          <span className="flex items-center gap-1 text-xs font-bold text-rose-400 bg-rose-950/60 px-2.5 py-1 rounded-full border border-rose-500/30">
            <AlertCircle className="w-3.5 h-3.5" /> {status}
          </span>
        );
      case 'RUNNING':
        return (
          <span className="flex items-center gap-1 text-xs font-bold text-blue-400 bg-blue-950/60 px-2.5 py-1 rounded-full border border-blue-500/30 animate-pulse">
            <Clock className="w-3.5 h-3.5 animate-spin" /> RUNNING...
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-xs font-medium text-zinc-500 bg-zinc-800/80 px-2.5 py-1 rounded-full">
            {status || 'WAITING'}
          </span>
        );
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Bot className="w-5 h-5 text-blue-400" />
            IBM Bob 2.0 Subagents Orchestration Pipeline
          </h3>
          <p className="text-xs text-zinc-400">Autonomous subagent execution with parallelized Phase 2 workflow</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1 font-medium">
            <Sparkles className="w-3 h-3" /> 3 Subagents in Parallel
          </span>
        </div>
      </div>

      {agents.length === 0 && (
        <div className="glow-card rounded-xl p-6 text-sm text-zinc-400">
          Sem dados ainda. Clique em <strong className="text-blue-400">Re-run Pipeline</strong> (o servidor
          <code className="text-zinc-300"> /api/run </code>
          precisa estar no ar via <code className="text-zinc-300">.venv/bin/python core/demo_server.py</code>).
        </div>
      )}

      <div className="space-y-3">
        {agents.map((agent) => {
          const Icon = agent.icon;
          const isExpanded = expandedAgent === agent.id;

          return (
            <div 
              key={agent.id} 
              className={`glow-card rounded-xl transition-all border ${isExpanded ? 'border-blue-500/40 bg-zinc-900/90' : 'border-zinc-800/70 hover:border-zinc-700/80'}`}
            >
              <div 
                className="p-4 flex items-center justify-between cursor-pointer select-none"
                onClick={() => setExpandedAgent(isExpanded ? null : agent.id)}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-xl bg-zinc-800/90 border border-zinc-700/60 text-blue-400`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-zinc-400">{agent.id}</span>
                      <h4 className="font-bold text-white text-sm">{agent.name}</h4>
                      <span className="text-[11px] text-zinc-500 font-normal">({agent.role})</span>
                    </div>
                    <p className="text-xs text-zinc-400 mt-0.5">{agent.summary}</p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <span className="text-xs font-mono text-zinc-400 hidden sm:inline">{agent.duration}</span>
                  {getStatusBadge(agent.status)}
                  {isExpanded ? <ChevronDown className="w-4 h-4 text-zinc-400" /> : <ChevronRight className="w-4 h-4 text-zinc-400" />}
                </div>
              </div>

              {isExpanded && (
                <div className="px-5 pb-5 pt-2 border-t border-zinc-800/60 text-xs space-y-3 bg-black/20">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                    <div className="bg-zinc-900/80 p-3 rounded-lg border border-zinc-800 space-y-1">
                      <div className="text-[11px] font-semibold text-zinc-400 uppercase">Persona Definition</div>
                      <p className="font-mono text-zinc-300">.bob/agents/{agent.id}.md</p>
                    </div>

                    <div className="bg-zinc-900/80 p-3 rounded-lg border border-zinc-800 space-y-1">
                      <div className="text-[11px] font-semibold text-zinc-400 uppercase">Agent Execution Output (Real)</div>
                      <pre className="text-zinc-300 font-mono whitespace-pre-wrap">
                        {typeof agent.details === 'object' ? JSON.stringify(agent.details, null, 1).replace(/[{}\"]/g, '') : agent.details}
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}