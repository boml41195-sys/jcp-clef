# 01 — Requisitos de máquina e ambiente

**JCP-application | browser-use + CLEF | PoC**

Esta especificação descreve o que precisa estar instalado e configurado na máquina antes de executar qualquer linha do runtime JCP.
Os requisitos derivam diretamente do `pyproject.toml` do browser-use-jcp (commit `7be96ed8`) e das decisões de arquitetura do MVP.

---

## 1. Sistema operacional

| SO | Status |
|---|---|
| Linux x86_64 | **Suportado** (ambiente recomendado para CI) |
| macOS arm64 / x86_64 | **Suportado** |
| Windows x86_64 | **Suportado** com ressalvas (ver §6) |

---

## 2. Python

| Requisito | Valor |
|---|---|
| Versão mínima | **3.11** |
| Versão máxima | **< 4.0** |
| Arquivo de versão | `.python-version` no fork (`3.13`) |
| Gerenciador recomendado | `uv` (já usado no upstream) |

**Atenção:** `browser-use-core==0.13.3` distribui wheels para plataformas específicas (darwin arm64, darwin x86_64, linux x86_64, linux aarch64, win32 AMD64). Não há wheel para Windows ARM.

---

## 3. Dependências Python (fixadas no pyproject.toml)

### Core obrigatório para o MVP

| Pacote | Versão | Para que serve no MVP |
|---|---|---|
| `browser-use` | 0.13.10 | Runtime de navegação |
| `browser-use-core` | 0.13.3 | Extensão nativa de browser |
| `pydantic` | 2.13.5 | Modelos de contrato |
| `pydantic-settings` | 2.15.0 | Configuração via env vars |
| `httpx` | 0.28.1 | Chamada REST ao Workers AI (CLEF) |
| `python-dotenv` | 1.2.2 | Carregar `.env` com credenciais |
| `anyio` | 4.12.1 | Async runtime |
| `cdp-use` | 1.4.5 | CDP para BrowserSession |
| `pypdf` | 6.16.2 | Leitura de PDF (opcional no MVP) |

### Dependências que o Browser Use puxa e que o MVP **não usa ativamente**

> Estas entram no ambiente mas o runtime JCP não deve chamá-las no caminho estável.
> Instrumentar para detectar chamadas acidentais.

| Pacote | Risco no MVP |
|---|---|
| `openai==2.26.0` | Não chamar no caminho determinístico |
| `anthropic>=0.76.0` | Idem |
| `google-genai==1.65.0` | Idem |
| `groq==1.0.0` | Idem |
| `ollama==0.6.1` | Idem |

**Regra:** o MVP instrumenta todos os providers LLM para contar chamadas. `llm_calls > 0` no caminho determinístico é falha de teste.

---

## 4. Navegador

| Requisito | Valor |
|---|---|
| Engine | **Chromium** (via Playwright, gerenciado pelo browser-use) |
| Instalação | `playwright install chromium` após instalar dependências |
| Versão | Gerenciada pelo Playwright compatível com a versão do pacote |
| Modo headless | Sim para CI; headful opcional para debug |

**Não usar Firefox ou WebKit no MVP** — o fork foi inspecionado somente com Chromium.

---

## 5. Credenciais e variáveis de ambiente

```env
# Obrigatório para o adapter CLEF
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=

# Modelo CLEF (não alterar sem avaliação)
CLEF_MODEL=@cf/cloudflare/clef
CLEF_FLASH_MODEL=@cf/cloudflare/clef-flash

# Opcional — controla qual modelo generativo o Agent usa em descoberta/reparo
# Não é chamado no caminho estável
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Controla comportamento do runtime JCP
JCP_ENV=development          # development | production
JCP_LOG_LEVEL=DEBUG
JCP_BROWSER_HEADLESS=true
JCP_LLM_CALL_BUDGET=0        # 0 = zero tolerância no caminho determinístico
```

**Regra:** nenhuma credencial pode estar hardcoded no código. O adapter CLEF lê somente do ambiente.

---

## 6. Ressalvas específicas por plataforma

### Windows
- `pyobjc` não é instalado (macOS-only) — ok, não afeta o MVP
- `screeninfo` é instalado para resolução de tela — verificar se Playwright headless dispensa
- Caminhos com espaço no diretório (como `LOPS OS DEFINITIVO`) podem causar problemas em scripts de instalação. Recomenda-se clonar o repo para um caminho sem espaços no ambiente de desenvolvimento
- Line endings CRLF: o `.gitattributes` do fork configura LF; manter essa configuração

### Linux CI
- Dependências de sistema para Chromium headless: `libnss3`, `libatk1.0-0`, `libgbm1` (instaladas pelo `playwright install-deps`)

---

## 7. Checklist de setup (executar nesta ordem)

```bash
# 1. Clonar o fork fixado
git clone https://github.com/boml41195-sys/jcp-clef.git
cd jcp-clef

# 2. Criar ambiente virtual
uv venv .venv
source .venv/bin/activate  # Linux/macOS
# .\.venv\Scripts\activate  # Windows

# 3. Instalar dependências
uv pip install -e ".[core]"

# 4. Instalar Chromium
playwright install chromium

# 5. Configurar credenciais
cp .env.example .env
# Editar .env com CLOUDFLARE_ACCOUNT_ID e CLOUDFLARE_API_TOKEN

# 6. Smoke test
python -c "from browser_use.browser.session import BrowserSession; print('OK')"

# 7. Smoke test do Actor
python JCP-application/runtime/smoke_test.py
```

---

## 8. O que o smoke test deve provar

O arquivo `runtime/smoke_test.py` (a criar) deve:

1. Abrir BrowserSession com Chromium headless
2. Navegar para `https://example.com`
3. Usar `Actor.goto()` e `Actor.get_elements_by_css_selector()`
4. Confirmar que **nenhum cliente LLM foi chamado**
5. Fechar a sessão e liberar recursos
6. Imprimir: `SMOKE TEST OK — llm_calls=0`

Se qualquer etapa falhar antes do código JCP ser escrito, é problema de ambiente, não de implementação.

---

## 9. Versões de runtime a registrar no primeiro setup

O desenvolvedor deve registrar os valores reais após o setup:

```
Python version:      ___________
uv version:          ___________
Playwright version:  ___________
Chromium version:    ___________
OS:                  ___________
browser-use version: 0.13.10 (fixada)
browser-use commit:  7be96ed8bafa8dfe1eef228b59cf5c884b8b2431
```

Esses valores vão para o relatório de benchmark do MVP.
