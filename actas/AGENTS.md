# actas — AGENTS.md

## OVERVIEW
Generación de actas legales (ENTREGA, DEVOLUCIÓN, DESTRUCCIÓN) con firma digital, folios correlativos y exportación PDF vía Playwright/Chromium.

## STRUCTURE
```
actas/
├── models.py              # Acta, FirmaActa, FolioSequence
├── services.py            # ~400 líneas — ActaService, ActaPDFService (COMPLEJO)
├── views.py               # CRUD actas + firma + descarga PDF
├── forms.py               # Formularios de acta
├── urls.py                # Names: acta_list, acta_firmar, acta_pdf, etc.
├── templates/actas/
│   ├── acta_*.html        # Templates de acta
│   └── partials/          # HTMX partials
├── tests/                 # Tests de servicio y flujo legal
└── migrations/
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Crear acta | `actas/services.py` | `ActaService.crear_acta()` — lógica legal compleja |
| Generar PDF | `actas/services.py` | `ActaPDFService` — Playwright render HTML→PDF |
| Firmar digitalmente | `actas/views.py` | `acta_firmar` — valida y guarda firma |
| Folio correlativo | `actas/models.py` | `FolioSequence` — secuencia atómica |
| Descargar PDF | `actas/views.py` | `acta_pdf` — devuelve archivo firmado |
| Inmutabilidad | `actas/tests/` | Tests verifican que acta firmada no se modifica |

## CONVENTIONS
- **Service layer**: Toda la lógica legal va en `services.py`, NO en views
- **Folio**: Secuencia atómica por tipo de acta (ENTREGA, DEVOLUCIÓN, DESTRUCCIÓN)
- **PDF**: Renderizado HTML con Playwright/Chromium, firma con pyHanko
- **Inmutabilidad**: Una vez firmada, la acta no puede modificarse (ValidationError)
- **Transacciones**: Creación de acta + folio dentro de `transaction.atomic()`

## ANTI-PATTERNS
- **NUNCA** poner lógica de generación de acta en views — usar `ActaService`
- **NUNCA** modificar una acta ya firmada — diseñado como inmutable
- **NUNCA** omitir `transaction.atomic()` en creación de acta (involucra ≥2 modelos)
- **NUNCA** generar folios manualmente — siempre usar `FolioSequence.next_folio()`

## COMPLEXITY NOTES
- `services.py` es el segundo archivo más complejo del proyecto (~400 líneas). Monitorear crecimiento; considerar dividir en `acta_service.py` y `pdf_service.py` si supera 500 líneas.
