import qrcode
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import HttpResponse, FileResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.models import TipoDispositivo, Modelo, Fabricante, EstadoDispositivo
from colaboradores.models import Colaborador
from .models import Dispositivo, BitacoraMantenimiento, HistorialAsignacion, EntregaAccesorio
from .forms import (
    NotebookTechForm, SmartphoneTechForm, MonitorTechForm, MantenimientoForm,
    AsignacionForm, ReasignacionForm, DevolucionForm, AccesorioForm
)
from .services import DispositivoFactory

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
            form.save()
            return redirect('dispositivos:dispositivo_list')
    else:
        form = DispositivoFactory.create_form_instance()
    
    return render(request, 'dispositivos/dispositivo_form.html', {
        'form': form,
        'tech_forms': tech_forms,
        'titulo': 'Registrar Nuevo Equipo'
    })

@login_required
def dispositivo_list(request):
    """Listado de inventario con filtros y búsqueda HTMX."""
    from dashboard.filters import AnaliticaInventarioFilter
    
    query = request.GET.get('q', '')
    dispositivos = Dispositivo.objects.select_related('tipo', 'modelo__fabricante', 'estado', 'propietario_actual', 'centro_costo')
    
    # Aplicar Filtros Avanzados (los mismos del Dashboard)
    filterset = AnaliticaInventarioFilter(request.GET, queryset=dispositivos)
    dispositivos = filterset.qs

    # Filtros por nombre para el Drill-down desde Chart.js
    tipo_nombre = request.GET.get('tipo_nombre')
    estado_nombre = request.GET.get('estado_nombre')
    cc_nombre = request.GET.get('cc_nombre')

    if tipo_nombre:
        dispositivos = dispositivos.filter(tipo__nombre=tipo_nombre)
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
        
    context = {
        'dispositivos': dispositivos,
        'filter': filterset,
        'tipos': TipoDispositivo.objects.all(),
        'estados': EstadoDispositivo.objects.all(),
        'query': query,
    }
    
    if request.headers.get('HX-Request'):
        if request.GET.get('_modal') == 'true':
            # Renderizamos la lista en un panel side-over
            context['drilldown_title'] = f"Equipos: {tipo_nombre or estado_nombre or cc_nombre or 'Listado'}"
            return render(request, 'dispositivos/partials/dispositivo_sideover_list.html', context)
        return render(request, 'dispositivos/partials/dispositivo_list_results.html', context)
        
    return render(request, 'dispositivos/dispositivo_list.html', context)

@login_required
def dispositivo_detail(request, pk):
    """Vista detallada con carga Ajax de specs técnicos."""
    dispositivo = get_object_or_404(
        Dispositivo.objects.select_related('tipo', 'modelo__fabricante', 'estado', 'propietario_actual', 'centro_costo'),
        pk=pk
    )
    
    if request.headers.get('HX-Request'):
        # Si es HTMX, devolvemos solo el sideover
        return render(request, 'dispositivos/partials/dispositivo_detail_sideover.html', {'d': dispositivo})
        
    return render(request, 'dispositivos/dispositivo_detail.html', {'d': dispositivo})

@login_required
def ajax_get_modelos(request):
    """Retorna opciones de modelos filtrados por fabricante para el formulario."""
    fabricante_id = request.GET.get('fabricante')
    if fabricante_id:
        modelos = Modelo.objects.filter(fabricante_id=fabricante_id).order_by('nombre')
    else:
        modelos = Modelo.objects.none()
    
    return render(request, 'dispositivos/partials/modelo_options.html', {'modelos': modelos})

@login_required
def ajax_get_tech_fields(request):
    """Retorna los campos técnicos específicos según el tipo de dispositivo."""
    tipo_id = request.GET.get('tipo')
    if not tipo_id:
        return HttpResponse("")
        
    tipo = get_object_or_404(TipoDispositivo, pk=tipo_id)
    form = None
    
    if tipo.nombre == 'Notebook':
        form = NotebookTechForm()
    elif tipo.nombre == 'Smartphone':
        form = SmartphoneTechForm()
    elif tipo.nombre == 'Monitor':
        form = MonitorTechForm()
        
    if form:
        return render(request, 'dispositivos/partials/tech_fields.html', {'form': form})
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
@transaction.atomic
def dispositivo_asignar(request, pk):
    """Asigna un dispositivo que está actualmente Disponible."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    if request.method == 'POST':
        form = AsignacionForm(request.POST)
        if form.is_valid():
            # 1. Crear el historial
            movimiento = form.save(commit=False)
            movimiento.dispositivo = dispositivo
            movimiento.save()
            
            # 2. Actualizar el dispositivo
            estado_asignado, _ = EstadoDispositivo.objects.get_or_create(nombre='Asignado')
            dispositivo.estado = estado_asignado
            dispositivo.propietario_actual = movimiento.colaborador
            dispositivo.save()
            
            if request.headers.get('HX-Request'):
                response = render(request, 'dispositivos/partials/trazabilidad_success.html', {'mensaje': 'Equipo asignado correctamente.'})
                response['HX-Trigger'] = 'asignacion-saved'
                return response
            return redirect('dispositivos:dispositivo_detail', pk=pk)
    else:
        form = AsignacionForm()
    
    return render(request, 'dispositivos/partials/asignacion_form_modal.html', {
        'form': form,
        'dispositivo': dispositivo
    })

@login_required
@permission_required('dispositivos.add_historialasignacion', raise_exception=True)
@transaction.atomic
def dispositivo_reasignar(request, pk):
    """Reasigna un dispositivo de un colaborador a otro."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    ultimo_mov = dispositivo.historial.filter(fecha_fin__isnull=True).first()
    
    if request.method == 'POST':
        form = ReasignacionForm(request.POST)
        if form.is_valid():
            # 1. Cerrar asignación anterior si existe
            if ultimo_mov:
                ultimo_mov.fecha_fin = timezone.now().date()
                ultimo_mov.save()
            
            # 2. Crear nueva asignación
            nuevo_mov = form.save(commit=False)
            nuevo_mov.dispositivo = dispositivo
            nuevo_mov.save()
            
            # 3. Actualizar dueño en dispositivo
            dispositivo.propietario_actual = nuevo_mov.colaborador
            dispositivo.save()
            
            if request.headers.get('HX-Request'):
                response = render(request, 'dispositivos/partials/trazabilidad_success.html', {'mensaje': 'Equipo reasignado correctamente.'})
                response['HX-Trigger'] = 'asignacion-saved'
                return response
            return redirect('dispositivos:dispositivo_detail', pk=pk)
    else:
        form = ReasignacionForm()
    
    return render(request, 'dispositivos/partials/reasignacion_form_modal.html', {
        'form': form,
        'dispositivo': dispositivo,
        'anterior': ultimo_mov.colaborador if ultimo_mov else None
    })

@login_required
@permission_required('dispositivos.add_historialasignacion', raise_exception=True)
@transaction.atomic
def dispositivo_devolver(request, pk):
    """Registra la devolución de un equipo a bodega."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)
    ultimo_mov = dispositivo.historial.filter(fecha_fin__isnull=True).first()
    
    if request.method == 'POST':
        form = DevolucionForm(request.POST)
        if form.is_valid():
            # 1. Cerrar asignación actual
            if ultimo_mov:
                ultimo_mov.fecha_fin = timezone.now().date()
                ultimo_mov.condicion_fisica += f"\n[Devolución]: {form.cleaned_data['condicion_fisica']}"
                ultimo_mov.save()
            
            # 2. Actualizar estado del dispositivo
            estado_slug = form.cleaned_data['estado_llegada']
            if estado_slug == 'danado':
                nuevo_estado, _ = EstadoDispositivo.objects.get_or_create(nombre='En Reparación')
            else:
                nuevo_estado, _ = EstadoDispositivo.objects.get_or_create(nombre='Disponible')
            
            dispositivo.estado = nuevo_estado
            dispositivo.propietario_actual = None
            dispositivo.save()
            
            if request.headers.get('HX-Request'):
                response = render(request, 'dispositivos/partials/trazabilidad_success.html', {'mensaje': 'Devolución registrada correctamente.'})
                response['HX-Trigger'] = 'asignacion-saved'
                return response
            return redirect('dispositivos:dispositivo_detail', pk=pk)
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
@transaction.atomic
def colaborador_entrega_accesorio(request, pk):
    """Registra la entrega de un accesorio a un colaborador."""
    colaborador = get_object_or_404(Colaborador, pk=pk)
    if request.method == 'POST':
        form = AccesorioForm(request.POST)
        if form.is_valid():
            entrega = form.save(commit=False)
            entrega.colaborador = colaborador
            entrega.save()
            
            if request.headers.get('HX-Request'):
                response = render(request, 'dispositivos/partials/accesorio_success.html', {'accesorio': entrega.tipo})
                response['HX-Trigger'] = 'accesorio-saved'
                return response
            return redirect('colaboradores:colaborador_detail', pk=pk)
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
    
    tech_forms = {
        'notebook': NotebookTechForm(request.POST if request.method == 'POST' else None, instance=getattr(dispositivo, 'notebook', None) if hasattr(dispositivo, 'notebook') else None),
        'smartphone': SmartphoneTechForm(request.POST if request.method == 'POST' else None, instance=getattr(dispositivo, 'smartphone', None) if hasattr(dispositivo, 'smartphone') else None),
        'monitor': MonitorTechForm(request.POST if request.method == 'POST' else None, instance=getattr(dispositivo, 'monitor', None) if hasattr(dispositivo, 'monitor') else None),
    }

    if request.method == 'POST':
        form = DispositivoFactory.create_form_instance(request.POST, request.FILES, instance=dispositivo)
        if form.is_valid():
            form.save()
            return redirect('dispositivos:dispositivo_detail', pk=pk)
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
        dispositivo.delete()
        if request.headers.get('HX-Request'):
            # Redirigir al listado despues de eliminar
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse_lazy('dispositivos:dispositivo_list')
            return response
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
