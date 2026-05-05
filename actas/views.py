import logging

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.utils.html import escape

from .models import Acta
from .forms import ActaCrearForm
from .services import ActaService, ActaPDFService
from core.htmx import htmx_trigger_response

logger = logging.getLogger('actas')


def _render_acta_error(message):
    """Renderiza el bloque OOB de errores para el modal de actas."""
    return render_to_string("actas/partials/acta_error.html", {"message": message})

@login_required
@permission_required('actas.view_acta', raise_exception=True)
def acta_list(request):
    """Listado paginado de actas con filtrado básico y ordenamiento HTMX."""
    actas_list = Acta.objects.all().select_related('colaborador', 'creado_por')
    
    # Excluir actas anuladas por defecto (a menos que se pida explícitamente)
    incluir_anuladas = request.GET.get('incluir_anuladas')
    if not incluir_anuladas:
        actas_list = actas_list.filter(anulada=False)
    
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
        'firmada': 'firmada',
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
        template = 'actas/partials/acta_table.html'

    return render(request, template, {
        'page_obj': page_obj,
        'query': q or '',
        'tipo': tipo or '',
        'current_sort': sort,
        'current_order': order,
    })

@login_required
@permission_required('actas.add_acta', raise_exception=True)
def acta_preview(request):
    """Genera la vista previa HTML de un acta sin persistir en BD.
    Soporta POST (desde HTMX) y GET (para abrir en nueva pestaña)."""
    if request.method == 'POST':
        data = request.POST
    elif request.method == 'GET':
        data = request.GET
    else:
        return HttpResponse("Método no permitido", status=405)

    form = ActaCrearForm(data)
    asignacion_ids = data.getlist('asignaciones')
    accesorio_ids = data.getlist('accesorios')
    movimiento_ids = data.getlist('movimientos')

    if not form.is_valid():
        error_html = _render_acta_error("Corrija los errores del formulario antes de previsualizar.")
        return HttpResponse(error_html)

    try:
        if form.cleaned_data['tipo_acta'] == 'ENTREGA_SUMINISTROS':
            preview_html = ActaService.generar_preview_html_suministros(
                colaborador=form.cleaned_data['colaborador'],
                tipo_acta=form.cleaned_data['tipo_acta'],
                movimiento_ids=movimiento_ids,
                creado_por=request.user,
                observaciones=form.cleaned_data.get('observaciones'),
            )
        else:
            preview_html = ActaService.generar_preview_html(
                colaborador=form.cleaned_data['colaborador'],
                tipo_acta=form.cleaned_data['tipo_acta'],
                asignacion_ids=asignacion_ids,
                creado_por=request.user,
                observaciones=form.cleaned_data.get('observaciones'),
                accesorio_ids=accesorio_ids,
                ministro_de_fe=form.cleaned_data.get('ministro_de_fe'),
            )

        # GET → renderizar página completa en nueva pestaña (para comparar con PDF)
        if request.method == 'GET':
            return render(request, 'actas/partials/acta_preview_fullpage.html', {
                'preview_html': preview_html,
                'acta': form.cleaned_data['colaborador'],  # fallback para title
            })

        return render(request, 'actas/partials/acta_preview_sideover.html', {
            'preview_html': preview_html,
            'form_data': data,
        })

    except ValidationError as e:
        error_html = _render_acta_error(str(e))
        return HttpResponse(error_html)
    except Exception:
        logger.exception("Error en preview de acta")
        error_html = _render_acta_error('Error interno al generar la vista previa.')
        return HttpResponse(error_html)


@login_required
@permission_required('actas.add_acta', raise_exception=True)
def acta_preview_pdf(request):
    """Genera un PDF de preview (sin persistir) usando el engine configurado."""
    form = ActaCrearForm(request.GET)
    asignacion_ids = request.GET.getlist('asignaciones')
    accesorio_ids = request.GET.getlist('accesorios')

    if not form.is_valid():
        return HttpResponse("Datos inválidos para generar PDF de preview", status=400)

    try:
        pdf_bytes = ActaPDFService.generar_preview_pdf(
            colaborador=form.cleaned_data['colaborador'],
            tipo_acta=form.cleaned_data['tipo_acta'],
            asignacion_ids=asignacion_ids,
            creado_por=request.user,
            observaciones=form.cleaned_data.get('observaciones'),
            accesorio_ids=accesorio_ids,
            ministro_de_fe=form.cleaned_data.get('ministro_de_fe'),
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="preview.pdf"'
        return response
    except ValidationError as e:
        logger.warning("Error de validación en preview PDF: %s", e)
        return HttpResponse("Datos inválidos para generar PDF de preview", status=400)
    except Exception:
        logger.exception("Error generando preview PDF")
        return HttpResponse("Error interno al generar el PDF. Intente nuevamente.", status=500)


@login_required
@permission_required('actas.add_acta', raise_exception=True)
def acta_create(request):
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
                error_html = _render_acta_error(str(e))
                return HttpResponse(error_html)
            except Exception:
                logger.exception("Error creando acta")
                error_html = _render_acta_error('Error interno al crear el acta.')
                return HttpResponse(error_html)

    else:
        form = ActaCrearForm()
    
    return render(request, 'actas/partials/acta_crear_modal.html', {'form': form})

@login_required
@permission_required('actas.view_acta', raise_exception=True)
def acta_detail(request, pk):
    """Muestra el detalle de un acta en el side-over."""
    acta, items = ActaService.obtener_acta_con_relaciones(pk)
    
    context = {
        'acta': acta,
        'asignaciones': items if acta.tipo_acta != 'ENTREGA_SUMINISTROS' else None,
        'movimientos': items if acta.tipo_acta == 'ENTREGA_SUMINISTROS' else None,
        'es_suministros': acta.tipo_acta == 'ENTREGA_SUMINISTROS',
    }
    
    return render(request, 'actas/partials/acta_detail_sideover.html', context)

@login_required
@permission_required('actas.view_acta', raise_exception=True)
def acta_pdf(request, pk):
    """Genera el PDF legal corporativo usando ActaPDFService (Playwright/Chromium)."""
    try:
        acta, items = ActaService.obtener_acta_con_relaciones(pk)
        
        if acta.tipo_acta == 'ENTREGA_SUMINISTROS':
            # Obtener costo unitario desde la última ENTRADA de cada suministro
            from suministros.models import MovimientoStock
            suministro_ids = [m.suministro_id for m in items]
            # SQLite no soporta .distinct('field'), usamos orden + seen set
            entradas = MovimientoStock.objects.filter(
                suministro_id__in=suministro_ids,
                tipo_movimiento=MovimientoStock.TipoMovimiento.ENTRADA,
                costo_unitario__isnull=False,
            ).order_by('-fecha')
            seen = set()
            costos_entrada = {}
            for e in entradas:
                if e.suministro_id not in seen:
                    seen.add(e.suministro_id)
                    costos_entrada[e.suministro_id] = e.costo_unitario
            movimientos_data = []
            for m in items:
                costo = m.costo_unitario or costos_entrada.get(m.suministro_id) or 0
                movimientos_data.append({
                    'movimiento': m,
                    'costo_efectivo': costo,
                    'subtotal': costo * m.cantidad,
                })
            valor_total = sum(d['subtotal'] for d in movimientos_data)
            preview_html = render_to_string('actas/partials/acta_suministro_preview_content.html', {
                'acta': acta,
                'movimientos': items,
                'movimientos_data': movimientos_data,
                'logo_path': ActaPDFService._encode_logo_to_base64(
                    finders.find('img/LogoColor.png')
                ),
                'fecha_actual': timezone.now(),
                'pdf_mode': True,
                'valor_total': valor_total,
                'es_suministros': True,
            })
            pdf_content = ActaPDFService.generar_pdf_suministros(acta, preview_html)
        else:
            pdf_content = ActaPDFService.generar_pdf(acta)

        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Acta_{acta.folio}.pdf"'
        return response
    except Exception:
        logger.exception("Error generando PDF para acta %s", pk)
        return HttpResponse('Error interno al generar el PDF. Intente nuevamente.', status=500)

@login_required
@permission_required('actas.change_acta', raise_exception=True)
def acta_firmar(request, pk):
    """Marca un acta como firmada usando ActaService."""
    if request.method == 'POST':
        try:
            ActaService.firmar_acta(pk, firmado_por=request.user)
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
@permission_required('actas.delete_acta', raise_exception=True)
def acta_anular(request, pk):
    """Anula o elimina un acta con doble confirmación vía HTMX.

    GET: Renderiza el modal de confirmación con text-guard.
    POST: Ejecuta la anulación (firmada) o eliminación (borrador).
    """
    acta = get_object_or_404(Acta, pk=pk)

    if acta.anulada:
        if request.headers.get('HX-Request'):
            return HttpResponse(
                _render_acta_error("Esta acta ya fue anulada."),
                status=400
            )
        return HttpResponse("Acta ya anulada.", status=400)

    if request.method == 'GET':
        # Determinar parámetros del modal según estado del acta
        if acta.firmada:
            context = {
                'acta': acta,
                'severity': 'firmada',
                'dialog_title': 'Anular Acta Firmada',
                'subtitle': acta.folio,
                'message': 'Esta acta está FIRMADA y constituye un documento legal. '
                           'La anulación es irreversible y el registro se conservará con estado ANULADA.',
                'guard_text': f'ANULAR-{acta.folio}',
                'guard_label': f'Escriba ANULAR-{acta.folio} para confirmar',
                'confirm_text': 'Anular Acta',
                'confirm_icon': 'gavel',
                'requires_reason': True,
                'action_url': f"/actas/{acta.pk}/anular/",
            }
        else:
            context = {
                'acta': acta,
                'severity': 'borrador',
                'dialog_title': 'Eliminar Borrador',
                'subtitle': acta.folio,
                'message': 'Este borrador será eliminado permanentemente. '
                           'Esta acción no se puede deshacer.',
                'guard_text': 'ELIMINAR',
                'guard_label': 'Escriba ELIMINAR para confirmar',
                'confirm_text': 'Eliminar',
                'confirm_icon': 'delete_forever',
                'requires_reason': False,
                'action_url': f"/actas/{acta.pk}/anular/",
            }
        return render(request, 'actas/partials/acta_anular_modal.html', context)

    # POST — ejecutar anulación/eliminación
    motivo = request.POST.get('motivo', '').strip()

    try:
        if acta.firmada:
            if not motivo or len(motivo) < 10:
                error_html = _render_acta_error(
                    "El motivo de anulación es obligatorio (mínimo 10 caracteres)."
                )
                return HttpResponse(error_html, status=400)

        acta_obj, accion = ActaService.anular(
            acta_pk=acta.pk,
            usuario=request.user,
            motivo=motivo if acta.firmada else None,
        )

        if accion == 'eliminada':
            # Borrador eliminado — la tabla se refresca y el registro desaparece
            return htmx_trigger_response('actaEliminada')
        else:
            # Acta anulada (soft delete) — la tabla se refresca mostrando estado ANULADA
            return htmx_trigger_response('actaAnulada')

    except ValidationError as e:
        error_html = _render_acta_error(str(e))
        return HttpResponse(error_html, status=400)
    except Exception:
        logger.exception("Error anulando acta %s", pk)
        error_html = _render_acta_error('Error interno al anular el acta.')
        return HttpResponse(error_html, status=500)


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
        nombre = escape(m.nombre_completo)
        cargo = escape(m.cargo) if m.cargo else "Sin Cargo"
        options_html += f'<option value="{m.pk}" {selected}>{nombre} ({cargo})</option>'

    return HttpResponse(options_html)


@login_required
@permission_required('actas.add_acta', raise_exception=True)
def acta_suministro_create(request):
    """Crea una nueva acta de entrega de suministros."""
    if request.method == 'POST':
        form = ActaCrearForm(request.POST)
        movimiento_ids = request.POST.getlist('movimientos')
        
        if form.is_valid():
            try:
                ActaService.crear_acta(
                    colaborador=form.cleaned_data['colaborador'],
                    tipo_acta='ENTREGA_SUMINISTROS',
                    movimiento_ids=movimiento_ids,
                    creado_por=request.user,
                    observaciones=form.cleaned_data.get('observaciones'),
                )
                return htmx_trigger_response('actaCreated')
            except ValidationError as e:
                error_html = _render_acta_error(str(e))
                return HttpResponse(error_html)
            except Exception:
                logger.exception("Error creando acta de suministros")
                error_html = _render_acta_error('Error interno al crear el acta.')
                return HttpResponse(error_html)
    else:
        form = ActaCrearForm(initial={'tipo_acta': 'ENTREGA_SUMINISTROS'})
    
    return render(request, 'actas/partials/acta_suministro_form.html', {
        'form': form,
        'es_suministros': True,
    })


@login_required
@permission_required('actas.add_acta', raise_exception=True)
def acta_suministro_preview(request):
    """Genera la vista previa HTML de un acta de suministros."""
    if request.method == 'POST':
        data = request.POST
    elif request.method == 'GET':
        data = request.GET
    else:
        return HttpResponse("Método no permitido", status=405)

    form = ActaCrearForm(data)
    movimiento_ids = data.getlist('movimientos')

    if not form.is_valid():
        error_html = _render_acta_error("Corrija los errores del formulario.")
        return HttpResponse(error_html)

    try:
        preview_html = ActaService.generar_preview_html_suministros(
            colaborador=form.cleaned_data['colaborador'],
            tipo_acta='ENTREGA_SUMINISTROS',
            movimiento_ids=movimiento_ids,
            creado_por=request.user,
            observaciones=form.cleaned_data.get('observaciones'),
        )

        if request.method == 'GET':
            return render(request, 'actas/partials/acta_preview_fullpage.html', {
                'preview_html': preview_html,
                'acta': form.cleaned_data['colaborador'],
            })

        return render(request, 'actas/partials/acta_suministro_preview_sideover.html', {
            'preview_html': preview_html,
            'form_data': data,
        })

    except ValidationError as e:
        error_html = _render_acta_error(str(e))
        return HttpResponse(error_html)
    except Exception:
        logger.exception("Error en preview de acta de suministros")
        error_html = _render_acta_error('Error interno al generar la vista previa.')
        return HttpResponse(error_html)


@login_required
@permission_required('actas.add_acta', raise_exception=True)
def acta_suministro_preview_pdf(request):
    """Genera un PDF de preview para acta de suministros."""
    form = ActaCrearForm(request.GET)
    movimiento_ids = request.GET.getlist('movimientos')

    if not form.is_valid():
        return HttpResponse("Datos inválidos para generar PDF", status=400)

    try:
        pdf_bytes = ActaService.generar_preview_pdf_suministros(
            colaborador=form.cleaned_data['colaborador'],
            tipo_acta='ENTREGA_SUMINISTROS',
            movimiento_ids=movimiento_ids,
            creado_por=request.user,
            observaciones=form.cleaned_data.get('observaciones'),
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="preview-suministros.pdf"'
        return response
    except ValidationError as e:
        logger.warning("Error de validación en preview PDF suministros: %s", e)
        return HttpResponse("Datos inválidos", status=400)
    except Exception:
        logger.exception("Error generando preview PDF suministros")
        return HttpResponse("Error interno al generar el PDF.", status=500)


@login_required
@permission_required('actas.add_acta', raise_exception=True)
def movimientos_pendientes(request, colaborador_pk):
    """HTMX partial que lista los movimientos de stock sin acta de un colaborador."""
    real_pk = colaborador_pk or request.GET.get('colaborador_pk')
    
    if not real_pk or real_pk == '0':
        return HttpResponse('<p class="text-xs text-jmie-gray italic text-center py-4">Seleccione un colaborador para ver movimientos pendientes.</p>')
    
    movimientos = ActaService.obtener_movimientos_pendientes(real_pk)
    
    return render(request, 'actas/partials/movimientos_pendientes.html', {
        'movimientos': movimientos
    })
