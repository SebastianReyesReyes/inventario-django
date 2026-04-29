"""
Pool híbrido de instancias Chromium para generación de PDFs vía Playwright.

Estrategia: on-demand con TTL y tamaño máximo configurable.
- Las instancias se reutilizan mientras no excedan el TTL.
- Tamaño máximo del pool evita memory bombs bajo carga concurrente.
- Sin estado compartido entre requests (cada página es independiente).
- Thread-safe mediante threading.Lock().
"""

import time
import logging
import threading
from django.conf import settings

logger = logging.getLogger('actas')

_browser_pool = []          # tuples of (Browser, Playwright)
_last_used_timestamps = []  # timestamps para TTL
_pool_lock = threading.Lock()


def _close_browser_instance(index):
    """Cierra un browser y su instancia Playwright asociada."""
    global _browser_pool, _last_used_timestamps
    browser, pw = _browser_pool[index]
    try:
        browser.close()
    except Exception as e:
        logger.warning(f"Error al cerrar browser: {e}")
    try:
        pw.stop()
    except Exception as e:
        logger.warning(f"Error al detener Playwright: {e}")
    del _browser_pool[index]
    del _last_used_timestamps[index]


def get_browser():
    """
    Obtiene una instancia de Chromium del pool o crea una nueva.

    Returns:
        playwright.sync_api.Browser: Instancia headless de Chromium.

    Raises:
        RuntimeError: Si Playwright no está instalado o Chromium falla al lanzar.
    """
    global _browser_pool, _last_used_timestamps

    TTL = getattr(settings, 'PLAYWRIGHT_BROWSER_TTL', 120)
    MAX_POOL = getattr(settings, 'PLAYWRIGHT_POOL_MAX_SIZE', 2)
    now = time.time()

    with _pool_lock:
        # 1. Limpiar instancias expiradas (TTL vencido)
        for i in reversed(range(len(_browser_pool))):
            if now - _last_used_timestamps[i] > TTL:
                logger.info(f"Cerrando instancia Chromium expirada (TTL={TTL}s)")
                _close_browser_instance(i)

        # 2. Reutilizar si hay instancia disponible
        if _browser_pool:
            _last_used_timestamps[-1] = now
            return _browser_pool[-1][0]

        # 3. Crear nueva instancia
        logger.info("Lanzando nueva instancia de Chromium para Playwright...")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright no está instalado. Ejecutá: pip install playwright && playwright install chromium"
            )

        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-gpu',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--font-render-hinting=none',
            ],
        )

        # 4. Respetar tamaño máximo del pool
        if len(_browser_pool) >= MAX_POOL:
            _close_browser_instance(0)
            logger.info(f"Pool lleno ({MAX_POOL}), cerrando instancia más antigua")

        _browser_pool.append((browser, pw))
        _last_used_timestamps.append(now)
        logger.info(f"Pool Chromium: {len(_browser_pool)}/{MAX_POOL} instancias activas")
        return browser


def shutdown_pool():
    """Cierra todas las instancias del pool. Útil en tests y al apagar la app."""
    global _browser_pool, _last_used_timestamps
    logger.info(f"Cerrando pool de {len(_browser_pool)} instancias Chromium...")
    with _pool_lock:
        for i in reversed(range(len(_browser_pool))):
            _close_browser_instance(i)
