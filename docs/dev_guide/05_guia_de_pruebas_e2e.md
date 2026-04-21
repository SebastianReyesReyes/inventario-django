# Guía de Pruebas: E2E y Pruebas Unitarias

La confianza de la "Consola de Precisión" recae en el aseguramiento de sus lógicas más complicadas, es por ello que todo módulo final requiere obligatoriamente someterse a *Testing Automatizado*.

## Estrategia de Testing (Pirámide de Pruebas)

### 1. Pruebas Unitarias Estándar (`pytest`)
Nos aseguran el correcto funcionamiento de las funciones y métodos aislados dentro de Django, especialmente en los servicios dedicados:
* **Ubicación:** Cada app contiene una carpeta `tests/`.
* **Correr en Local:** Verifica estar en tu entorno activado e instalar tus paquetes y ejecuta: `pytest`.
* **Factory Boy:** Se desaconsejan completamente los "Fixtures estáticos de JSON". Utilizaremos la inyección mediante `factory_boy` para construir entidades en nuestra BD de prueba de manera viva. 

### 2. Pruebas End-to-End Multimodelo (`Playwright`)
Las pruebas Unitarias no validan eventos del usuario (Cierres de un modal HTMX, cambios desencadenados por inputs Alpine.js). Utiliza herramientas asíncronas para comprobar validaciones End-To-End (E2E).

* **Organización:** Utiliza un directorio globalizado `tests_e2e/`.
* **Flujos de Vida Básicos E2E que Debes Comprobar:**
  1. Cración y edición con modal abierto (Comprobar que en el DOM se levanta el z-index de `.modal-dialog`).
  2. Funcionalidad de filtros y campos "Autocompletes" personalizados.
  3. Comprobar que en operaciones fallidas HTTP se inyecta y renderiza correctamente la respuesta de alerta `.alert-error` vía HTMX.

## Correr Pruebas Playwright (Ejemplo de Guía)
Si implementas pruebas E2E desde un terminal:

```bash
# Correr en formato Headed (Para inspección visual de errores)
pytest tests_e2e/ -v --headed --browser chromium
```

> [!TIP]
> Dado nuestro robusto Stack Tecnológico basado exclusivamente en SSR y renders parciales (HTMX), asegúrate siempre de esperar por los selectores utilizando Playwright, ya que HTMX tiene comportamientos instantáneos mediante Fetch, es crucial incluir comandos `.wait_for_selector('table.catalogo')` previendo demoras de renderizado natural del backend.
