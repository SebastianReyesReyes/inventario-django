import json
import qrcode
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, FileResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Q, OuterRef, Subquery, ProtectedError
from django.utils import timezone

from core.models import TipoDispositivo, Modelo, Fabricante, EstadoDispositivo
from colaboradores.models import Colaborador
from .models import Dispositivo, BitacoraMantenimiento, HistorialAsignacion
from .forms import (
    NotebookTechForm, SmartphoneTechForm, MonitorTechForm, MantenimientoForm,
    AsignacionForm, ReasignacionForm, DevolucionForm, AccesorioForm
)
from .services import DispositivoFactory, TrazabilidadService
from core.htmx import htmx_render_or_redirect, htmx_redirect_or_redirect, is_htmx
from core.pagination import paginate_queryset

@login_required
@permission_required('dispositivos.add_dispositivo', raise_exception=True)
def dispositivo_create(request):
    """Vista para crear un nuevo dispositivo general o específico."""
    tech_forms = {
        'notebook': NotebookTechForm(request.POST if request.method == 'POST' else None),
        'smartphone': SmartphoneTechForm(request.POST if request.method == 'POST' else None),
        'monitor': MonitorTechForm(request.POST if request.method == 'POST' else None),
    }

    if request.method == 'POST':
        tipo_id = request.POST.get('tipo')
        form = DispositivoFactory.create_form_instance(request.POST, request.FILES, tipo_id)

        if form.is_valid():
            # Aislamos transaccionalmente la creación del dispositivo base
            with transaction.atomic():
                dispositivo = form.save()

            # Si se solicitó generar acta y hay propietario asignado,
            # ejecutamos la generación del acta en un bloque atómico separado
            # para no revertir el registro del equipo en caso de fallo.
            if form.cleaned_data.get('generar_acta') and dispositivo.propietario_actual:
                from actas.services import ActaService
                movimiento = dispositivo.historial.filter(
                    colaborador=dispositivo.propietario_actual
                ).order_by('-fecha_inicio').first()

                if movimiento:
                    with transaction.atomic():
                        acta = ActaService.crear_acta(
                            colaborador=dispositivo.propietario_actual,
                            tipo_acta='ENTREGA',
                            asignacion_ids=[movimiento.pk],
                            creado_por=request.user,
                            observaciones=f"Acta generada automáticamente al registrar equipo {dispositivo.identificador_interno}."
                        )
                    messages.success(
                        request,
                        f"Equipo registrado y acta {acta.folio} generada correctamente."
                    )
                    return render(request, 'dispositivos/dispositivo_detail.html', {
                        'd': dispositivo,
                        'show_acta_modal': True,
                        'acta': acta,
                    })

            messages.success(request, "Equipo registrado correctamente.")
            return redirect('dispositivos:dispositivo_detail', pk=dispositivo.pk)
    else:
        form = DispositivoFactory.create_form_instance()

    return render(request, 'dispositivos/dispositivo_form.html', {
        'form': form,
        'tech_forms': tech_forms,
        'titulo': 'Registrar Nuevo Equipo'
    })

@login_required
def dispositivo_list(request):
    """Listado de inventario con filtros, búsqueda y ordenamiento HTMX."""
    from dashboard.filters import AnaliticaInventarioFilter
    
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'identificador_interno')
    order = request.GET.get('order', 'asc')
    
    # Subquery para obtener el estado de firma del acta más reciente
    ultima_acta_firmada = HistorialAsignacion.objects.filter(
        dispositivo=OuterRef('pk')
    ).order_by('-fecha_inicio').values('acta__firmada')[:1]
    
    dispositivos = Dispositivo.objects.select_related('modelo__tipo_dispositivo', 'modelo__fabricante', 'estado', 'propietario_actual', 'centro_costo').annotate(
        acta_firmada=Subquery(ultima_acta_firmada)
    )
    
    # Aplicar Filtros Avanzados (los mismos del Dashboard)
    filterset = AnaliticaInventarioFilter(request.GET, queryset=dispositivos)
    dispositivos = filterset.qs

    # Filtros por nombre para el Drill-down desde Chart.js
    tipo_nombre = request.GET.get('tipo_nombre')
    estado_nombre = request.GET.get('estado_nombre')
    cc_nombre = request.GET.get('cc_nombre')

    if tipo_nombre:
        dispositivos = dispositivos.filter(modelo__tipo_dispositivo__nombre=tipo_nombre)
    if estado_nombre:
        dispositivos = dispositivos.filter(estado__nombre=estado_nombre)
    if cc_nombre:
        if cc_nombre == 'Central/Stock':
            dispositivos = dispositivos.filter(centro_costo__isnull=True)
        else:
            dispositivos = dispositivos.filter(centro_costo__codigo_contable=cc_nombre)
    
    # Manejo de alertas desde la Home
    alerta = request.GET.get('alerta')
    if alerta == 'mantenimiento':
        dispositivos = dispositivos.filter(estado__nombre__icontains='Reparación')
    elif alerta == 'sin_acta':
        # Dispositivos que tienen una asignación actual sin acta
        dispositivos = dispositivos.filter(
            historial__isnull=False,
            historial__acta__isnull=True
        ).distinct()
    
    # Búsqueda textual adicional
    if query:
        dispositivos = dispositivos.filter(
            Q(identificador_interno__icontains=query) |
            Q(numero_serie__icontains=query) |
            Q(modelo__nombre__icontains=query) |
            Q(propietario_actual__first_name__icontains=query) |
            Q(propietario_actual__last_name__icontains=query)
        )
    
    # Ordenamiento
    SORT_MAP = {
        'id': 'identificador_interno',
        'tipo': 'modelo__tipo_dispositivo__nombre',
        'marca': 'modelo__fabricante__nombre',
        'modelo': 'modelo__nombre',
        'responsable': 'propietario_actual__first_name',
        'estado': 'estado__nombre',
        'cc': 'centro_costo__nombre',
        'acta': 'acta_firmada',
    }
    sort_field = SORT_MAP.get(sort, 'identificador_interno')
    if order == 'desc':
        sort_field = f'-{sort_field}'
    dispositivos = dispositivos.order_by(sort_field)
        
    page_obj = paginate_queryset(request, dispositivos, per_page=20)
    context = {
        'page_obj': page_obj,
        'dispositivos': page_obj,
        'filter': filterset,
        'tipos': TipoDispositivo.objects.all(),
        'estados': EstadoDispositivo.objects.all(),
        'query': query,
        'current_sort': sort,
        'current_order': order,
    }
    
    if request.headers.get('HX-Request'):
        if request.GET.get('_modal') == 'true':
            # Renderizamos la lista en un panel side-over
            context['drilldown_title'] = f"Equipos: {tipo_nombre or estado_nombre or cc_nombre or 'Listado'}"
            return render(request, 'dispositivos/partials/dispositivo_sideover_list.html', context)
        return render(request, 'dispositivos/partials/dispositivo_list_table.html', context)
        
    return render(request, 'dispositivos/dispositivo_list.html', context)

@login_required
def dispositivo_detail(request, pk):
    """Vista detallada con carga Ajax de specs técnicos."""
    dispositivo = get_object_or_404(
        Dispositivo.objects.select_related('modelo__tipo_dispositivo', 'modelo__fabricante', 'estado', 'propietario_actual', 'centro_costo'),
        pk=pk
    )
    
    if request.headers.get('HX-Request'):
        # Si es HTMX, devolvemos solo el sideover
        return render(request, 'dispositivos/partials/dispositivo_detail_sideover.html', {'d': dispositivo})
        
    return render(request, 'dispositivos/dispositivo_detail.html', {'d': dispositivo})

@login_required
def ajax_get_modelos(request):
    """Retorna opciones de modelos filtrados por fabricante y tipo para el formulario."""
    fabricante_id = request.GET.get('fabricante')
    tipo_id = request.GET.get('tipo')
    
    modelos = Modelo.objects.all()
    
    if fabricante_id:
        modelos = modelos.filter(fabricante_id=fabricante_id)
    if tipo_id:
        modelos = modelos.filter(tipo_dispositivo_id=tipo_id)
        
    if not fabricante_id and not tipo_id:
        modelos = Modelo.objects.none()
    else:
        modelos = modelos.order_by('nombre')
    
    return render(request, 'dispositivos/partials/modelo_options.html', {'modelos': modelos})


@login_required
@permission_required('dispositivos.add_dispositivo', raise_exception=True)
def ajax_crear_modelo(request):
    """Crea un modelo nuevo para un fabricante y tipo desde el formulario de dispositivos."""
    fabricante_id = request.POST.get('fabricante')
    tipo_id = request.POST.get('tipo')
    nombre = request.POST.get('nuevo_modelo_nombre', '').strip()

    modelos = Modelo.objects.all()
    if fabricante_id:
        modelos = modelos.filter(fabricante_id=fabricante_id)
    if tipo_id:
        modelos = modelos.filter(tipo_dispositivo_id=tipo_id)

    if not fabricante_id or not tipo_id or not nombre:
        return render(request, 'dispositivos/partials/modelo_options.html', {'modelos': modelos.order_by('nombre') if (fabricante_id or tipo_id) else Modelo.objects.none()})

    fabricante = get_object_or_404(Fabricante, pk=fabricante_id)
    tipo_dispositivo = get_object_or_404(TipoDispositivo, pk=tipo_id)

    # Normalización: evitar duplicados por diferencia de mayúsculas
    modelo = Modelo.objects.filter(fabricante=fabricante, tipo_dispositivo=tipo_dispositivo, nombre__iexact=nombre).first()

    if not modelo:
        try:
            modelo = Modelo.objects.create(nombre=nombre, fabricante=fabricante, tipo_dispositivo=tipo_dispositivo)
        except IntegrityError:
            modelo = Modelo.objects.get(fabricante=fabricante, tipo_dispositivo=tipo_dispositivo, nombre__iexact=nombre)

    modelos = Modelo.objects.filter(fabricante=fabricante, tipo_dispositivo=tipo_dispositivo).order_by('nombre')
    return render(request, 'dispositivos/partials/modelo_options.html', {
        'modelos': modelos,
        'selected_modelo_id': modelo.id
    })

@login_required
def ajax_get_tech_fields(request):
    """Retorna los campos técnicos específicos según el tipo de dispositivo."""
    tipo_id = request.GET.get('tipo')
    if not tipo_id:
        return HttpResponse("")
        
    tipo = get_object_or_404(TipoDispositivo, pk=tipo_id)
    nombre = tipo.nombre.lower()
    form = None
    
    if 'notebook' in nombre or 'laptop' in nombre:
        form = NotebookTechForm()
    elif 'smartphone' in nombre or 'celular' in nombre:
        form = SmartphoneTechForm()
    elif 'monitor' in nombre:
        form = MonitorTechForm()
        
    if form:
        return render(request, 'dispositivos/partials/tipo_especifico_fields.html', {'form': form})
    return HttpResponse("")

@login_required
def dispositivo_qr(request, pk):
    """Genera un código QR dinámico para el equipo."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    
    # URL absoluta al detalle
    url = request.build_absolute_uri(dispositivo.get_absolute_url())
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return FileResponse(buffer, as_attachment=False, filename=f"qr_{dispositivo.identificador_interno}.png", content_type="image/png")

@login_required
@permission_required('dispositivos.add_bitacoramantenimiento', raise_exception=True)
@transaction.atomic
def mantenimiento_create(request, pk):
    """Registra una entrada de mantenimiento."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    if request.method == 'POST':
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            mantenimiento = form.save(commit=False)
            mantenimiento.dispositivo = dispositivo
            mantenimiento.save()
            
            # Si se marcó cambio automático y el equipo estaba en reparación
            if mantenimiento.cambio_estado_automatico:
                estado_disponible, _ = EstadoDispositivo.objects.get_or_create(nombre='Disponible')
                dispositivo.estado = estado_disponible
                dispositivo.save()
                
            return render(request, 'dispositivos/partials/mantenimiento_success.html')
    else:
        form = MantenimientoForm()
    
    return render(request, 'dispositivos/partials/mantenimiento_form_modal.html', {
        'form': form,
        'dispositivo': dispositivo
    })

# --- VISTAS DE TRAZABILIDAD (ÉPICA 4) ---

@login_required
@permission_required('dispositivos.add_historialasignacion', raise_exception=True)
def dispositivo_asignar(request, pk):
    """Asigna un dispositivo que está actualmente Disponible."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    if request.method == 'POST':
        form = AsignacionForm(request.POST)
        if form.is_valid():
            creado_por = getattr(request.user, 'colaborador', None)
            movimiento, acta = TrazabilidadService.asignar(dispositivo, form, creado_por=creado_por)
            return htmx_render_or_redirect(
                request,
                'dispositivos/partials/trazabilidad_success.html',
                {'mensaje': 'Equipo asignado correctamente.', 'acta': acta},
                redirect_url=reverse('dispositivos:dispositivo_detail', kwargs={'pk': pk}),
                trigger='asignacion-saved',
            )
    else:
        form = AsignacionForm()

    return render(request, 'dispositivos/partials/asignacion_form_modal.html', {
        'form': form,
        'dispositivo': dispositivo
    })

@login_required
@permission_required('dispositivos.add_historialasignacion', raise_exception=True)
def dispositivo_reasignar(request, pk):
    """Reasigna un dispositivo de un colaborador a otro."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    ultimo_mov = dispositivo.historial.filter(fecha_fin__isnull=True).first()

    if request.method == 'POST':
        form = ReasignacionForm(request.POST)
        if form.is_valid():
            creado_por = getattr(request.user, 'colaborador', None)
            nuevo_mov, acta = TrazabilidadService.reasignar(dispositivo, form, creado_por=creado_por)
            return htmx_render_or_redirect(
                request,
                'dispositivos/partials/trazabilidad_success.html',
                {'mensaje': 'Equipo reasignado correctamente.', 'acta': acta},
                redirect_url=reverse('dispositivos:dispositivo_detail', kwargs={'pk': pk}),
                trigger='asignacion-saved',
            )
    else:
        form = ReasignacionForm()

    return render(request, 'dispositivos/partials/reasignacion_form_modal.html', {
        'form': form,
        'dispositivo': dispositivo,
        'anterior': ultimo_mov.colaborador if ultimo_mov else None
    })

@login_required
@permission_required('dispositivos.add_historialasignacion', raise_exception=True)
def dispositivo_devolver(request, pk):
    """Registra la devolución de un equipo a bodega."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    ultimo_mov = dispositivo.historial.filter(fecha_fin__isnull=True).first()

    if request.method == 'POST':
        form = DevolucionForm(request.POST)
        if form.is_valid():
            creado_por = getattr(request.user, 'colaborador', None)
            ultimo_mov, acta = TrazabilidadService.devolver(dispositivo, form, creado_por=creado_por)
            return htmx_render_or_redirect(
                request,
                'dispositivos/partials/trazabilidad_success.html',
                {'mensaje': 'Devolución registrada correctamente.', 'acta': acta},
                redirect_url=reverse('dispositivos:dispositivo_detail', kwargs={'pk': pk}),
                trigger='asignacion-saved',
            )
    else:
        form = DevolucionForm()

    return render(request, 'dispositivos/partials/devolucion_form_modal.html', {
        'form': form,
        'dispositivo': dispositivo,
        'colaborador': ultimo_mov.colaborador if ultimo_mov else None
    })

@login_required
def dispositivo_historial(request, pk):
    """Carga el timeline del historial de movimientos (Lazy load)."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    historial = dispositivo.historial.select_related('colaborador').all().order_by('-fecha_inicio')
    return render(request, 'dispositivos/partials/historial_timeline.html', {
        'historial': historial
    })

@login_required
@permission_required('dispositivos.add_entregaaccesorio', raise_exception=True)
def colaborador_entrega_accesorio(request, pk):
    """Registra la entrega de un accesorio a un colaborador."""
    colaborador = get_object_or_404(Colaborador, pk=pk)
    if request.method == 'POST':
        form = AccesorioForm(request.POST)
        if form.is_valid():
            entrega = TrazabilidadService.entregar_accesorio(colaborador, form)
            return htmx_render_or_redirect(
                request,
                'dispositivos/partials/accesorio_success.html',
                {'accesorio': entrega.tipo},
                redirect_url=reverse('colaboradores:colaborador_detail', kwargs={'pk': pk}),
                trigger='accesorio-saved',
            )
    else:
        form = AccesorioForm()

    return render(request, 'dispositivos/partials/accesorio_form_modal.html', {
        'form': form,
        'colaborador': colaborador
    })

@login_required
def colaborador_historial_accesorios(request, pk):
    """Carga el listado de accesorios entregados (Lazy load)."""
    colaborador = get_object_or_404(Colaborador, pk=pk)
    accesorios = colaborador.accesorios.all().order_by('-fecha')
    return render(request, 'dispositivos/partials/accesorios_list.html', {
        'accesorios': accesorios
    })

@login_required
@permission_required('dispositivos.change_dispositivo', raise_exception=True)
def dispositivo_update(request, pk):
    """Actualiza la información de un dispositivo."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    propietario_anterior = dispositivo.propietario_actual

    tech_forms = {
        'notebook': NotebookTechForm(request.POST if request.method == 'POST' else None, instance=getattr(dispositivo, 'notebook', None) if hasattr(dispositivo, 'notebook') else None),
        'smartphone': SmartphoneTechForm(request.POST if request.method == 'POST' else None, instance=getattr(dispositivo, 'smartphone', None) if hasattr(dispositivo, 'smartphone') else None),
        'monitor': MonitorTechForm(request.POST if request.method == 'POST' else None, instance=getattr(dispositivo, 'monitor', None) if hasattr(dispositivo, 'monitor') else None),
    }

    if request.method == 'POST':
        form = DispositivoFactory.create_form_instance(request.POST, request.FILES, instance=dispositivo)
        if form.is_valid():
            cambio_propietario = False
            nuevo_propietario = None
            movimiento = None

            # Bloque atómico para la edición del dispositivo base + trazabilidad
            with transaction.atomic():
                dispositivo = form.save()

                nuevo_propietario = dispositivo.propietario_actual
                cambio_propietario = (propietario_anterior != nuevo_propietario)

                # Si cambió el propietario y se solicitó generar acta,
                # actualizamos la trazabilidad dentro del mismo bloque base.
                if cambio_propietario and form.cleaned_data.get('generar_acta') and nuevo_propietario:
                    ultimo_mov = dispositivo.historial.filter(fecha_fin__isnull=True).first()
                    if ultimo_mov and cambio_propietario:
                        ultimo_mov.fecha_fin = timezone.now().date()
                        ultimo_mov.save()

                    movimiento = HistorialAsignacion.objects.create(
                        dispositivo=dispositivo,
                        colaborador=nuevo_propietario,
                        condicion_fisica="Asignación generada desde edición del equipo."
                    )

                    estado_asignado, _ = EstadoDispositivo.objects.get_or_create(nombre='Asignado')
                    dispositivo.estado = estado_asignado
                    dispositivo.save()

            # Generación del acta en un bloque atómico separado para no revertir
            # la edición del equipo si falla la creación del acta.
            if cambio_propietario and form.cleaned_data.get('generar_acta') and nuevo_propietario and movimiento:
                from actas.services import ActaService
                with transaction.atomic():
                    acta = ActaService.crear_acta(
                        colaborador=nuevo_propietario,
                        tipo_acta='ENTREGA',
                        asignacion_ids=[movimiento.pk],
                        creado_por=request.user,
                        observaciones=f"Acta generada automáticamente al editar asignación de {dispositivo.identificador_interno}."
                    )
                messages.success(
                    request,
                    f"Equipo actualizado y acta {acta.folio} generada correctamente."
                )
                return render(request, 'dispositivos/dispositivo_detail.html', {
                    'd': dispositivo,
                    'show_acta_modal': True,
                    'acta': acta,
                })

            messages.success(request, "Equipo actualizado correctamente.")
            return redirect('dispositivos:dispositivo_detail', pk=pk)
        else:
            return render(request, 'dispositivos/dispositivo_form.html', {
                'form': form,
                'tech_forms': tech_forms,
                'titulo': f'Editar {dispositivo.identificador_interno}'
            })
    else:
        form = DispositivoFactory.create_form_instance(instance=dispositivo)

    return render(request, 'dispositivos/dispositivo_form.html', {
        'form': form,
        'tech_forms': tech_forms,
        'titulo': f'Editar {dispositivo.identificador_interno}'
    })

@login_required
@permission_required('dispositivos.delete_dispositivo', raise_exception=True)
def dispositivo_delete(request, pk):
    """Elimina un dispositivo (confirmación vía modal)."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    if request.method in ['POST', 'DELETE']:
        try:
            dispositivo.delete()
            return htmx_redirect_or_redirect(
                request,
                redirect_url=reverse('dispositivos:dispositivo_list'),
            )
        except (ProtectedError, IntegrityError):
            error_msg = (
                "No se puede eliminar este equipo porque tiene un historial de "
                "asignaciones, actas o mantenimientos asociados."
            )
            if is_htmx(request):
                from core.htmx import htmx_trigger_response
                # Devolvemos 204 para no alterar el DOM y disparamos el toast de error
                return htmx_trigger_response(
                    trigger={'show-notification': {'message': error_msg, 'type': 'error'}},
                    status=204
                )

            messages.error(request, error_msg)
            return redirect('dispositivos:dispositivo_list')

    return render(request, 'dispositivos/partials/dispositivo_confirm_delete.html', {
        'dispositivo': dispositivo
    })

@login_required
@permission_required('dispositivos.change_bitacoramantenimiento', raise_exception=True)
def mantenimiento_update(request, pk):
    """Actualiza un registro de mantenimiento."""
    mantenimiento = get_object_or_404(BitacoraMantenimiento, pk=pk)
    if request.method == 'POST':
        form = MantenimientoForm(request.POST, instance=mantenimiento)
        if form.is_valid():
            form.save()
            return render(request, 'dispositivos/partials/mantenimiento_success.html')
    else:
        form = MantenimientoForm(instance=mantenimiento)
    
    return render(request, 'dispositivos/partials/mantenimiento_form_modal.html', {
        'form': form,
        'dispositivo': mantenimiento.dispositivo,
        'edit_mode': True
    })
