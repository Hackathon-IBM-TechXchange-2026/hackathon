# ChangeFlow — Visão Técnica: Objetivo, Funcionamento, Vantagens e Limitações

---

## Por que esse código existe?

Toda vez que um desenvolvedor faz uma mudança no código, uma série de tarefas chatas e repetitivas precisa acontecer:

- Alguém precisa revisar se o código está seguro
- Alguém precisa atualizar a documentação
- Os testes precisam ser rodados
- Alguém precisa verificar se a cobertura de testes está boa
- Alguém precisa decidir se pode ir para produção

Em times de engenharia, isso costuma demorar **100 minutos** por Pull Request — entre revisar, comentar, corrigir, rodar CI, e aprovar.

O ChangeFlow automatiza esse processo todo, deixando o desenvolvedor fazer apenas a decisão final: **aprovar ou rejeitar o merge**. O resto é feito em menos de 2 minutos por IA.

---

## Como o código funciona por dentro

O pipeline é organizado em **5 agentes especializados** que rodam em sequência ou em paralelo:

```
Arquivo .patch
      │
      ▼
[Fase 1 — Sequencial]
01-change-analyzer    → Lê o diff, mapeia quais arquivos/APIs/testes são impactados
      │
      ▼
[Fase 2 — Paralelo]
02-code-reviewer  ──┐
03-doc-agent      ──┤ → Rodam ao mesmo tempo (3 threads simultâneas)
04-test-engineer  ──┘
      │
      ▼
[Fase 3 — Sequencial]
05-validation-agent   → Consolida tudo e emite o veredito final
```

### O que cada agente faz de verdade

#### 01 — Change Analyzer (`core/analyzer/diff_parser.py`)
- Lê o arquivo `.patch` linha por linha
- Identifica quais arquivos foram adicionados/modificados/removidos
- Varre o repositório procurando quais testes importam os arquivos modificados
- Calcula o "blast radius" — o quanto essa mudança pode impactar o sistema

#### 02 — Code Reviewer (`core/orchestrator.py` + `core/agents/code_reviewer_agent.py`)
- Primeiro roda um **pré-filtro de regex** para pegar problemas óbvios (SQL injection hardcoded, credenciais expostas, `eval()`, etc.)
- Depois manda o conteúdo dos arquivos para o **IBM watsonx.ai** (modelo Llama 3.3 ou Granite) com um prompt especializado de Code Review
- O resultado do AI é o autoritativo — se o AI responder, substitui o regex
- Se o AI falhar, usa o regex como fallback (`basis: "fallback_regex"`)

#### 03 — Documentation Agent (`core/orchestrator.py`)
- Escaneia os docs (`docs/API.md`, `docs/ARCHITECTURE.md`) em busca de identificadores novos introduzidos pelo diff
- Se encontrar tokens novos que não estão na documentação, atualiza os arquivos automaticamente
- Não usa AI — é heurística pura (busca por tokens)

#### 04 — Test Engineer (`core/orchestrator.py` + `core/runner/test_runner.py`)
- Detecta se há arquivos TypeScript novos sem testes correspondentes → pede ao AI para gerar os testes
- Roda `npx jest --coverage --json` no diretório do app detectado
- Coleta métricas reais: testes passando, falhando, cobertura por arquivo
- Se testes falharem, roda um loop de auto-correção usando AI (até 3 tentativas)
- Pede ao AI um relatório narrativo dos resultados

#### 05 — Validation Agent (`core/orchestrator.py`)
- Consolida os resultados dos 4 agentes anteriores
- Verifica 4 quality gates: Review OK + Testes OK + Cobertura ≥ 90% + Docs sincronizados
- Calcula o `readiness_score` (média ponderada: 35% testes + 25% cobertura + 25% review + 15% docs)
- Pede ao AI para escrever o veredito final em linguagem natural

### A integração com IBM watsonx.ai (`core/bob_client.py`)

O módulo `bob_client.py` é o único ponto de contato com a IA. Ele:
1. Busca um token IAM da IBM Cloud usando a API Key
2. Guarda o token em cache (válido por 1 hora, renova automaticamente)
3. Manda o prompt para o endpoint `/ml/v1/text/generation` do watsonx.ai
4. Retorna o texto gerado

Todas as chamadas passam por esse módulo — se a IA mudar, só esse arquivo precisa ser alterado.

---

## Vantagens reais do código

### 1. Agnóstico ao domínio de negócio
O pipeline não sabe (e não precisa saber) se está analisando um sistema de pagamentos, reservas de hotel, e-commerce ou qualquer outro domínio. Desde que o projeto use Jest/npm e gere um arquivo diff, funciona.

### 2. Fallback sempre disponível
Nenhum agente quebra o pipeline. Se o watsonx.ai estiver indisponível, a revisão de código continua com as regras regex. O campo `basis: "fallback_regex"` no output informa que o AI não foi usado.

### 3. Paralelismo real
Os agentes 02, 03 e 04 rodam simultaneamente com `ThreadPoolExecutor`. Em um projeto real com muitos arquivos, isso reduz o tempo total significativamente.

### 4. Métricas reais, não simuladas
Os números de testes, cobertura e timing são **medidos de verdade**:
- `tests_executed: 52` → Jest realmente rodou 52 testes
- `coverage_percentage: 93.4%` → Istanbul mediu 93.4% de cobertura real
- `duration_seconds: 2.1` → cronometrado com `time.time()`

### 5. Detecção automática do app
Quando você passa `hotel-diff.patch`, o sistema detecta automaticamente que os arquivos pertencem a `hotel-app/` e roda os testes de lá. Não precisa configurar nada manualmente.

### 6. Arquitetura extensível
Cada agente é um método independente no `ChangeFlowOrchestrator`. Adicionar um novo agente (ex: um que verifica licenças de dependências) é só adicionar um novo método e incluí-lo no `execute_pipeline`.

---

## Limitações reais

### Limitações técnicas

| Limitação | Impacto | O que seria necessário para resolver |
|---|---|---|
| **Só funciona com Jest/npm** | Projetos Python (pytest), Java (JUnit), Go (go test) não são suportados | Criar runners específicos para cada ecossistema |
| **Testes detectados só com `*.test.ts`** | Projetos com `*.spec.ts`, `*.test.js` não têm os testes corretamente mapeados no impact analysis (mas ainda são executados) | Tornar o glob pattern configurável via `jest.config.js` |
| **Documentação só via `docs/API.md`** | Projetos com Swagger, OpenAPI YAML, Confluence ou Notion não têm docs sincronizadas | Parser de OpenAPI 3.x e integrações com plataformas de docs |
| **Diff precisa ser gerado manualmente** | Não há integração nativa com GitHub/GitLab webhooks | Endpoint HTTP para receber eventos de PR automaticamente |
| **Sem retry/circuit breaker no AI** | Se o watsonx.ai demorar ou falhar, cai direto no fallback sem tentar novamente | Implementar retry com backoff exponencial |
| **Demo server sem autenticação** | Qualquer pessoa com acesso à porta 8787 pode rodar o pipeline | JWT ou API Key no `demo_server.py` |

### Limitações conceituais

**O AI pode estar errado.** O watsonx.ai pode aprovar código com vulnerabilidade ou reprovar código correto. Por isso o "Human-in-the-Loop" é obrigatório — a decisão final sempre é do desenvolvedor.

**A análise de documentação é heurística, não semântica.** O agente 03 busca tokens (palavras) nos docs, não entende o significado. Um token novo chamado `PIX` pode estar já documentado com um nome diferente e o agente não vai perceber.

**O onboarding varre `node_modules`.** O agente 00 (onboarding) lista entrypoints do projeto mas acidentalmente inclui arquivos de dependências em `node_modules/`. Isso não quebra nada, mas polui o output.

---

## Em que contexto esse código é adequado

| Contexto | Adequado? | Por quê |
|---|---|---|
| Hackathon / prova de conceito | ✅ Muito adequado | É exatamente para isso que foi construído |
| Demo para cliente / investidor | ✅ Adequado | Funciona de verdade, métricas são reais |
| Projeto pessoal Node.js/TypeScript | ✅ Adequado com ressalvas | Funciona, mas sem integração automática com GitHub |
| Startup em estágio inicial | ⚠️ Parcialmente | Precisaria de autenticação e webhook antes de usar em produção |
| Empresa de médio/grande porte | ❌ Não adequado ainda | Faltam: multi-linguagem, integração CI/CD, persistência, autenticação, observabilidade |

---

## O que seria necessário para produção real

Se o objetivo for transformar esse projeto em um produto de mercado, as principais evoluções seriam:

1. **Webhook GitHub/GitLab** — receber eventos de PR automaticamente em vez de precisar de um `.patch` manual
2. **Runners multi-linguagem** — suporte a pytest, Maven, Gradle, go test
3. **Parser OpenAPI** — sincronizar documentação Swagger/OpenAPI além de Markdown
4. **Banco de dados** — persistir histórico de execuções em vez de sobrescrever `latest-pipeline-run.json`
5. **Autenticação** — proteger o `demo_server.py` com JWT ou OAuth
6. **Observabilidade** — logs estruturados, métricas Prometheus, tracing distribuído
7. **Retry e circuit breaker** — resiliência nas chamadas ao watsonx.ai
8. **Interface de configuração** — arquivo `changeflow.yaml` por projeto para customizar thresholds, runners e agentes

---

## Conclusão

O ChangeFlow prova um conceito real e valioso: **é possível automatizar 92% do trabalho de revisão de código com IA** e fazer isso de forma que os resultados sejam genuinamente úteis (não apenas simulados). O código funciona, os testes rodam de verdade, as métricas são medidas, e a IA gera análises reais.

As limitações existem e são honestas — é um MVP de hackathon, não um produto SaaS maduro. Mas a arquitetura está correta, os conceitos estão validados, e o caminho para evolução está claro.
