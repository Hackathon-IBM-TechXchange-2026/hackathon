import React from 'react';
import { GitCommit, FileCode, Plus, Minus, Check } from 'lucide-react';

export default function DiffViewer({ diffContent }) {
  const defaultDiff = `diff --git a/sample-app/src/repository/payment.repository.ts b/sample-app/src/repository/payment.repository.ts
--- a/sample-app/src/repository/payment.repository.ts
+++ b/sample-app/src/repository/payment.repository.ts
@@ -1,3 +1,3 @@
-export type PaymentMethod = 'CREDIT_CARD' | 'DEBIT_CARD' | 'BANK_TRANSFER';
+export type PaymentMethod = 'CREDIT_CARD' | 'DEBIT_CARD' | 'BANK_TRANSFER' | 'PIX';
 
 export interface PaymentRecord {
diff --git a/sample-app/src/services/payment.service.ts b/sample-app/src/services/payment.service.ts
--- a/sample-app/src/services/payment.service.ts
+++ b/sample-app/src/services/payment.service.ts
@@ -20,6 +20,8 @@ export class PaymentService {
       case 'DEBIT_CARD':
         return Number((amount * 0.015 + 0.15).toFixed(2));
       case 'BANK_TRANSFER':
         return Number((amount * 0.005).toFixed(2));
+      case 'PIX':
+        return Number(Math.min(amount * 0.0099, 3.00).toFixed(2));
       default:
         throw new Error(\`Unsupported payment method: \${method}\`);
     }
@@ -35,6 +37,9 @@ export class PaymentService {
     if (input.amount > this.MAX_TRANSACTION_LIMIT) {
       throw new Error(\`Amount exceeds maximum transaction limit of \${this.MAX_TRANSACTION_LIMIT}\`);
     }
+    if (input.method === 'PIX' && input.currency !== 'BRL') {
+      throw new Error('PIX payment method is only supported for BRL currency');
+    }
     if (!this.SUPPORTED_CURRENCIES.has(input.currency.toUpperCase())) {
       throw new Error(\`Unsupported currency: \${input.currency}\`);
     }`;

  const diffText = diffContent || defaultDiff;
  const lines = diffText.split('\n');

  return (
    <div className="glow-card rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/60">
        <div className="flex items-center gap-2">
          <GitCommit className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-bold text-white">Target Change: benchmarks/sample-diff.patch</span>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="text-emerald-400 flex items-center gap-0.5"><Plus className="w-3 h-3" /> 6 additions</span>
          <span className="text-rose-400 flex items-center gap-0.5"><Minus className="w-3 h-3" /> 1 deletion</span>
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

