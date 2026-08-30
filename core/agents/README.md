# Bob Agents — Implementação Python

Este pacote traduz os três specs (`bob-agent-onboarding.md`, `bob-agent-reviewer.md`,
`bob-agent-testing.md`) em código executável. A ideia é separar responsabilidades:

- **O `.md` (o spec do agente)** = a persona/instruções que o **Bob IDE** ou o
  **watsonx Orchestrate** usam para raciocinar, decidir o que fazer e escrever
  a explicação em linguagem natural para o desenvolvedor.
- **O `.py` (este pacote)** = as "mãos" determinísticas do agente: varredura de
  arquivos, regex, `git diff`, execução de `pytest`, parsing com `ast`. Coisas
  que não precisam (e não devem) depender de um LLM para serem confiáveis e
  baratas em tokens.

## Arquivos

| Arquivo | Agente | O que faz |
|---|---|---|
| `onboarding_agent.py` | O Facilitador | Escaneia o repo, detecta stack, gera `AGENTS.md`, diagramas Mermaid e starter tasks |
| `code_reviewer_agent.py` | O Revisor | Escaneia diffs/arquivos, classifica riscos por severidade, gera relatório |
| `test_engineer_agent.py` | O Engenheiro de Qualidade | Gera esqueleto PyTest via AST, roda self-healing loop, estima cobertura |

## Como plugar no IBM Bob IDE

1. Coloque os três `.py` numa pasta `tools/` do repositório.
2. Nos arquivos `.bob/agents/*.md` (os specs que você já tem), adicione uma
   instrução para o Bob invocar o script correspondente via terminal antes de
   escrever a resposta final, por exemplo, no `onboarding-agent.md`:
   ```
   Antes de escrever o relatório, execute:
   `python tools/onboarding_agent.py . --json`
   e use a saída como fonte de verdade para stack, entrypoints e starter tasks.
   ```
3. Isso funciona tanto no **Bob IDE** (agent mode executando comandos com
   auto-approve de `Execute`) quanto no **Bob Shell** (modo não-interativo,
   ideal para rodar em CI/CD).

## Como plugar no watsonx Orchestrate (ADK)

Cada função pública destes módulos pode virar uma **ferramenta Python** do ADK.
Exemplo mínimo de wrapper (`orchestrate_tools.py`):

```python
from ibm_watsonx_orchestrate.agent_builder.tools import tool
from onboarding_agent import run as run_onboarding
from code_reviewer_agent import run as run_review
from test_engineer_agent import generate_test_skeleton, self_healing_loop
from pathlib import Path

@tool
def onboarding_scan(repo_path: str) -> dict:
    """Analisa um repositório e retorna stack, diagramas e starter tasks."""
    return run_onboarding(repo_path)

@tool
def code_review_scan(files: list[str]) -> dict:
    """Roda a varredura estática de segurança/qualidade nos arquivos informados."""
    return run_review(files)

@tool
def generate_tests(module_path: str) -> str:
    """Gera um esqueleto de testes PyTest para o módulo informado."""
    return generate_test_skeleton(Path(module_path))
```

Depois é só registrar essas tools num agente via `orchestrate tools import` /
YAML de definição do agente, seguindo o guia "Connecting to MCP tools with
watsonx Orchestrate" ou "Getting Started with watsonx Orchestrate ADK".

## Limitações conhecidas (importante citar na apresentação do hackathon)

- **Detecção de SQL injection** é baseada em regex simples (concatenação/f-string
  direto no `execute`). Não detecta fluxo de dados através de variáveis
  intermediárias — isso exigiria análise de fluxo de dados (dataflow) ou o
  próprio Bob/LLM analisando semanticamente.
- **Diagrama de classes** via `ast` só funciona nativamente para Python. Para
  outras linguagens, o próprio Bob deve gerar o diagrama via leitura semântica
  do código (ele já sabe fazer isso, como mostrado no guia do hackathon).
- **Self-healing loop** de testes tem um `fixer_callback` como "buraco" —
  na integração real, é o Bob (ou uma chamada à API do watsonx.ai) quem lê o
  traceback e decide a correção; o script só orquestra o ciclo e limita a
  3 iterações para não estourar Bobcoins/créditos.

## Testes rápidos (smoke tests) já validados

```bash
python3 onboarding_agent.py .                        # roda no próprio repo
python3 code_reviewer_agent.py --files caminho.py     # detecta secret hardcoded, except vazio, etc.
python3 test_engineer_agent.py --module m.py --generate --test t.py --run
```
