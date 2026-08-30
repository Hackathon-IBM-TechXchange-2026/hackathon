"""
Onboarding Agent ("O Facilitador")
==================================

Implementação em Python da lógica determinística descrita em
`.bob/agents/onboarding-agent.md`.

Este módulo NÃO substitui o Bob/LLM — ele é a "mão" do agente: faz o
trabalho mecânico (varrer arquivos, extrair metadados, montar diagramas)
que o Bob então usa como contexto para escrever a explicação em linguagem
natural. Pode ser exposto como:
  - uma ferramenta MCP para o Bob IDE
  - um "tool" Python de um agente watsonx Orchestrate (ADK)
  - um script chamado pelo Bob Shell em modo não-interativo

Uso:
    python onboarding_agent.py /caminho/do/repositorio
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# 1. Respeito ao .bobignore
# --------------------------------------------------------------------------

DEFAULT_IGNORES = [
    ".git", ".git/*", "node_modules", "node_modules/*",
    "__pycache__", "__pycache__/*", "*.pyc", ".venv", ".venv/*",
    "dist", "dist/*", "build", "build/*",
]


def load_bobignore(root: Path) -> list[str]:
    """Lê .bobignore (se existir) e retorna padrões de exclusão."""
    patterns = list(DEFAULT_IGNORES)
    bobignore = root / ".bobignore"
    if bobignore.exists():
        for line in bobignore.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def is_ignored(rel_path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pat) or rel_path.startswith(pat.rstrip("/*"))
               for pat in patterns)


def walk_repo(root: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        dirnames[:] = [d for d in dirnames if not is_ignored(
            os.path.normpath(os.path.join(rel_dir, d)), patterns)]
        for fname in filenames:
            rel = os.path.normpath(os.path.join(rel_dir, fname))
            if not is_ignored(rel, patterns):
                files.append(Path(dirpath) / fname)
    return files


# --------------------------------------------------------------------------
# 2. Detecção de stack tecnológica
# --------------------------------------------------------------------------

STACK_SIGNATURES = {
    "package.json": ("Node.js / JavaScript", "npm/yarn"),
    "requirements.txt": ("Python", "pip"),
    "pyproject.toml": ("Python", "poetry/pip"),
    "pom.xml": ("Java", "Maven"),
    "build.gradle": ("Java/Kotlin", "Gradle"),
    "go.mod": ("Go", "go modules"),
    "Cargo.toml": ("Rust", "cargo"),
    "composer.json": ("PHP", "composer"),
    "Gemfile": ("Ruby", "bundler"),
}

ENTRYPOINT_CANDIDATES = [
    "main.py", "app.py", "manage.py", "index.js", "server.js",
    "app.js", "Main.java", "Application.java", "main.go", "src/main.rs",
]


@dataclass
class StackInfo:
    language: str = "Desconhecido"
    package_manager: str = "Desconhecido"
    key_files: list[str] = field(default_factory=list)
    entrypoints: list[str] = field(default_factory=list)
    env_vars: list[str] = field(default_factory=list)


def detect_stack(root: Path, files: list[Path]) -> StackInfo:
    info = StackInfo()
    names = {f.name: f for f in files}

    for signature, (lang, pm) in STACK_SIGNATURES.items():
        if signature in names:
            info.language = lang
            info.package_manager = pm
            info.key_files.append(signature)

    for candidate in ENTRYPOINT_CANDIDATES:
        for f in files:
            rel = f.relative_to(root).as_posix()
            if rel == candidate or rel.endswith("/" + candidate):
                info.entrypoints.append(rel)

    for f in files:
        if f.name in (".env.example", ".env.sample", "env.example"):
            content = f.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    info.env_vars.append(line.split("=", 1)[0].strip())

    return info


# --------------------------------------------------------------------------
# 3. Diagrama de classes (Mermaid) via AST — para projetos Python
# --------------------------------------------------------------------------

def build_class_diagram(root: Path, files: list[Path]) -> str:
    lines = ["classDiagram"]
    found_any = False

    for f in files:
        if f.suffix != ".py":
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                found_any = True
                lines.append(f"    class {node.name} {{")
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        args = [a.arg for a in item.args.args if a.arg != "self"]
                        lines.append(f"        +{item.name}({', '.join(args)})")
                lines.append("    }")
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        lines.append(f"    {base.id} <|-- {node.name}")

    if not found_any:
        lines.append("    class ProjetoNaoPython")
        lines.append('    note for ProjetoNaoPython "Diagrama de classes automático suportado para Python. Para outras linguagens, o Bob deve gerar via análise semântica (LLM)."')

    return "\n".join(lines)


def build_sequence_diagram_template(entrypoints: list[str]) -> str:
    """Gera um esqueleto de diagrama de sequência a partir dos entrypoints.

    O preenchimento fino do fluxo (quem chama quem) é deixado para o Bob,
    que tem contexto semântico; aqui só fixamos os atores conhecidos.
    """
    ep = entrypoints[0] if entrypoints else "Entrypoint"
    return (
        "sequenceDiagram\n"
        "    actor Dev as Desenvolvedor\n"
        f"    participant EP as {ep}\n"
        "    participant Core as Módulo Central\n"
        "    Dev->>EP: Inicia a aplicação\n"
        "    EP->>Core: Delega processamento\n"
        "    Core-->>EP: Retorna resultado\n"
        "    EP-->>Dev: Resposta / saída\n"
    )


# --------------------------------------------------------------------------
# 4. Starter tasks (TODOs e débitos técnicos simples)
# --------------------------------------------------------------------------

TODO_PATTERN = re.compile(r"(TODO|FIXME|HACK)[:\s](.*)", re.IGNORECASE)


def find_starter_tasks(root: Path, files: list[Path], limit: int = 3) -> list[dict]:
    tasks = []
    text_ext = {".py", ".js", ".ts", ".java", ".go", ".rb", ".php", ".rs"}
    for f in files:
        if f.suffix not in text_ext:
            continue
        try:
            for lineno, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                match = TODO_PATTERN.search(line)
                if match:
                    tasks.append({
                        "file": f.relative_to(root).as_posix(),
                        "line": lineno,
                        "tag": match.group(1).upper(),
                        "text": match.group(2).strip(),
                    })
                    if len(tasks) >= limit:
                        return tasks
        except (UnicodeDecodeError, OSError):
            continue
    return tasks


# --------------------------------------------------------------------------
# 5. Geração do AGENTS.md e do relatório final
# --------------------------------------------------------------------------

def generate_agents_md(stack: StackInfo) -> str:
    return (
        "# AGENTS.md\n\n"
        f"## Stack\n- Linguagem: {stack.language}\n"
        f"- Gerenciador de dependências: {stack.package_manager}\n"
        f"- Arquivos-chave: {', '.join(stack.key_files) or 'N/A'}\n\n"
        f"## Entrypoints\n" + "\n".join(f"- `{e}`" for e in stack.entrypoints or ["N/A"]) + "\n\n"
        f"## Variáveis de ambiente esperadas\n" + "\n".join(f"- `{v}`" for v in stack.env_vars or ["N/A"]) + "\n"
    )


def generate_report(root: Path, stack: StackInfo, class_diagram: str,
                     sequence_diagram: str, tasks: list[dict]) -> str:
    setup_steps = [
        f"1. Instale as dependências com **{stack.package_manager}**.",
        "2. Copie `.env.example` para `.env` e preencha as variáveis listadas abaixo.",
        f"3. Rode o entrypoint: `{stack.entrypoints[0] if stack.entrypoints else '<definir entrypoint>'}`.",
    ]

    tasks_md = "\n".join(
        f"- **[{t['tag']}]** `{t['file']}:{t['line']}` — {t['text']}"
        for t in tasks
    ) or "- Nenhum TODO/FIXME encontrado automaticamente. Peça ao Bob para sugerir tarefas com base na complexidade dos módulos."

    return f"""# 🚀 Onboarding & Codebase Insights

## Seção 1: Quick Stack & Architecture Overview

| Item | Valor |
|---|---|
| Linguagem | {stack.language} |
| Gerenciador de dependências | {stack.package_manager} |
| Entrypoints | {', '.join(stack.entrypoints) or 'N/A'} |

### Diagrama de Classes/Módulos
```mermaid
{class_diagram}
```

### Diagrama de Sequência
```mermaid
{sequence_diagram}
```

## Seção 2: Local Setup in 3 Steps
{chr(10).join(setup_steps)}

### Variáveis de ambiente
{chr(10).join(f'- `{v}`' for v in stack.env_vars) if stack.env_vars else '- Nenhuma variável detectada em .env.example'}

## Seção 3: Starter Tasks Recommendations
{tasks_md}
"""


# --------------------------------------------------------------------------
# 6. CLI
# --------------------------------------------------------------------------

def run(repo_path: str) -> dict:
    root = Path(repo_path).resolve()
    if not root.exists():
        return {
            "error": ("Não consegui mapear os pontos de entrada do projeto de forma "
                       "automática. Por favor, indique qual é o arquivo principal ou "
                       "a stack padrão do repositório para que eu possa gerar a "
                       "documentação e os guias corretos.")
        }

    patterns = load_bobignore(root)
    files = walk_repo(root, patterns)
    stack = detect_stack(root, files)
    class_diagram = build_class_diagram(root, files)
    sequence_diagram = build_sequence_diagram_template(stack.entrypoints)
    tasks = find_starter_tasks(root, files)

    agents_md = generate_agents_md(stack)
    report = generate_report(root, stack, class_diagram, sequence_diagram, tasks)

    return {
        "agents_md": agents_md,
        "report_markdown": report,
        "stack": stack.__dict__,
        "starter_tasks": tasks,
    }


def main():
    parser = argparse.ArgumentParser(description="Onboarding Agent (O Facilitador)")
    parser.add_argument("repo_path", help="Caminho do repositório a analisar")
    parser.add_argument("--write-agents-md", action="store_true",
                         help="Escreve AGENTS.md na raiz do repositório")
    parser.add_argument("--json", action="store_true", help="Saída em JSON")
    args = parser.parse_args()

    result = run(args.repo_path)

    if "error" in result:
        print(result["error"])
        return

    if args.write_agents_md:
        Path(args.repo_path, "AGENTS.md").write_text(result["agents_md"], encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(result["report_markdown"])


if __name__ == "__main__":
    main()
