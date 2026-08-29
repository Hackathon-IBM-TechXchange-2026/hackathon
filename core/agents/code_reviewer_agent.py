"""
Code Reviewer Agent ("O Revisor")
==================================

Implementação em Python da lógica determinística descrita em
`.bob/agents/code-reviewer.md`.

Faz uma varredura estática (regex/heurísticas) por padrões de risco em
segurança, lógica e clean code, e produz o relatório no formato exigido
pelo spec (tabela de severidade + detalhamento). A parte semântica mais
profunda (ex.: "essa validação realmente cobre esse caso de negócio?")
continua sendo responsabilidade do Bob/LLM — este módulo entrega os
"fatos brutos" e uma primeira triagem para ele refinar.

Uso:
    python code_reviewer_agent.py --diff                # revisa git diff (staged+unstaged)
    python code_reviewer_agent.py --files a.py b.py      # revisa arquivos específicos
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# 1. Severidades
# --------------------------------------------------------------------------

CRITICAL = "🔴 CRITICAL"
HIGH = "🟠 HIGH"
MEDIUM = "🟡 MEDIUM"
LOW = "🟢 LOW"

SEVERITY_ORDER = [CRITICAL, HIGH, MEDIUM, LOW]


@dataclass
class Finding:
    severity: str
    file: str
    line: int
    description: str
    snippet: str
    suggested_fix: str = ""


# --------------------------------------------------------------------------
# 2. Regras de detecção (heurísticas / regex)
# --------------------------------------------------------------------------

RULES = [
    # (severidade, regex, descrição, sugestão)
    (CRITICAL,
     re.compile(r"""(execute|cursor\.execute|query)\s*\(\s*["'].*%s.*["']\s*%|"""
                 r"""(execute|cursor\.execute)\s*\(\s*f["']""", re.IGNORECASE),
     "Possível SQL Injection: construção de query por concatenação/format string.",
     "Use parameterized queries: cursor.execute(\"SELECT * FROM t WHERE id = %s\", (id,))"),

    (CRITICAL,
     re.compile(r"""(api[_-]?key|secret|password|token)\s*=\s*["'][A-Za-z0-9/_\-\.]{8,}["']""",
                re.IGNORECASE),
     "Possível segredo/credencial hardcoded no código-fonte.",
     "Mova o valor para variável de ambiente ou secret manager (ex: os.environ['API_KEY'])."),

    (HIGH,
     re.compile(r"""(print|log(ger)?\.\w+)\s*\(.*(password|card[_-]?number|ssn|cpf)""",
                re.IGNORECASE),
     "Log potencialmente expõe dado sensível (violação de PCI/LGPD).",
     "Mascare o dado sensível antes de logar (ex: '***' + card[-4:])."),

    (HIGH,
     re.compile(r"""except\s*:\s*$|except\s+Exception\s*:\s*pass"""),
     "Bloco except vazio/genérico engole erros silenciosamente.",
     "Capture exceções específicas e trate ou re-lance com contexto (raise ... from e)."),

    (HIGH,
     re.compile(r"""open\([^)]*\)(?!\s*as)"""),
     "Arquivo aberto sem context manager — risco de vazamento de handle.",
     "Use 'with open(...) as f:' para garantir o fechamento do recurso."),

    (MEDIUM,
     re.compile(r"""^\s*def\s+\w+\([^)]*\):"""),
     "Função encontrada — validar tamanho/complexidade (checagem automática abaixo).",
     ""),

    (LOW,
     re.compile(r"""[ \t]+$"""),
     "Espaço em branco no final da linha.",
     "Remova espaços em branco à direita (trailing whitespace)."),
]

# Regra especial: função com corpo muito longo (proxy simples de complexidade)
MAX_FUNCTION_LINES = 60
MAX_FILE_LINES_FOR_SINGLE_PASS = 800  # ligado ao fallback de "código extenso"


def _scan_function_length(filename: str, lines: list[str]) -> list[Finding]:
    findings = []
    func_start = None
    func_name = None
    for i, line in enumerate(lines):
        m = re.match(r"^\s*def\s+(\w+)\(", line)
        if m:
            if func_start is not None and i - func_start > MAX_FUNCTION_LINES:
                findings.append(Finding(
                    MEDIUM, filename, func_start + 1,
                    f"Função '{func_name}' tem mais de {MAX_FUNCTION_LINES} linhas — "
                    "alta complexidade cognitiva.",
                    lines[func_start].strip(),
                    "Considere quebrar em funções menores com responsabilidade única."))
            func_start = i
            func_name = m.group(1)
    return findings


def scan_content(filename: str, content: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = content.splitlines()

    for lineno, line in enumerate(lines, 1):
        for severity, pattern, desc, fix in RULES:
            if severity == MEDIUM and pattern.pattern.startswith("^\\s*def"):
                continue  # tratado separadamente por _scan_function_length
            if pattern.search(line):
                findings.append(Finding(severity, filename, lineno, desc, line.strip(), fix))

    findings.extend(_scan_function_length(filename, lines))
    return findings


# --------------------------------------------------------------------------
# 3. Coleta de conteúdo: git diff ou lista de arquivos
# --------------------------------------------------------------------------

def get_git_diff_files(repo_path: str = ".") -> list[str]:
    """Retorna a lista de arquivos alterados (staged + unstaged) no repo."""
    try:
        out = subprocess.run(
            ["git", "-C", repo_path, "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        return [f for f in out.stdout.splitlines() if f.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return []


# --------------------------------------------------------------------------
# 4. Relatório
# --------------------------------------------------------------------------

def build_report(findings: list[Finding]) -> str:
    counts = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        counts[f.severity] += 1

    status = {
        CRITICAL: "[FAILED / ACTION REQUIRED]" if counts[CRITICAL] else "[PASSED]",
        HIGH: "[ACTION RECOMMENDED]" if counts[HIGH] else "[PASSED]",
        MEDIUM: "[REVIEW SUGGESTED]" if counts[MEDIUM] else "[PASSED]",
        LOW: "[PASSED / SUGGESTION]",
    }

    table = "\n".join(
        f"| {sev} | {counts[sev]} | {status[sev]} |" for sev in SEVERITY_ORDER
    )

    details = []
    for i, f in enumerate(sorted(findings, key=lambda x: SEVERITY_ORDER.index(x.severity)), 1):
        details.append(
            f"### {i}. {f.severity} — `{f.file}:{f.line}`\n"
            f"**Descrição:** {f.description}\n\n"
            f"**Código encontrado:**\n```\n{f.snippet}\n```\n"
            + (f"**Sugestão de correção:** {f.suggested_fix}\n" if f.suggested_fix else "")
        )

    return f"""# 🔍 Code Review & Security Report

## Painel de Status
| Severidade | Quantidade | Status |
| :--- | :--- | :--- |
{table}

## Seção de Detalhes
{chr(10).join(details) if details else "Nenhum problema encontrado pela varredura automática."}
"""


# --------------------------------------------------------------------------
# 5. CLI
# --------------------------------------------------------------------------

def run(paths: list[str]) -> dict:
    all_findings: list[Finding] = []
    total_lines = 0

    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        total_lines += len(content.splitlines())

        if total_lines > MAX_FILE_LINES_FOR_SINGLE_PASS:
            return {"error": (
                "O volume de código enviado ultrapassa o limite de revisão semântica "
                "segura em uma única execução. Por favor, fragmente as alterações ou "
                "use @nome_do_arquivo para me focar em um componente específico."
            )}

        all_findings.extend(scan_content(str(path), content))

    return {
        "report_markdown": build_report(all_findings),
        "findings": [f.__dict__ for f in all_findings],
        "counts": {s: sum(1 for f in all_findings if f.severity == s) for s in SEVERITY_ORDER},
    }


def main():
    parser = argparse.ArgumentParser(description="Code Reviewer Agent (O Revisor)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--diff", action="store_true", help="Revisa arquivos alterados no git diff")
    group.add_argument("--files", nargs="+", help="Lista explícita de arquivos a revisar")
    parser.add_argument("--repo", default=".", help="Caminho do repositório (para --diff)")
    parser.add_argument("--json", action="store_true", help="Saída em JSON")
    args = parser.parse_args()

    paths = get_git_diff_files(args.repo) if args.diff else args.files
    result = run(paths)

    if "error" in result:
        print(result["error"])
        return

    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else result["report_markdown"])


if __name__ == "__main__":
    main()
