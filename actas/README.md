# App Actas — Gestión Legal y Trazabilidad

## Propósito
La aplicación `actas` es el núcleo legal del sistema de inventario. Su función principal es documentar formalmente todos los movimientos de activos (equipos y suministros) mediante la generación de documentos legales (Actas) que aseguran la trazabilidad, responsabilidad y cumplimiento normativo.

## Flujo Legal y Tipos de Actas
El sistema soporta tres tipos fundamentales de documentos:

1.  **Acta de Entrega (`ENTREGA`)**: Documenta la asignación inicial de equipos (laptops, periféricos) a un colaborador.
2.  **Acta de Devolución (`DEVOLUCION`)**: Documenta el retorno de activos. Incluye campos críticos para el cumplimiento técnico como el **Estándar de Sanitización NIST SP 800-88** (Borrado lógico, criptográfico o destrucción física).
3.  **Acta de Entrega de Suministros (`ENTREGA_SUMINISTROS`)**: Documenta la salida de consumibles (teclados, mouse, tóners) con valorización económica (FIFO/Costo promedio).

### Roles Legales
- **Ministro de Fe**: Los administradores de obra o jefes de área actúan como ministros de fe en terreno para validar las entregas y devoluciones físicas.
- **Auditoría de Firma**: El sistema registra quién generó el acta (`creado_por`) y quién la validó legalmente (`firmada_por`).

## Ciclo de Vida del PDF (Playwright Integration)
La generación de documentos PDF corporativos utiliza un motor moderno basado en **Playwright/Chromium** para garantizar que el diseño visual sea idéntico en pantalla y en papel.

1.  **Renderizado HTML**: Se utiliza el motor de templates de Django (`acta_preview_content.html`) para construir el documento.
2.  **Conversión PDF**: `ActaPDFService` delega en Playwright para capturar el HTML y convertirlo a PDF con formato Carta (Letter) y márgenes técnicos específicos.
3.  **Optimización (Chromium Pool)**: `actas/playwright_browser.py` implementa un pool híbrido de instancias de Chromium con:
    -   **TTL (Time To Live)**: Las instancias se cierran tras un periodo de inactividad para liberar memoria.
    -   **Max Size**: Limita la cantidad de procesos concurrentes para evitar picos de consumo de recursos.
    -   **Thread-Safety**: Garantiza la generación segura en entornos multi-hilo.

## Firma Digital
El sistema implementa un modelo de firma en dos etapas:

-   **Actual (Audit Record)**: Firma electrónica interna. Al marcar un acta como "Firmada", el registro se vuelve **inmutable**. No se permiten modificaciones posteriores para preservar la integridad legal.
-   **Planificada (Criptográfica)**: El stack incluye `pyHanko` para la firma digital de PDFs con certificados X.509 (infraestructura lista en `requirements.txt` y `ARCHITECTURE.md`, pendiente de integración final en la capa de servicios).

## Gestión de Folios
Los folios son correlativos y únicos por año, siguiendo el estándar corporativo:
-   **Formato**: `ACT-YYYY-NNNN` (ej. `ACT-2024-0042`).
-   **Generación Atómica**: El método `save()` del modelo `Acta` calcula el siguiente número de forma segura.
-   **Resiliencia**: `ActaService.crear_acta()` incluye lógica de reintentos ante colisiones de folio para garantizar la consistencia en entornos de alta concurrencia.

## Seguridad e Inmutabilidad
-   **Blindaje Legal**: Una vez que un acta es marcada como `firmada=True`, el sistema lanza `ValidationError` ante cualquier intento de modificación.
-   **Anulación**:
    -   **Borradores**: Eliminación física permitida.
    -   **Firmadas**: Requieren **Anulación Lógica**. Se mantiene el registro para auditoría, pero se marca como anulada con un **motivo obligatorio** de al menos 10 caracteres y registro de quién ejecutó la acción.

## Estructura de Archivos Clave
-   `models.py`: Definición de `Acta` y lógica de folios.
-   `services.py`: Capa de negocio (Creación, Firma, Anulación y PDF).
-   `playwright_browser.py`: Gestión del pool de Chromium.
-   `templates/actas/playwright/`: Wrappers específicos para el renderizado PDF.
