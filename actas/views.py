from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.template.loader import render_to_string

from .models import Acta
from .forms import ActaCrearForm
from .services import ActaService
from core.htmx import htmx_trigger_response


def _render_acta_error(message):
    """Renderiza el bloque OOB de errores para el modal de actas."""
    return render_to_string("actas/partials/acta_error.html", {"message": message})

@login_required
@permission_required('actas.view_acta', raise_exception=True)
def acta_list(request):
    """Listado paginado de actas con filtrado básico y ordenamiento HTMX."""
    actas_list = Acta.objects.all().select_related('colaborador', 'creado_por')
    
    q = request.GET.get('q')
    if q:
        from django.db.models import Q
        actas_list = actas_list.filter(
            Q(folio__icontains=q) | 
            Q(colaborador__first_name__icontains=q) |
            Q(colaborador__last_name__icontains=q)
        )
        
    tipo = request.GET.get('tipo')
    if tipo:
        actas_list = actas_list.filter(tipo_acta=tipo)

    # Ordenamiento
    sort = request.GET.get('sort', 'folio')
    order = request.GET.get('order', 'asc')
    
    SORT_MAP = {
        'folio': 'folio',
        'colaborador': 'colaborador__first_name',
        'tipo': 'tipo_acta',
        'fecha': 'fecha',
        'creado_por': 'creado_por__first_name',
    }
    
    sort_field = SORT_MAP.get(sort, 'folio')
    if order == 'desc':
        sort_field = f'-{sort_field}'
    actas_list = actas_list.order_by(sort_field)

    paginator = Paginator(actas_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    template = 'actas/acta_list.html'
    if request.headers.get('HX-Request'):
        if 'sort' in request.GET or 'order' in request.GET:
            template = 'actas/partials/acta_table.html'
        else:
            template = 'actas/partials/acta_table_rows.html'

    return render(request, template, {
        'page_obj': page_obj,
        'query': q or '',
        'tipo': tipo or '',
        'current_sort': sort,
        'current_order': order,
    })

@login_required
@permission_required('actas.add_acta', raise_exception=True)
def acta_crear(request):
    """Crea una nueva acta vinculando asignaciones seleccionadas usando ActaService."""
    if request.method == 'POST':
        form = ActaCrearForm(request.POST)
        asignacion_ids = request.POST.getlist('asignaciones')
        accesorio_ids = request.POST.getlist('accesorios')
        
        if form.is_valid():
            try:
                # Toda la lógica de negocio se delega al servicio
                ActaService.crear_acta(
                    colaborador=form.cleaned_data['colaborador'],
                    tipo_acta=form.cleaned_data['tipo_acta'],
                    asignacion_ids=asignacion_ids,
                    creado_por=request.user,
                    observaciones=form.cleaned_data.get('observaciones'),
                    accesorio_ids=accesorio_ids,
                    metodo_sanitizacion=form.cleaned_data.get('metodo_sanitizacion', 'N/A'),
                    ministro_de_fe=form.cleaned_data.get('ministro_de_fe')
                )

                return htmx_trigger_response('actaCreated')
                
            except ValidationError as e:
                error_html = _render_acta_error(str(e.message if hasattr(e, 'message') else e))
                return HttpResponse(error_html)
            except Exception as e:
                error_html = _render_acta_error(f'Error: {str(e)}')
                return HttpResponse(error_html)

    else:
        form = ActaCrearForm()
    
    return render(request, 'actas/partials/acta_crear_modal.html', {'form': form})

@login_required
@permission_required('actas.view_acta', raise_exception=True)
def acta_detail(request, pk):
    """Muestra el detalle de un acta en el side-over."""
    acta, asignaciones = ActaService.obtener_acta_con_relaciones(pk)
    
    return render(request, 'actas/partials/acta_detail_sideover.html', {
        'acta': acta,
        'asignaciones': asignaciones
    })

@login_required
@permission_required('actas.view_acta', raise_exception=True)
def acta_pdf(request, pk):
    """Genera el PDF legal corporativo usando ActaService."""
    try:
        acta, _ = ActaService.obtener_acta_con_relaciones(pk)
        pdf_content = ActaService.generar_pdf(acta)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Acta_{acta.folio}.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f'Error al generar PDF: {str(e)}', status=500)

@login_required
@permission_required('actas.change_acta', raise_exception=True)
def acta_firmar(request, pk):
    """Marca un acta como firmada usando ActaService."""
    if request.method == 'POST':
        try:
            ActaService.firmar_acta(pk)
        except ValidationError:
            pass  # Si ya está firmada, no es un error
        
        # Devolvemos el botón en estado firmado (reemplaza el original via HTMX)
        response = HttpResponse(
            '<button disabled class="w-full py-3 bg-success/10 text-success text-xs font-black uppercase tracking-widest rounded-xl border border-success/20 transition-all flex items-center justify-center gap-2 opacity-60 cursor-not-allowed">'
            '<span class="material-symbols-outlined text-sm">check_circle</span>'
            'Acta Firmada'
            '</button>',
            status=200
        )
        response["HX-Trigger"] = "actaFirmada"
        return response
    return HttpResponse("Método no permitido", status=405)

@login_required
@permission_required('actas.add_acta', raise_exception=True)
def asignaciones_pendientes(request, colaborador_pk):
    """HTMX partial que lista las asignaciones sin acta de un colaborador."""
    real_pk = colaborador_pk or request.GET.get('colaborador_pk')
    
    if not real_pk or real_pk == '0':
        return HttpResponse('<p class="text-xs text-jmie-gray italic text-center py-4">Seleccione un colaborador para ver equipos pendientes.</p>')
    
    asignaciones = ActaService.obtener_pendientes(real_pk)
    accesorios = ActaService.obtener_accesorios_pendientes(real_pk)
    
    return render(request, 'actas/partials/asignaciones_pendientes.html', {
        'asignaciones': asignaciones,
        'accesorios': accesorios
    })

@login_required
def ministros_por_colaborador(request, colaborador_pk):
    """Retorna las opciones del select de Ministro de Fe filtradas por la obra del colaborador."""
    from colaboradores.models import Colaborador
    from django.db.models import Q
    
    colaborador = get_object_or_404(Colaborador, pk=colaborador_pk)
    obra = colaborador.centro_costo
    
    # Filtramos administradores de la misma obra
    admin_criterios = Q(cargo__icontains='Administrador') | Q(cargo__icontains='Jefe') | Q(cargo__icontains='Encargado')
    
    ministros = Colaborador.objects.filter(
        esta_activo=True,
        centro_costo=obra
    ).filter(admin_criterios).order_by('first_name')
    
    # Si no hay administradores en la misma obra, mostramos todos los administradores generales como respaldo
    if not ministros.exists():
        ministros = Colaborador.objects.filter(
            esta_activo=True
        ).filter(admin_criterios).order_by('first_name')

    options_html = '<option value="">---------</option>'
    for m in ministros:
        # Marcamos como seleccionado si es el único
        selected = 'selected' if ministros.count() == 1 else ''
        options_html += f'<option value="{m.pk}" {selected}>{m.nombre_completo} ({m.cargo or "Sin Cargo"})</option>'
    
    return HttpResponse(options_html)
