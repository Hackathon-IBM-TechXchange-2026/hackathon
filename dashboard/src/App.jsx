import React, { useState } from 'react';
import { 
  Bot, 
  Layers, 
  Play, 
  RotateCcw, 
  GitPullRequest, 
  ShieldCheck, 
  CheckCircle2, 
  TrendingDown, 
  FileCode, 
  Clock, 
  Network, 
  Award,
  Sparkles,
  ExternalLink,
  ChevronRight
} from 'lucide-react';

import ImpactViewer from './components/ImpactViewer';
import AgentStatus from './components/AgentStatus';
import MetricsBadge from './components/MetricsBadge';
import DiffViewer from './components/DiffViewer';
import HumanApprovalModal from './components/HumanApprovalModal';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [pipelinePhase, setPipelinePhase] = useState(3); // 0: Idle, 1: Analyzer, 2: Parallel, 3: Gatekeeper, 4: Merged
  const [isSimulating, setIsSimulating] = useState(false);
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isApproved, setIsApproved] = useState(false);
  const [approvalNote, setApprovalNote] = useState('');

  const runSimulation = () => {
    setIsSimulating(true);
    setIsApproved(false);
    setPipelinePhase(0);

    setTimeout(() => {
      setPipelinePhase(1); // 01 Analyzer
      setTimeout(() => {
        setPipelinePhase(2); // 02, 03, 04 in Parallel
        setTimeout(() => {
          setPipelinePhase(3); // 05 Validation Gatekeeper
          setIsSimulating(false);
        }, 1200);
      }, 1000);
    }, 600);
  };

  const handleApprove = (note) => {
    setIsApproved(true);
    setApprovalNote(note || 'Approved by Lead Engineer via ChangeFlow Portal.');
    setPipelinePhase(4);
  };

  return (
    <div className="min-h-screen bg-[#0c0d0f] text-zinc-100 flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-tr from-blue-600 to-indigo-500 rounded-xl shadow-lg shadow-blue-500/20 text-white font-black">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg tracking-tight text-white">ChangeFlow</span>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-500/10 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded-full">
                  IBM Bob 2.0
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 font-normal">AI-Powered Software Change Intelligence</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={runSimulation}
              disabled={isSimulating}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                isSimulating 
                  ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                  : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 hover:border-zinc-600'
              }`}
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isSimulating ? 'animate-spin' : ''}`} />
              Re-run Pipeline
            </button>

            <button
              onClick={() => setIsApprovalOpen(true)}
              className={`px-4 py-1.5 rounded-xl text-xs font-bold flex items-center gap-2 transition-all shadow-md ${
                isApproved
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white glow-blue'
              }`}
            >
              {isApproved ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Merged to Main
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" /> Human Sign-Off Gate
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Banner with Value Proposition */}
        <div className="glow-card rounded-2xl p-6 relative overflow-hidden bg-gradient-to-r from-blue-950/30 via-zinc-900/60 to-purple-950/20 border border-blue-500/20">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1 max-w-2xl">
              <div className="flex items-center gap-2 text-xs font-bold text-blue-400 uppercase tracking-wider">
                <Sparkles className="w-4 h-4" /> Hackathon IBM Dev Day — IBM Bob 2.0
              </div>
              <h2 className="text-2xl font-black text-white tracking-tight">
                From Code Change to Production-Ready Change.
              </h2>
              <p className="text-xs sm:text-sm text-zinc-300">
                Toda alteração de código encadeia um efeito cascata. O ChangeFlow orquestra subagentes em paralelo para análise de impacto, revisão estática, sincronização documental e testes automáticos — preservando a decisão final humana.
              </p>
            </div>

            <div className="flex items-center gap-4 self-start md:self-center bg-black/40 px-4 py-3 rounded-xl border border-zinc-800">
              <div className="text-center">
                <span className="text-[10px] text-zinc-400 uppercase font-semibold block">Manual</span>
                <span className="text-xl font-bold text-rose-400 font-mono">100 min</span>
              </div>
              <ChevronRight className="w-4 h-4 text-zinc-600" />
              <div className="text-center">
                <span className="text-[10px] text-emerald-400 uppercase font-semibold block">ChangeFlow</span>
                <span className="text-xl font-bold text-emerald-400 font-mono">8 min</span>
              </div>
              <div className="w-px h-8 bg-zinc-800"></div>
              <div className="text-center">
                <span className="text-[10px] text-blue-400 uppercase font-semibold block">Effort Saved</span>
                <span className="text-xl font-black text-blue-400 font-mono">-92%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Pipeline Stage Stepper */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { step: '01', title: 'Diff Analysis', agent: '01-change-analyzer', phase: 1 },
            { step: '02', title: 'Code Review', agent: '02-code-reviewer', phase: 2 },
            { step: '03', title: 'Docs Sync', agent: '03-documentation', phase: 2 },
            { step: '04', title: 'Test Runner', agent: '04-test-engineer', phase: 2 },
            { step: '05', title: 'Gatekeeper & Sign-off', agent: '05-validation', phase: 3 }
          ].map((item, idx) => {
            const isCompleted = pipelinePhase >= item.phase;
            const isCurrent = pipelinePhase === item.phase - 1;

            return (
              <div
                key={idx}
                className={`p-3.5 rounded-xl border transition-all ${
                  isCompleted
                    ? 'bg-zinc-900/90 border-emerald-500/40 text-emerald-400'
                    : isCurrent
                    ? 'bg-blue-950/30 border-blue-500 text-blue-300 animate-pulse'
                    : 'bg-zinc-900/40 border-zinc-800/60 text-zinc-500'
                }`}
              >
                <div className="flex items-center justify-between text-[11px] font-mono mb-1">
                  <span>STEP {item.step}</span>
                  {isCompleted ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Clock className="w-3.5 h-3.5" />}
                </div>
                <div className="font-bold text-xs text-white truncate">{item.title}</div>
                <div className="text-[10px] text-zinc-400 truncate mt-0.5">.{item.agent}</div>
              </div>
            );
          })}
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-zinc-800 space-x-2">
          {[
            { id: 'overview', label: 'Executive Overview', icon: Layers },
            { id: 'agents', label: 'Subagents Pipeline', icon: Bot },
            { id: 'impact', label: 'Impact & Blast Radius', icon: Network },
            { id: 'diff', label: 'Git Diff Inspector', icon: FileCode },
            { id: 'benchmarks', label: 'Benchmark Data (-92%)', icon: Award }
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`pb-3 px-3 text-xs sm:text-sm font-semibold flex items-center gap-2 border-b-2 transition-all select-none ${
                  isActive
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content Panels */}
        <div className="space-y-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <MetricsBadge />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <ImpactViewer />
                <div className="space-y-6">
                  <AgentStatus activePhase={pipelinePhase} />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'agents' && (
            <div className="space-y-6">
              <AgentStatus activePhase={pipelinePhase} />
            </div>
          )}

          {activeTab === 'impact' && (
            <div className="space-y-6">
              <ImpactViewer />
            </div>
          )}

          {activeTab === 'diff' && (
            <div className="space-y-6">
              <DiffViewer />
            </div>
          )}

          {activeTab === 'benchmarks' && (
            <div className="space-y-6">
              <MetricsBadge />
            </div>
          )}
        </div>
      </main>

      {/* Human In The Loop Approval Modal */}
      <HumanApprovalModal
        isOpen={isApprovalOpen}
        onClose={() => setIsApprovalOpen(false)}
        onApprove={handleApprove}
        isApproved={isApproved}
      />

      {/* Footer */}
      <footer className="border-t border-zinc-800/60 py-6 mt-12 bg-zinc-950/60 text-center text-xs text-zinc-500">
        <p>ChangeFlow — AI-Powered Software Change Intelligence • IBM Bob 2.0 Hackathon Challenge</p>
      </footer>
    </div>
  );
}

