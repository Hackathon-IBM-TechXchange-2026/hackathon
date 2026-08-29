"""
Testing Agent ("O Engenheiro de Qualidade")
============================================

Implementação em Python da lógica determinística descrita em
`.bob/agents/test-engineer.md`.

Este módulo:
  1. Gera um esqueleto de testes PyTest a partir da assinatura das
     funções/classes de um módulo (via `ast`).
  2. Executa os testes com timeout e captura falhas.
  3. Roda um "Self-Healing Loop": a cada falha, delega a um `fixer_callback`
     (que na integração real é o Bob/LLM lendo o traceback e reescrevendo
     código) e tenta de novo, até `max_iterations` (default 3) para evitar
     loop infinito de consumo de tokens.
  4. Estima cobertura das funções exercitadas.

Uso:
    python test_engineer_agent.py --module app/services.py --generate
    python test_engineer_agent.py --module app/services.py --test tests/test_services.py --run
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

TEST_TIMEOUT_SECONDS = 10
MAX_ITERATIONS = 3

# --------------------------------------------------------------------------
# 1. Geração de esqueleto de testes via AST
# --------------------------------------------------------------------------

@dataclass
class FunctionSpec:
    name: str
    args: list[str]
    is_method: bool = False
    class_name: Optional[str] = None


def extract_functions(module_path: Path) -> list[FunctionSpec]:
    """Percorre apenas o nível do módulo (tree.body), evitando duplicar
    métodos de classe como funções soltas — ast.walk() sozinho misturaria
    os dois porque visita todos os descendentes sem distinguir escopo."""
    tree = ast.parse(module_path.read_text(encoding="utf-8", errors="ignore"))
    specs: list[FunctionSpec] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                    args = [a.arg for a in item.args.args if a.arg != "self"]
                    specs.append(FunctionSpec(item.name, args, is_method=True, class_name=node.name))
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            args = [a.arg for a in node.args.args]
            specs.append(FunctionSpec(node.name, args))

    return specs


def _module_import_path(module_path: Path) -> str:
    """Converte um caminho de arquivo em um caminho de import Python simplificado."""
    return module_path.stem


def generate_test_skeleton(module_path: Path) -> str:
    specs = extract_functions(module_path)
    module_name = _module_import_path(module_path)

    lines = [
        "import pytest",
        "from unittest.mock import MagicMock, patch",
        f"from {module_name} import *  # noqa: F401,F403 — ajuste o import conforme o pacote real",
        "",
    ]

    if not specs:
        lines.append("# Nenhuma função/método público detectado automaticamente.")
        lines.append("# TODO: adicionar testes manualmente ou revisar o módulo.")
        return "\n".join(lines)

    for spec in specs:
        args_setup = "\n    ".join(f"{a} = MagicMock()" for a in spec.args) or "pass"
        call_target = f"{spec.class_name}().{spec.name}" if spec.is_method else spec.name
        call_args = ", ".join(spec.args)
        test_name = f"test_{spec.class_name.lower() + '_' if spec.class_name else ''}{spec.name}"

        lines.append(f"def {test_name}():")
        lines.append(f"    # Cenário: comportamento padrão de {spec.name}")
        lines.append(f"    {args_setup}")
        lines.append(f"    result = {call_target}({call_args})")
        lines.append("    # TODO: substituir pela asserção real de comportamento esperado")
        lines.append("    assert result is not None")
        lines.append("")
        lines.append(f"def {test_name}_edge_case():")
        lines.append(f"    # Cenário de borda para {spec.name} — TODO: definir input inválido/limite")
        lines.append("    with pytest.raises(Exception):")
        lines.append(f"        {call_target}(*[None] * {len(spec.args)})")
        lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------
# 2. Execução dos testes com timeout
# --------------------------------------------------------------------------

@dataclass
class TestRunResult:
    passed: bool
    returncode: int
    stdout: str
    stderr: str
    failed_tests: list[str] = field(default_factory=list)


FAIL_LINE = re.compile(r"^FAILED\s+(\S+)")


def run_tests(test_path: Path, timeout: int = TEST_TIMEOUT_SECONDS) -> TestRunResult:
    try:
        proc = subprocess.run(
            ["pytest", str(test_path), "-v", "--tb=short"],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        return TestRunResult(False, -1, e.stdout or "", f"Timeout após {timeout}s — possível teste travado/flaky.")
    except FileNotFoundError:
        return TestRunResult(False, -1, "", "pytest não encontrado no ambiente. Ative o venv do projeto.")

    failed = [m.group(1) for line in proc.stdout.splitlines() if (m := FAIL_LINE.match(line))]
    return TestRunResult(proc.returncode == 0, proc.returncode, proc.stdout, proc.stderr, failed)


# --------------------------------------------------------------------------
# 3. Self-Healing Loop
# --------------------------------------------------------------------------

FixerCallback = Callable[[str, TestRunResult], None]
"""Assinatura do callback de correção: recebe (caminho_do_teste, resultado_da_execução)
e deve alterar o arquivo de teste ou o código-fonte em disco. Na integração real,
isso é o Bob (ou watsonx.ai) lendo o traceback e reescrevendo o arquivo problemático."""


def self_healing_loop(test_path: Path, fixer_callback: Optional[FixerCallback] = None,
                       max_iterations: int = MAX_ITERATIONS) -> dict:
    iterations = []

    for i in range(1, max_iterations + 1):
        result = run_tests(test_path)
        iterations.append({
            "iteration": i,
            "status": "PASS" if result.passed else "FAIL",
            "traceback_summary": (result.stderr or result.stdout)[-1500:],
            "failed_tests": result.failed_tests,
        })

        if result.passed:
            break

        if fixer_callback is None:
            iterations[-1]["note"] = ("Nenhum fixer_callback configurado — em produção, "
                                       "aqui entraria a chamada ao Bob/watsonx.ai para corrigir o código.")
            break

        fixer_callback(str(test_path), result)

    final_status = iterations[-1]["status"] if iterations else "UNKNOWN"
    escaped_iterations = i if 'i' in dir() else 0

    if final_status == "FAIL" and len(iterations) >= max_iterations:
        escalation = ("Não foi possível resolver as falhas de teste após "
                       f"{max_iterations} iterações automáticas. É necessária intervenção humana.")
    else:
        escalation = None

    return {"iterations": iterations, "final_status": final_status, "escalation": escalation}


# --------------------------------------------------------------------------
# 4. Estimativa de cobertura (heurística leve, sem dependência de coverage.py)
# --------------------------------------------------------------------------

def estimate_coverage(module_path: Path, test_content: str) -> float:
    specs = extract_functions(module_path)
    if not specs:
        return 0.0
    exercised = sum(1 for s in specs if re.search(rf"\b{re.escape(s.name)}\b", test_content))
    return round(100 * exercised / len(specs), 1)


# --------------------------------------------------------------------------
# 5. Relatório final
# --------------------------------------------------------------------------

def build_report(module_path: Path, test_skeleton: str, healing_result: Optional[dict],
                  coverage_pct: float) -> str:
    iterations_md = ""
    if healing_result:
        for it in healing_result["iterations"]:
            iterations_md += (
                f"**Iteração #{it['iteration']}:** {it['status']}"
                + (f"\n```\n{it['traceback_summary']}\n```\n" if it["status"] == "FAIL" else "\n")
            )
        if healing_result.get("escalation"):
            iterations_md += f"\n⚠️ {healing_result['escalation']}\n"

    return f"""# 🧪 Automated Test Pipeline & Self-Healing

## Seção 1: Test Plan & Scenarios
Testes gerados a partir da assinatura pública de `{module_path.name}` — cenário
padrão + cenário de borda para cada função/método público detectado.

## Seção 2: Test Implementation
```python
{test_skeleton}
```

## Seção 3: Execution Iterations
{iterations_md or "Execução não solicitada nesta chamada (use --run)."}

## Seção 4: Coverage Metrics
Cobertura estimada das funções modificadas: **{coverage_pct}%**
"""


# --------------------------------------------------------------------------
# 6. CLI
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Testing Agent (O Engenheiro de Qualidade)")
    parser.add_argument("--module", required=True, help="Módulo Python a testar")
    parser.add_argument("--test", help="Caminho do arquivo de teste (gerado ou existente)")
    parser.add_argument("--generate", action="store_true", help="Gera o esqueleto de testes")
    parser.add_argument("--run", action="store_true", help="Executa o self-healing loop")
    parser.add_argument("--json", action="store_true", help="Saída em JSON")
    args = parser.parse_args()

    module_path = Path(args.module)
    if not module_path.exists():
        print(f"Módulo não encontrado: {module_path}")
        return

    skeleton = ""
    if args.generate:
        skeleton = generate_test_skeleton(module_path)
        if args.test:
            Path(args.test).write_text(skeleton, encoding="utf-8")

    healing_result = None
    coverage_pct = 0.0
    if args.run:
        if not args.test:
            print("Use --test <arquivo> junto com --run para indicar onde estão os testes.")
            return
        healing_result = self_healing_loop(Path(args.test))
        coverage_pct = estimate_coverage(module_path, Path(args.test).read_text(encoding="utf-8", errors="ignore"))

    report = build_report(module_path, skeleton or "(esqueleto não gerado nesta chamada)",
                           healing_result, coverage_pct)

    if args.json:
        print(json.dumps({
            "skeleton": skeleton,
            "healing_result": healing_result,
            "coverage_pct": coverage_pct,
        }, indent=2, ensure_ascii=False))
    else:
        print(report)


if __name__ == "__main__":
    main()
