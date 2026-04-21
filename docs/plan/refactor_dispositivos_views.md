# Plan de implementación: refactor de `dispositivos/views.py`

## Problema y enfoque
- `dispositivos/views.py` concentra múltiples responsabilidades (HTTP, reglas transaccionales, integración con actas, respuestas HTMX), lo que aumenta riesgo de regresión y dificulta mantenimiento.
- Se refactorizará de forma incremental: extraer lógica de negocio a servicios en `dispositivos/services.py`, mantener contratos externos (URLs, templates, eventos HX), y reforzar cobertura en puntos críticos antes y después de mover lógica.

## Alcance
- Refactorización enfocada en `dispositivos/views.py` (sin rediseñar todo el proyecto).

## Fases de implementación
1. **baseline-tests**
   - Levantar línea base de pruebas de `dispositivos` y dependencias directas (`actas` relacionadas con trazabilidad).
   - Identificar brechas de cobertura en flujos de asignar/reasignar/devolver y respuestas HTMX.

2. **map-contracts**
   - Inventariar contratos que no pueden cambiar: nombres de URL, templates renderizados, `HX-Trigger`, `HX-Redirect`, códigos HTTP y parámetros usados por formularios.
   - Documentar contratos en pruebas de regresión.

3. **extract-traceability-service**
   - Crear/expandir servicio de trazabilidad en `dispositivos/services.py` para:
     - asignar dispositivo
     - reasignar dispositivo
     - devolver dispositivo
     - entregar accesorio
   - Consolidar manejo atómico y creación opcional de acta en métodos de servicio.

4. **extract-view-helpers**
   - Extraer helpers internos para reducir duplicación en views:
     - detección de request HTMX
     - construcción de respuesta HTMX de éxito (template + trigger)
     - resolución de estados estándar (`Asignado`, `Disponible`, `En Reparación`)

5. **refactor-views**
   - Refactorizar `dispositivos/views.py` para que cada view:
     - valide request/form
     - delegue lógica de negocio al servicio
     - preserve exactamente respuesta HTTP/HTMX esperada
   - Mantener intactos `urls.py` y nombres de rutas.

6. **tests-regression**
   - Ampliar tests en `dispositivos/tests/` para cubrir contratos de vistas HTMX y flujos transaccionales.
   - Agregar casos para:
     - triggers esperados (`asignacion-saved`, `accesorio-saved`)
     - creación opcional de acta en asignación/reasignación/devolución
     - estados y propietario final del dispositivo

7. **cross-app-check**
   - Verificar compatibilidad con `actas/services.py`, templates en `core`, `dashboard` y `colaboradores`, y enlaces `dispositivos:*`.
   - Confirmar que no se rompe navegación ni sideovers HTMX.

8. **final-validation**
   - Ejecutar suite de pruebas relevante completa y ajustar regresiones.
   - Dejar el archivo de views más legible sin cambiar comportamiento observable.

## Restricciones y criterios de seguridad
- No cambiar nombres de URL `dispositivos:*`.
- No cambiar contratos HTMX (status, headers, templates).
- Priorizar cambios pequeños por lote para aislar regresiones.
- Mantener lógica de negocio en service layer (no mover flujo principal a signals).
