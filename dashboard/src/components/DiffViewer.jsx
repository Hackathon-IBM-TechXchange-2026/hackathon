import React, { useState, useEffect } from 'react';
import { GitCommit, FileCode, Plus, Minus, Check } from 'lucide-react';

export default function DiffViewer({ diffContent, diffMeta }) {
  const [fetchedDiff, setFetchedDiff] = useState(null);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    if (diffContent) return;
    fetch('/api/diff')
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => setFetchedDiff(data.diff))
      .catch(() => setLoadError(true));
  }, [diffContent]);

  const diffText = diffContent || fetchedDiff;
  const additions = diffMeta?.total_additions ?? 6;
  const deletions = diffMeta?.total_deletions ?? 1;

  if (loadError) {
    return (
      <div className="glow-card rounded-xl p-6 text-sm text-zinc-400">
        Diff indisponível — suba o servidor (<code className="text-zinc-300">.venv/bin/python core/demo_server.py</code>).
      </div>
    );
  }

  if (!diffText) {
    return (
      <div className="glow-card rounded-xl p-6 text-sm text-zinc-400 animate-pulse">
        Carregando diff real de benchmarks/sample-diff.patch...
      </div>
    );
  }

  const lines = diffText.split('\n');

  return (
    <div className="glow-card rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/60">
        <div className="flex items-center gap-2">
          <GitCommit className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-bold text-white">Target Change: benchmarks/sample-diff.patch</span>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="text-emerald-400 flex items-center gap-0.5"><Plus className="w-3 h-3" /> {additions} additions</span>
          <span className="text-rose-400 flex items-center gap-0.5"><Minus className="w-3 h-3" /> {deletions} deletions</span>
        </div>
      </div>

      <div className="p-4 bg-[#0d0e11] overflow-x-auto text-xs font-mono leading-relaxed">
        {lines.map((line, idx) => {
          let bgClass = 'hover:bg-zinc-800/30 text-zinc-300';
          let indicator = ' ';

          if (line.startsWith('diff --git')) {
            bgClass = 'bg-blue-950/40 text-blue-300 font-bold mt-3 pt-1 border-t border-zinc-800';
          } else if (line.startsWith('@@')) {
            bgClass = 'bg-purple-950/40 text-purple-300 font-semibold my-1 py-0.5';
          } else if (line.startsWith('+') && !line.startsWith('+++')) {
            bgClass = 'bg-emerald-950/40 text-emerald-300 font-semibold';
            indicator = '+';
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            bgClass = 'bg-rose-950/40 text-rose-300 line-through opacity-80';
            indicator = '-';
          }

          return (
            <div key={idx} className={`px-3 py-0.5 flex items-start gap-4 rounded ${bgClass}`}>
              <span className="text-zinc-600 select-none w-8 text-right font-normal">{idx + 1}</span>
              <pre className="font-mono whitespace-pre flex-1">{line}</pre>
            </div>
          );
        })}
      </div>
    </div>
  );
}