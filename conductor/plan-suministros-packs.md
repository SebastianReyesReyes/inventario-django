# Suministros Dashboard Packs Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a 'Consumable Packs' grouping logic in the `DashboardMetricsService` to visually group supplies by their compatible hardware models, and add a 'Duración Estimada' field to `Suministro` for consumption alerts.

**Architecture:** 
1. Modify `Suministro` model to add `duracion_estimada_dias` (Gonzalo's requirement).
2. Create `get_suministros_packs` in `DashboardMetricsService`. It will fetch active supplies, prefetch `modelos_compatibles`, and use `frozenset` of model IDs to group them into "Packs".
3. Create a helper method to generate a human-readable title for the Pack based on the models.

**Tech Stack:** Python, Django ORM, HTMX, Tailwind.

---

### Task 1: Update Suministro Model (Consumo Estimado)

**Files:**
- Modify: `suministros/models.py`

**Step 1: Add field to Suministro model**

Modify the `Suministro` class in `suministros/models.py`:

```python
    duracion_estimada_dias = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Días estimados que debería durar este insumo. Usado para alertas de consumo inusual."
    )
```

**Step 2: Generate Migration**

Run: `python manage.py makemigrations suministros`

**Step 3: Apply Migration**

Run: `python manage.py migrate suministros`

---

### Task 2: Implement `get_suministros_packs` Logic

**Files:**
- Modify: `dashboard/services.py`

**Step 1: Import Suministro**

Ensure `from suministros.models import Suministro` is imported in `dashboard/services.py`.

**Step 2: Implement Pack grouping method**

Add the following classmethod to `DashboardMetricsService`:

```python
    @classmethod
    def get_suministros_packs(cls):
        """
        Agrupa suministros activos por fingerprint de modelos_compatibles.
        """
        # 1. Fetch activos con prefetch para evitar N+1
        suministros = Suministro.objects.activos().prefetch_related('modelos_compatibles')
        
        packs_dict = {}
        individuales = []
        
        for s in suministros:
            # 2. Generar fingerprint basado en IDs de modelos compatibles
            modelos = list(s.modelos_compatibles.all())
            
            if not modelos:
                # Si no tiene modelos compatibles, va suelto
                individuales.append({
                    'id': s.id,
                    'nombre': s.nombre,
                    'stock_actual': s.stock_actual,
                    'stock_minimo': s.stock_minimo,
                    'semaforo': cls._semaforo_suministro(s.stock_actual, s.stock_minimo),
                    'is_pack': False,
                    'categoria_id': s.categoria_id
                })
                continue
                
            model_ids = frozenset([m.id for m in modelos])
            
            if model_ids not in packs_dict:
                # Nombres de modelos para el título del pack
                model_names = [m.nombre for m in modelos]
                label = f"Compatible con: {', '.join(model_names[:2])}"
                if len(model_names) > 2:
                    label += f" y {len(model_names)-2} más"
                    
                packs_dict[model_ids] = {
                    'pack_label': label,
                    'modelos_compatibles': model_names,
                    'items': [],
                    'is_pack': True,
                    'categoria_id': s.categoria_id, # Para el redirect
                    'count_agotados': 0,
                    'count_bajo_stock': 0,
                    'resumen_semaforo': 'green' # Por defecto
                }
                
            # 3. Agregar item al pack
            semaforo = cls._semaforo_suministro(s.stock_actual, s.stock_minimo)
            packs_dict[model_ids]['items'].append({
                'id': s.id,
                'nombre': s.nombre,
                'stock_actual': s.stock_actual,
                'stock_minimo': s.stock_minimo,
                'semaforo': semaforo
            })
            
            # 4. Actualizar semáforo del pack (el peor estado manda)
            if semaforo == 'red':
                packs_dict[model_ids]['resumen_semaforo'] = 'red'
                packs_dict[model_ids]['count_agotados'] += 1
            elif semaforo == 'yellow' and packs_dict[model_ids]['resumen_semaforo'] != 'red':
                packs_dict[model_ids]['resumen_semaforo'] = 'yellow'
                packs_dict[model_ids]['count_bajo_stock'] += 1

        # 5. Filtrar verdaderos packs (>= 2 items) y mover los de 1 item a individuales
        packs_finales = []
        for fingerprint, pack_data in packs_dict.items():
            if len(pack_data['items']) >= 2:
                packs_finales.append(pack_data)
            else:
                # Era un pack de 1 solo item, se trata como individual
                item = pack_data['items'][0]
                item['is_pack'] = False
                item['categoria_id'] = pack_data['categoria_id']
                individuales.append(item)

        # 6. Ordenar: Rojos primero, luego Amarillos, luego Verdes
        def sort_key(item):
            s = item.get('resumen_semaforo') if item['is_pack'] else item.get('semaforo')
            return {'red': 0, 'yellow': 1, 'green': 2}.get(s, 3)

        return sorted(packs_finales + individuales, key=sort_key)

    @staticmethod
    def _semaforo_suministro(stock, stock_minimo):
        if stock == 0: return 'red'
        if stock <= stock_minimo: return 'yellow'
        return 'green'
```

---

### Task 3: Implement Consumption Alert (Actas/Entregas)

**Files:**
- Modify: `actas/services.py` OR `suministros/services.py` (wherever the "EntregaSuministro" logic lives).

**Step 1: Check for Previous Deliveries**
When registering a new `MovimientoStock.TipoMovimiento.SALIDA` to a specific `dispositivo_destino` or `colaborador_destino`, find the *last* transaction of this exact `Suministro` to this exact destination.

**Step 2: Calculate Delta and Compare**
If `last_transaction` exists and `suministro.duracion_estimada_dias` is set:
Calculate `days_since = (timezone.now() - last_transaction.fecha).days`.
If `days_since < suministro.duracion_estimada_dias`, raise a specific Warning or add a note to the `MovimientoStock` indicating "⚠️ Consumo inusual: esperado X días, pasaron Y".

*(Note: For this Task 3, precise implementation depends on how the UI currently handles supply deliveries. If it's a form, we add a `clean()` validation warning. If it's the `Acta` service, we append the warning to the Acta context.)*