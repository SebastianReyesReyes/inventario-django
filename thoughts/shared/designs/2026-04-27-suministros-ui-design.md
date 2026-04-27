---
date: 2026-04-27
topic: "Suministros UI Module"
status: draft
---

## Problem Statement

IT departments manage consumables alongside fixed assets, but the `suministros` app — despite having robust backend models for stock tracking, movements, low-stock alerts, and device-model compatibility — has no user interface. End users cannot view supplies, register stock movements, or receive low-stock warnings through the application.

## Constraints

- **Must reuse existing stack**: HTMX + Alpine.js + Tailwind CSS + `django-cotton`
- **Must follow URL naming convention**: `[model_name]_[action]` (e.g., `suministro_list`, `movimiento_create`) — breaking this breaks `{% render_actions %}`
- **Must use `BaseStyledForm`** for visual consistency
- **Must use `core/htmx.py` helpers** for HTMX responses (`htmx_trigger_response`, `htmx_render_or_redirect`)
- **Must respect existing permission groups**: `Técnicos` register movements, `Administradores` manage catalog, `Auditores` read-only
- **Must not duplicate backend logic** — services in `suministros/services.py` already handle atomicity and business rules
- **Must be compatible with existing dashboard** — low-stock alerts should feed into dashboard widgets
- **Soft-delete pattern** — supplies should deactivate, not delete, to preserve movement history

## Approach

**Chosen approach: HTMX-driven CRUD with inline stock movement modals**

The supply list view will be the hub. Users see supplies with color-coded stock badges. Clicking "Registrar Movimiento" opens a modal HTMX form. Successful movements trigger `HX-Trigger` to refresh the list and show a toast. This mirrors the existing dispositivos assignment flow, ensuring UX consistency.

**Alternatives considered:**
- *Dedicated "Stock Movements" page*: Rejected because inventory operations are contextual — users want to adjust stock while looking at the item. A separate page adds clicks and cognitive load.
- *Full-page form for movements*: Rejected because it breaks the HTMX partial-update pattern established across the rest of the app. Modals keep the user in context.

## Architecture

**Layered within existing Django app structure:**

```
suministros/
├── views.py          # New: CBVs for list, CRUD, movement modal
├── urls.py           # New: activate commented routes
├── services.py       # Existing: no changes needed
├── forms.py          # Existing: no changes needed
└── templates/
    └── suministros/
        ├── suministro_list.html      # Grid/table with stock badges
        ├── suministro_form.html      # Create/edit (full page)
        ├── suministro_detail.html    # Detail + movement history
        ├── partials/
        │   ├── _suministro_row.html  # HTMX-swapable table row
        │   ├── _movimiento_modal.html # Modal form for stock movement
        │   └── _stock_badge.html     # Color-coded stock indicator
        └── components/
            └── low_stock_alert.html  # Dashboard widget component
```

**Key decision:** Reuse `core/templates/cotton/` components (`page_header`, `search_input`, `glass_panel`, `btn_primary`, `table_base`) to maintain visual consistency without duplicating markup.

## Components

### 1. `SuministroListView` (CBV)
- Inherits from `LoginRequiredMixin` + `PermissionRequiredMixin`
- Queryset: `Suministro.objects.select_related('categoria').with_stock_level()` (assuming we add a custom manager method, or annotate)
- Supports search (name, SKU) and filter by category via HTMX
- Pagination: 20 items per page (addresses the 479KB list problem seen in dispositivos)

### 2. `SuministroCreateView` / `SuministroUpdateView` (CBV)
- Use existing `SuministroForm` from `suministros/forms.py`
- Full-page form (not modal) — supply catalog management is less frequent and benefits from dedicated focus
- Success: redirect to `suministro_list` with `HX-Trigger: showToast`

### 3. `MovimientoStockCreateView` (FBV or CBV)
- HTMX-only endpoint
- Uses existing `MovimientoStockForm`
- On POST: calls `suministros.services.registrar_movimiento()` (already atomic)
- Returns: `204 No Content` + `HX-Trigger: {"refreshSuministroList": "", "showToast": {"message": "Movimiento registrado", "type": "success"}}`
- On validation error: returns rendered modal HTML with errors

### 4. `SuministroDetailView` (CBV)
- Displays supply details + paginated movement history (last 20 movements)
- Uses `prefetch_related` on `movimientos` or separate HTMX-paginated partial

### 5. `SuministroDeleteView` (CBV)
- Soft delete: set `esta_activo = False` (follow `Colaborador` pattern)
- On delete: check if stock is zero; if not, warn user that history remains but item is hidden from default lists

### 6. Stock Badge Component (`_stock_badge.html`)
- Green: stock > umbral_critico
- Yellow: stock <= umbral_critico and > 0
- Red: stock == 0
- Uses Tailwind color classes, no inline styles

## Data Flow

### Viewing Supplies (GET /suministros/)
1. User navigates to supply list
2. `SuministroListView` renders full page with initial queryset
3. Table body is a Cotton component; each row is a partial template
4. Search/filter triggers HTMX GET to same URL with query params
5. View detects HTMX request and returns only `_suministro_table.html` partial (using `htmx_render_or_redirect` pattern)

### Registering a Movement (POST /suministros/movimiento/nuevo/)
1. User clicks "Registrar Movimiento" on a supply row
2. HTMX GET loads `_movimiento_modal.html` into modal container
3. User fills form (tipo: ENTRADA/SALIDA/AJUSTE, cantidad, observaciones)
4. HTMX POST to `movimiento_create`
5. `registrar_movimiento()` service validates stock sufficiency for SALIDA, creates `MovimientoStock`, updates `Suministro.stock_actual`
6. View returns `204` + `HX-Trigger` to refresh list and show toast
7. Alpine.js listens for `showToast` and displays notification
8. HTMX on list container listens for `refreshSuministroList` and re-fetches list

### Low-Stock Alert Flow
1. `SuministroQuerySet` method `bajo_stock()` returns supplies where `stock_actual <= umbral_critico`
2. Dashboard context processor (or dedicated view context) queries this
3. Renders `low_stock_alert.html` Cotton component in dashboard sidebar
4. Badge on main navigation updates via HTMX on page load or polling

## Error Handling

**Validation errors in movement form**
- Return modal HTML with field errors + `HX-Reswap: innerHTML`
- Do not close modal; let user correct input

**Insufficient stock for SALIDA**
- Service raises `ValidationError` with message "Stock insuficiente para salida"
- View catches and returns modal with error on `cantidad` field

**ProtectedError / IntegrityError on delete**
- Return HTML of confirmation modal with error message + `HX-Trigger: showToast` with error type (per AGENTS.md convention)

**Permission denied**
- Standard Django 403 response; middleware handles redirect to login or forbidden page

## Testing Strategy

**Unit tests for views**
- Test list view queryset includes `select_related`
- Test movement view calls service layer (mock `registrar_movimiento`)
- Test permission checks: `Técnicos` can POST movements, `Auditores` cannot

**Integration tests**
- Full flow: create supply → register entrada → verify stock updated → register salida → verify stock decreased → attempt oversale → verify error
- Test HTMX partial response vs full page response based on `HX-Request` header

**E2E tests (Playwright)**
- Navigate to supply list → verify stock badges render
- Open movement modal → submit form → verify toast appears and stock badge updates
- Filter by category → verify URL params and results

**Coverage target**: 80%+ for new view code (bring `suministros` app from ~20% to 80%+)

## Open Questions

1. **Should supply movements require linking to a `Dispositivo`?** The backend model `MovimientoStock` has a nullable FK to `Dispositivo`. The design assumes generic stock movements, but if the business requires every mouse/keyboard exit to be tied to a device assignment, the movement form needs a device search field. Assuming generic movements for now.

2. **Should low-stock alerts trigger email/notification, or just UI badges?** The backend has no notification system yet. Sticking to UI-only alerts to avoid scope creep.
