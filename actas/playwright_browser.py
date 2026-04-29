"""
Pool híbrido de instancias Chromium para generación de PDFs vía Playwright.

Estrategia: on-demand con TTL y tamaño máximo configurable.
- Las instancias se reutilizan mientras no excedan el TTL.
- Tamaño máximo del pool evita memory bombs bajo carga concurrente.
- Sin estado compartido entre requests (cada página es independiente).
"""

import time
import logging
from django.conf import settings

logger = logging.getLogger('actas')

_browser_pool = []          # instancias activas de Browser
_last_used_timestamps = []  # timestamps para TTL
_pool_lock_acquired = False


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

    # 1. Limpiar instancias expiradas (TTL vencido)
    for i in reversed(range(len(_browser_pool))):
        if now - _last_used_timestamps[i] > TTL:
            logger.info(f"Cerrando instancia Chromium expirada (TTL={TTL}s)")
            try:
                _browser_pool[i].close()
            except Exception as e:
                logger.warning(f"Error al cerrar browser expirado: {e}")
            del _browser_pool[i]
            del _last_used_timestamps[i]

    # 2. Reutilizar si hay instancia disponible
    if _browser_pool:
        _last_used_timestamps[-1] = now
        return _browser_pool[-1]

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
        old = _browser_pool.pop(0)
        _last_used_timestamps.pop(0)
        logger.info(f"Pool lleno ({MAX_POOL}), cerrando instancia más antigua")
        try:
            old.close()
        except Exception as e:
            logger.warning(f"Error al cerrar browser desplazado: {e}")

    _browser_pool.append(browser)
    _last_used_timestamps.append(now)
    logger.info(f"Pool Chromium: {len(_browser_pool)}/{MAX_POOL} instancias activas")
    return browser


def shutdown_pool():
    """Cierra todas las instancias del pool. Útil en tests y al apagar la app."""
    global _browser_pool, _last_used_timestamps
    logger.info(f"Cerrando pool de {len(_browser_pool)} instancias Chromium...")
    for browser in _browser_pool:
        try:
            browser.close()
        except Exception as e:
            logger.warning(f"Error al cerrar browser durante shutdown: {e}")
    _browser_pool.clear()
    _last_used_timestamps.clear()
