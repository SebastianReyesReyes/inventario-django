# core — AGENTS.md

## OVERVIEW
Catálogos base, utilidades HTMX, templatetags reutilizables, templates base y componentes Cotton.

## STRUCTURE
```
core/
├── models.py              # Catálogos base (Fabricante, TipoDispositivo, EstadoDispositivo, etc.)
├── views.py               # CRUD catálogos + AJAX inline para modelos
├── forms.py               # BaseStyledForm (herencia obligatoria para forms globales)
├── htmx.py                # Helpers HTMX: htmx_trigger_response, htmx_render_or_redirect
├── templatetags/          # action_tags (render_actions), core_tags
├── templates/core/        # Templates base, partials HTMX
├── management/commands/   # Comandos personalizados (import_inventario.py ~539 líneas)
├── tests/                 # factories.py (canónico), test_models, test_views
└── migrations/
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Crear/actualizar catálogo | `core/views.py` | CRUD genérico con soft delete |
| Helper HTMX | `core/htmx.py` | Preferir `htmx_trigger_response` para mutaciones |
| Form base estilizado | `core/forms.py` | Heredar `BaseStyledForm` para consistencia Tailwind |
| URL action dinámica | `core/templatetags/action_tags.py` | Requiere naming `modelname_action` |
| Factory canónica | `core/tests/factories.py` | Guard `sys.modules["pytest"]` obligatorio |
| Importación masiva CSV | `core/management/commands/import_inventario.py` | Comando `import_devices` |

## CONVENTIONS
- **Soft delete**: Todos los modelos de catálogo usan `esta_activo` + `deleted_at`
- **URLs**: CRUD sigue `[model_name]_[action]` en minúsculas (ej. `tipodispositivo_create`)
- **Formularios**: Atributos HTMX/Alpine van en `__init__` del form/widget, no en templates
- **Templates base**: `base.html` carga Tailwind + Alpine + HTMX; bloques definidos para `content`, `extra_css`, `extra_js`

## ANTI-PATTERNS
- **NUNCA** modificar `core/htmx.py` para lógica de app específica — mantener genérico
- **NUNCA** usar `fields = '__all__'` en forms — listar explícitamente
- **NUNCA** hardcodear URLs en templates — siempre usar `{% url %}` o `reverse()`
