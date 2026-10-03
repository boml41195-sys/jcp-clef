"""
JCP MVP — Smoke Test
Valida que o ambiente está funcional antes de qualquer código de runtime ser escrito.
Executa: python JCP-application/runtime/smoke_test.py
"""
import os
import sys
import asyncio

# --- 1. Verificação de ambiente ---

def check_env():
    errors = []

    # Telemetria deve estar desligada
    if os.environ.get("ANONYMIZED_TELEMETRY", "true").lower() != "false":
        errors.append(
            "ANONYMIZED_TELEMETRY não está configurado como 'false'. "
            "Adicione ANONYMIZED_TELEMETRY=false ao seu .env antes de continuar."
        )

    # Python >= 3.11
    if sys.version_info < (3, 11):
        errors.append(f"Python 3.11+ exigido. Atual: {sys.version}")

    if errors:
        print("SMOKE TEST FALHOU — erros de ambiente:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)

    print("  ✓ Ambiente OK")
    print(f"  ✓ Python {sys.version}")
    print(f"  ✓ ANONYMIZED_TELEMETRY=false")


# --- 2. Verificação de imports ---

def check_imports():
    try:
        from browser_use.browser.session import BrowserSession
        print("  ✓ browser_use.browser.session importado")
    except ImportError as e:
        print(f"  ✗ Falha ao importar browser_use: {e}")
        print("    Execute: uv pip install -e '.[core]'")
        sys.exit(1)

    try:
        from browser_use.actor.page import PageActor
        print("  ✓ browser_use.actor.page importado")
    except ImportError as e:
        print(f"  ✗ Falha ao importar actor: {e}")
        sys.exit(1)


# --- 3. Verificação de LLM call counter ---

llm_call_count = 0

def patch_llm_providers():
    """Instrumenta os providers LLM para detectar chamadas acidentais."""
    try:
        import browser_use.llm.base as llm_base
        original_ainvoke = getattr(llm_base.BaseChatModel, 'ainvoke', None)
        if original_ainvoke:
            async def counted_ainvoke(self, *args, **kwargs):
                global llm_call_count
                llm_call_count += 1
                return await original_ainvoke(self, *args, **kwargs)
            llm_base.BaseChatModel.ainvoke = counted_ainvoke
            print("  ✓ Instrumentação de LLM ativa")
    except Exception as e:
        print(f"  ⚠ Não foi possível instrumentar LLM providers: {e}")
        print("    Prosseguindo sem instrumentação.")


# --- 4. Teste de navegação básica ---

async def test_browser_navigation():
    from browser_use.browser.session import BrowserSession

    session = None
    try:
        session = BrowserSession(headless=True)
        await session.start()
        print("  ✓ BrowserSession iniciada")

        page = await session.get_current_page()
        await page.goto("https://example.com")
        title = await page.title()
        assert "Example" in title, f"Título inesperado: {title}"
        print(f"  ✓ Navegação funcional (título: {title})")

        # Verificar que nenhum LLM foi chamado
        assert llm_call_count == 0, f"LLM foi chamado {llm_call_count} vez(es) inesperadamente!"
        print(f"  ✓ Zero chamadas LLM confirmadas (llm_calls={llm_call_count})")

    except Exception as e:
        print(f"  ✗ Erro de navegação: {e}")
        print(f"    Execute: playwright install chromium")
        raise
    finally:
        if session:
            await session.stop()
            print("  ✓ BrowserSession encerrada corretamente")


# --- Main ---

async def main():
    print("\n=== JCP MVP — Smoke Test ===\n")

    print("[1/4] Verificando ambiente...")
    check_env()

    print("\n[2/4] Verificando imports...")
    check_imports()

    print("\n[3/4] Instrumentando providers LLM...")
    patch_llm_providers()

    print("\n[4/4] Testando navegação...")
    await test_browser_navigation()

    print(f"\n{'='*40}")
    print(f"SMOKE TEST OK — llm_calls={llm_call_count}")
    print(f"{'='*40}\n")
    print("Próximo passo: implementar jcp/contracts/ e rodar os testes do Grupo A")
    print("Ver: JCP-application/specs/05-ACCEPTANCE-TESTS.md\n")


if __name__ == "__main__":
    asyncio.run(main())
