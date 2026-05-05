# Documentation Update Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Comprehensively update the project's documentation using an App-Centric approach, reviewing the codebase to ensure all apps, architecture details, and guidelines are accurately documented without including dates or version numbers.

**Architecture:** We will create/update a `README.md` in each Django app. We will use a systematic approach: Analyze -> Draft Sub-components -> Finalize App README. Root files will then be updated to link to these.

**Tech Stack:** Markdown, SocratiCode (for codebase exploration).

---

### Task 1: Update Root Level Documentation

**Step 1: Cleanup `README.md`**
- Modify: `README.md`
- Action: Remove dates, version numbers, and update the "Apps del Proyecto" table to include all current apps.

**Step 2: Cleanup `ARCHITECTURE.md`**
- Modify: `ARCHITECTURE.md`
- Action: Remove dates, update directory structure tree, and ensure "Core Components" matches current app list.

---

### Task 2: Document `core` App (Granular)

**Step 1: Analyze `core` Models and Catalogs**
- Action: Review `core/models.py` to identify all base catalogs (Fabricante, Modelo, etc.).

**Step 2: Analyze `core` HTMX and UI Helpers**
- Action: Review `core/htmx.py`, `core/utils.py`, and `templates/cotton/`.

**Step 3: Write `core/README.md`**
- Create: `core/README.md`
- Content: Purpose, Catalog definitions, HTMX response patterns, and Cotton component usage.

---

### Task 3: Document `colaboradores` App (Granular)

**Step 1: Analyze Custom User Model**
- Action: Review `colaboradores/models.py` (Colaborador model, soft-delete logic).

**Step 2: Analyze Admin and Forms**
- Action: Review `colaboradores/admin.py` and `colaboradores/forms.py`.

**Step 3: Write `colaboradores/README.md`**
- Create: `colaboradores/README.md`
- Content: User model details, soft-delete implementation, and permissions/roles overview.

---

### Task 4: Document `dispositivos` App (Granular)

**Step 1: Map Polymorphic Hierarchy**
- Action: Review `dispositivos/models.py` to document the Dispositivo -> Specialized Model relationship.

**Step 2: Document Services and Signals**
- Action: Review `dispositivos/services.py` and `dispositivos/signals.py` for traceability and auto-ID logic.

**Step 3: Write `dispositivos/README.md`**
- Create: `dispositivos/README.md`
- Content: Model hierarchy, DispositivoFactory usage, traceability flow, and QR generation.

---

### Task 5: Document `actas` App (Granular)

**Step 1: Document Legal Flow**
- Action: Review `actas/services.py` and `actas/models.py` (Acta, FolioCounter).

**Step 2: Document PDF and Signature Integration**
- Action: Review `actas/playwright_browser.py` and pyHanko usage in services.

**Step 3: Write `actas/README.md`**
- Create: `actas/README.md`
- Content: Acta types, PDF generation lifecycle, digital signature configuration, and folio management.

---

### Task 6: Document `dashboard` and `suministros` (Granular)

**Step 1: Analyze Dashboard Metrics**
- Action: Review `dashboard/services.py` and filters.

**Step 2: Analyze Suministros Logic**
- Action: Review `suministros/models.py` and compatibility logic.

**Step 3: Write `dashboard/README.md` and `suministros/README.md`**
- Create: `dashboard/README.md`, `suministros/README.md`.

---

### Task 7: Final Polish of Central Docs

**Step 1: Update `docs/ARQUITECTURA_TECNICA.md`**
- Action: Align technical patterns with the new app READMEs and remove dates.

**Step 2: Update `docs/STYLE_GUIDE.md`**
- Action: Ensure HTMX/Alpine/Tailwind guidelines are up to date with project conventions.
