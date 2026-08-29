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

export default function AgentStatus({ agentsData, activePhase }) {
  const [expandedAgent, setExpandedAgent] = useState('02-code-reviewer');

  const agents = [
    {
      id: '01-change-analyzer',
      name: 'Change Analyzer Agent',
      role: 'Impact Analysis & Blast Radius',
      icon: Search,
      color: 'blue',
      status: activePhase >= 1 ? 'COMPLETED' : 'WAITING',
      duration: '1.2s',
      summary: 'Parsed diff, mapped 2 modified files, 1 affected API endpoint, 2 test suites and 2 doc targets.',
      details: {
        blastRadius: '85.0/100 (HIGH)',
        impactedComponents: ['payment.repository.ts', 'payment.service.ts'],
        dependencies: 'Clean Architecture Layer 1 -> Layer 2 cascade detected.'
      }
    },
    {
      id: '02-code-reviewer',
      name: 'Code Reviewer Agent',
      role: 'Static Security & Standards Audit',
      icon: ShieldCheck,
      color: 'emerald',
      status: activePhase >= 2 ? 'PASSED' : (activePhase === 1 ? 'RUNNING' : 'WAITING'),
      duration: '2.4s',
      summary: '0 Critical, 0 High vulnerabilities. Strict parameter and currency checks verified against rules.',
      details: {
        score: '98/100',
        findings: [
          { severity: 'Passed', category: 'Security', msg: 'PIX currency restriction correctly bound to BRL currency' },
          { severity: 'Info', category: 'Performance', msg: 'Fee cap Math.min evaluated in constant time O(1)' }
        ]
      }
    },
    {
      id: '03-documentation-agent',
      name: 'Documentation Agent',
      role: 'Docs & OpenAPI Sync',
      icon: FileText,
      color: 'indigo',
      status: activePhase >= 2 ? 'SYNCHRONIZED' : (activePhase === 1 ? 'RUNNING' : 'WAITING'),
      duration: '1.8s',
      summary: 'Automatically updated API.md with new PIX method, fee formulas, and ARCHITECTURE.md specs.',
      details: {
        filesModified: ['sample-app/docs/API.md', 'sample-app/docs/ARCHITECTURE.md'],
        schemaSync: 'OpenAPI 3.1 & Markdown schemas 100% aligned.'
      }
    },
    {
      id: '04-test-engineer',
      name: 'Test Engineer Agent',
      role: 'Test Generation & Runner',
      icon: FlaskConical,
      color: 'purple',
      status: activePhase >= 2 ? 'PASSED' : (activePhase === 1 ? 'RUNNING' : 'WAITING'),
      duration: '3.1s',
      summary: 'Generated 3 new test scenarios, 13/13 tests passing, 98.5% branch & line coverage achieved.',
      details: {
        testSuites: ['payment.service.test.ts (8 passed)', 'payment.flow.test.ts (5 passed)'],
        coverage: '98.5% line coverage (Threshold 80% met)'
      }
    },
    {
      id: '05-validation-agent',
      name: 'Validation Agent',
      role: 'Quality Gatekeeper & Sign-off',
      icon: Scale,
      color: 'amber',
      status: activePhase >= 3 ? 'READY_FOR_HUMAN_REVIEW' : (activePhase === 2 ? 'RUNNING' : 'WAITING'),
      duration: '0.9s',
      summary: 'All automated quality gates passed. Readiness score 98/100. Benchmarked 92% effort reduction.',
      details: {
        readinessScore: '98 / 100',
        gateVerdict: 'READY FOR HUMAN REVIEW',
        effortSaved: '92 minutes saved (8 min human review vs 100 min manual)'
      }
    }
  ];

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

      <div className="space-y-3">
        {agents.map((agent) => {
          const Icon = agent.icon;
          const isExpanded = expandedAgent === agent.id;

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
              case 'RUNNING':
                return (
                  <span className="flex items-center gap-1 text-xs font-bold text-blue-400 bg-blue-950/60 px-2.5 py-1 rounded-full border border-blue-500/30 animate-pulse">
                    <Clock className="w-3.5 h-3.5 animate-spin" /> RUNNING...
                  </span>
                );
              default:
                return (
                  <span className="flex items-center gap-1 text-xs font-medium text-zinc-500 bg-zinc-800/80 px-2.5 py-1 rounded-full">
                    WAITING
                  </span>
                );
            }
          };

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
                      <div className="text-[11px] font-semibold text-zinc-400 uppercase">Agent Execution Output</div>
                      <p className="text-zinc-300 font-mono">
                        {typeof agent.details === 'object' ? JSON.stringify(agent.details, null, 1).replace(/[{}\"]/g, '') : agent.details}
                      </p>
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

