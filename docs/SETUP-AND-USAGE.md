# ChangeFlow — Guia de Configuração e Uso

> Como configurar, rodar e testar o ChangeFlow com qualquer projeto Node.js/TypeScript.

---

## O que é o ChangeFlow?

ChangeFlow é um pipeline de inteligência artificial que analisa automaticamente mudanças de código. Quando um desenvolvedor termina de escrever uma alteração, o ChangeFlow:

1. **Analisa o impacto** — quais arquivos, APIs e testes são afetados
2. **Revisa o código** — segurança, boas práticas e qualidade via IBM watsonx.ai
3. **Sincroniza a documentação** — atualiza arquivos de docs automaticamente
4. **Executa os testes** — roda a suíte de testes real e mede cobertura
5. **Emite um veredito** — aprova ou bloqueia o merge com score de 0-100

Tudo isso em menos de 2 minutos, com o desenvolvedor tomando apenas a decisão final de merge.

---

## Pré-requisitos

Antes de começar, você precisa ter instalado na sua máquina:

| Ferramenta | Versão mínima | Para que serve |
|---|---|---|
| **Python** | 3.10+ | Rodar o pipeline principal |
| **Node.js** | 18+ | Rodar os testes Jest |
| **npm** | 9+ | Instalar dependências do projeto testado |
| **Git** | qualquer | Gerar o arquivo diff |

---

## Estrutura do Repositório

```
changeflow/                        ← raiz do projeto
├── core/                          ← cérebro do pipeline (Python)
│   ├── orchestrator.py            ← coordena todos os agentes
│   ├── bob_client.py              ← integração com IBM watsonx.ai
│   ├── analyzer/diff_parser.py    ← lê e interpreta o arquivo diff
│   └── runner/test_runner.py      ← executa Jest e coleta resultados
│
├── benchmarks/                    ← arquivos de entrada e saída
│   ├── sample-diff.patch          ← exemplo de diff (pagamentos)
│   ├── hotel-diff.patch           ← exemplo de diff (hotel)
│   └── latest-pipeline-run.json  ← resultado da última execução
│
├── sample-app/                    ← app de demonstração (pagamentos)
├── hotel-app/                     ← app de demonstração (hotel)
│
├── dashboard/                     ← interface visual React
├── .bob/agents/                   ← personas dos agentes de IA
└── .env                           ← suas credenciais (nunca commitar!)
```

---

## Passo 1 — Credenciais IBM watsonx.ai

### 1.1 Criar o arquivo `.env`

Na raiz do projeto, copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Abra o `.env` e preencha com suas credenciais reais:

```
IBM_CLOUD_API_KEY=sua_api_key_aqui
WATSONX_PROJECT_ID=seu_project_id_aqui
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=meta-llama/llama-3-3-70b-instruct
```

### 1.2 Onde obter cada valor

| Variável | Onde obter |
|---|---|
| `IBM_CLOUD_API_KEY` | [cloud.ibm.com/iam/apikeys](https://cloud.ibm.com/iam/apikeys) → **Create an IBM Cloud API key** |
| `WATSONX_PROJECT_ID` | [dataplatform.cloud.ibm.com](https://dataplatform.cloud.ibm.com) → seu projeto → aba **Manage** → **General** → **Project ID** |
| `WATSONX_URL` | Geralmente `https://us-south.ml.cloud.ibm.com` (Dallas). Ajuste se sua conta estiver em outra região |
| `WATSONX_MODEL_ID` | Use `meta-llama/llama-3-3-70b-instruct` — disponível na maioria das contas de hackathon |

> ⚠️ **NUNCA** commite o arquivo `.env` no Git. Ele já está no `.gitignore`.

### 1.3 Verificar que as credenciais funcionam

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 core/bob_client.py
```

Saída esperada:
```
=== Bob AI Client Smoke Test ===
[complete()] → 'Hello from watsonx'
Smoke test PASSED ✓
```

---

## Passo 2 — Configurar o Ambiente Python

O ChangeFlow usa **somente a biblioteca padrão do Python** — não precisa instalar nenhum pacote via pip:

```bash
python3 -m venv .venv
source .venv/bin/activate
# Não precisa de pip install — stdlib apenas
```

---

## Passo 3 — Adicionar Seu Projeto para Teste

### Onde colocar a pasta do projeto

Coloque a pasta do seu projeto diretamente na **raiz do repositório ChangeFlow**, no mesmo nível que `sample-app/` e `hotel-app/`:

```
changeflow/
├── sample-app/          ← já existe (demo de pagamentos)
├── hotel-app/           ← já existe (demo de hotel)
├── meu-projeto/         ← ← ← coloque aqui o seu projeto
└── core/
```

### Requisitos do projeto

Para que o ChangeFlow consiga testar seu projeto, ele precisa:

- ✅ Ter um `package.json` na raiz da pasta
- ✅ Ter o Jest instalado (`npm install` deve funcionar)
- ✅ Os testes devem rodar com `npx jest --coverage --json`
- ✅ Os arquivos de teste devem terminar em `.test.ts` ou `.test.js`

```bash
# Instale as dependências do seu projeto primeiro
cd meu-projeto
npm install
npx jest --coverage   # confirme que os testes passam
cd ..
```

---

## Passo 4 — O Arquivo Diff (o que é e como gerar)

### O que é um arquivo diff?

Imagine que você é um desenvolvedor e acabou de adicionar uma nova funcionalidade ao código. O **arquivo diff** é como uma "receita de mudanças" — ele descreve exatamente o que foi adicionado, removido ou modificado no código, linha por linha.

É o mesmo formato usado em Pull Requests do GitHub: as linhas em **verde** (com `+`) são o que foi adicionado, e as linhas em **vermelho** (com `-`) são o que foi removido.

**Exemplo visual de um diff:**

```diff
-  // versão antiga: sem validação de moeda
+  if (input.method === 'PIX' && input.currency !== 'BRL') {
+    throw new Error('PIX só aceita moeda BRL');
+  }
```

O ChangeFlow usa esse arquivo para saber **o que mudou** — sem ele, não sabe o que analisar.

### Como gerar o arquivo diff

**Opção A — A partir de um commit do Git:**

```bash
cd meu-projeto

# Mudanças ainda não commitadas (working tree)
git diff HEAD > ../benchmarks/meu-projeto-diff.patch

# Mudanças de um commit específico
git show abc1234 --format="" > ../benchmarks/meu-projeto-diff.patch

# Mudanças entre dois branches
git diff main..minha-feature > ../benchmarks/meu-projeto-diff.patch
```

**Opção B — A partir de um Pull Request no GitHub:**

1. Abra o PR no GitHub
2. Adicione `.diff` no final da URL do PR
   - Ex: `https://github.com/user/repo/pull/42` → `https://github.com/user/repo/pull/42.diff`
3. Salve o conteúdo como `benchmarks/meu-projeto-diff.patch`

**Opção C — Criar manualmente (para testes rápidos):**

Crie um arquivo `.patch` seguindo o formato:

```
diff --git a/meu-projeto/src/arquivo.ts b/meu-projeto/src/arquivo.ts
--- a/meu-projeto/src/arquivo.ts
+++ b/meu-projeto/src/arquivo.ts
@@ -10,6 +10,9 @@ export class MinhaClasse {
   metodoExistente() {
     return true;
   }
+
+  novoMetodo() {
+    return 'nova funcionalidade';
+  }
 }
```

### Onde salvar o arquivo diff

Salve sempre na pasta `benchmarks/`:

```
changeflow/
└── benchmarks/
    ├── sample-diff.patch          ← demo pagamentos (já existe)
    ├── hotel-diff.patch           ← demo hotel (já existe)
    └── meu-projeto-diff.patch     ← ← ← o seu arquivo diff
```

---

## Passo 5 — Rodar o Pipeline

```bash
source .venv/bin/activate
python3 core/orchestrator.py benchmarks/meu-projeto-diff.patch
```

O ChangeFlow vai detectar automaticamente que o diff pertence a `meu-projeto/` e vai executar os testes de lá.

**O que você vai ver no terminal:**

```
[orchestrator] Detected app directory: meu-projeto

=======================================================
🚀 Starting ChangeFlow AI Multi-Agent Pipeline (IBM Bob 2.0)
=======================================================

[00-onboarding] 🗺️  Scanning repository stack...
[01-change-analyzer] 🔍 Analyzing git diff...

⚡ Launching Parallel Subagents: Reviewer, Documentation, Test Engineer...
[02-code-reviewer] 🛡️  Running AI-powered security review...
[03-documentation-agent] 📚 Synchronizing docs...
[04-test-engineer] 🧪 Executing test suites...

🏁 Launching Quality Gatekeeper...
[05-validation-agent] ⚖️  Synthesizing results...

✨ Pipeline Finished in 45.2s! Status: READY_FOR_HUMAN_REVIEW
```

**O resultado completo é salvo em:**

```
benchmarks/latest-pipeline-run.json
```

---

## Passo 6 — Ver o Dashboard Visual (opcional)

Para visualizar os resultados de forma interativa:

**Terminal 1 — Servidor de API:**
```bash
source .venv/bin/activate
python3 core/demo_server.py
# Rodando em http://localhost:8787
```

**Terminal 2 — Dashboard React:**
```bash
cd dashboard
npm install
npm run dev
# Abra http://localhost:3000
```

No dashboard você pode:
- Ver o status de cada agente em tempo real
- Inspecionar os findings de segurança
- Ver a cobertura de testes por arquivo
- Aprovar ou rejeitar o merge (Human-in-the-Loop)

---

## Resumo Rápido (TL;DR)

```bash
# 1. Configurar credenciais
cp .env.example .env && nano .env

# 2. Ambiente Python
python3 -m venv .venv && source .venv/bin/activate

# 3. Instalar dependências do seu projeto
cd meu-projeto && npm install && cd ..

# 4. Gerar o diff da mudança que quer analisar
git -C meu-projeto diff HEAD > benchmarks/meu-diff.patch

# 5. Rodar o pipeline
python3 core/orchestrator.py benchmarks/meu-diff.patch

# 6. Ver o resultado
cat benchmarks/latest-pipeline-run.json
```

---

## Problemas Comuns

| Erro | Causa | Solução |
|---|---|---|
| `IBM_CLOUD_API_KEY not set` | `.env` não criado | `cp .env.example .env` e preencher |
| `IAM token failed (400)` | API Key com prefixo `ApiKey-` | Usar só o UUID, sem o prefixo |
| `project_id not associated with WML` | WML não associado ao projeto watsonx | Ir em Manage → Services → Associate → watsonx.ai Runtime |
| `node_modules not installed` | `npm install` não foi rodado | `cd meu-projeto && npm install` |
| `jest did not return parseable JSON` | Jest não suporta `--json` ou tem reporter customizado | Verificar `jest.config.js` do projeto |
| `Patch file not found` | Caminho errado para o .patch | Confirmar que o arquivo está em `benchmarks/` |
