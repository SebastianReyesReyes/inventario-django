# Higiene de dependencias

Esta guía define cómo mantener `requirements.txt` liviano y útil para el proyecto.

## 1) Clasificación mínima

### Núcleo hoy
Dependencias con uso verificable en código o flujo actual (views, forms, templates, tests, comandos de operación).

### Opcional roadmap
Dependencias sin uso actual, pero con un caso de uso definido para el corto/mediano plazo.

### Quitar si no se usa
Dependencias instaladas por prueba o exploración que no tienen uso verificable ni ticket de adopción.

## 2) Regla de evidencia

Una dependencia se mantiene solo si cumple al menos una condición:
- Está usada en archivos del repo (imports, settings, templates, comandos), o
- Tiene un issue/ticket de roadmap con fecha y responsable.

Si no cumple ninguna, se elimina.

## 3) Cadencia de revisión

- Revisar dependencias cada **4-6 semanas**.
- En cada revisión:
  - identificar paquetes sin uso,
  - decidir `mantener / opcional / quitar`,
  - actualizar documentación afectada.

## 4) Reglas prácticas para este repo

- `django-debug-toolbar` puede mantenerse como herramienta de diagnóstico local.
- `django-imagekit` puede mantenerse como opcional si hay probabilidad real de flujo de escaneo/procesamiento de imágenes.
- Dependencias opcionales deben tener referencia en roadmap (issue o documento de planificación).

## 5) Checklist rápido antes de agregar una dependencia

1. ¿Resuelve una necesidad actual del proyecto?
2. ¿Existe una alternativa ya instalada que resuelva lo mismo?
3. ¿Está documentado dónde se usará?
4. ¿Tiene un plan de salida si no se adopta?

Si no puedes responder "sí" a (1) o (3), no la agregues a `requirements.txt` principal.
