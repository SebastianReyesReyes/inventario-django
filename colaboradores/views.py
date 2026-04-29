from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from .models import Colaborador
from .forms import ColaboradorForm
from .resources import ColaboradorResource
import secrets
from core.pagination import paginate_queryset

@login_required
def colaborador_list(request):
    """Listado de colaboradores con búsqueda en vivo (HTMX) y ordenamiento."""
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'first_name')
    order = request.GET.get('order', 'asc')

    # Solo mostrar los que están activos operativamente
    colaboradores = Colaborador.objects.filter(esta_activo=True).select_related('departamento', 'centro_costo')

    if query:
        colaboradores = colaboradores.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(rut__icontains=query) |
            Q(username__icontains=query)
        )

    # Ordenamiento
    SORT_MAP = {
        'nombre': 'first_name',
        'rut': 'rut',
        'departamento': 'departamento__nombre',
        'centro_costo': 'centro_costo__nombre',
        'estado': 'esta_activo',
    }
    sort_field = SORT_MAP.get(sort, 'first_name')
    if order == 'desc':
        sort_field = f'-{sort_field}'
    colaboradores = colaboradores.order_by(sort_field)

    page_obj = paginate_queryset(request, colaboradores, per_page=20)
    context = {
        'page_obj': page_obj,
        'colaboradores': page_obj,
        'query': query,
        'current_sort': sort,
        'current_order': order,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'colaboradores/partials/colaborador_list_table.html', context)

    return render(request, 'colaboradores/colaborador_list.html', context)

@login_required
@permission_required('colaboradores.add_colaborador', raise_exception=True)
def colaborador_create(request):
    """Vista para registrar un nuevo colaborador."""
    if request.method == 'POST':
        form = ColaboradorForm(request.POST)
        if form.is_valid():
            colaborador = form.save(commit=False)
            # Por ahora asignamos una password aleatoria ya que el login se manejará después
            colaborador.password = make_password(secrets.token_urlsafe(16))
            colaborador.save()
            return redirect('colaboradores:colaborador_list')
    else:
        form = ColaboradorForm()
    
    return render(request, 'colaboradores/colaborador_form.html', {'form': form, 'titulo': 'Registrar Colaborador'})

@login_required
@permission_required('colaboradores.change_colaborador', raise_exception=True)
def colaborador_update(request, pk):
    """Vista para editar datos de un colaborador."""
    colaborador = get_object_or_404(Colaborador, pk=pk)
    if request.method == 'POST':
        form = ColaboradorForm(request.POST, instance=colaborador)
        if form.is_valid():
            form.save()
            return redirect('colaboradores:colaborador_list')
    else:
        form = ColaboradorForm(instance=colaborador)
    
    return render(request, 'colaboradores/colaborador_form.html', {'form': form, 'titulo': f'Editar: {colaborador.nombre_completo}', 'es_edicion': True})

@login_required
def colaborador_detail(request, pk):
    """Vista de perfil y auditoría de equipos asignados."""
    colaborador = get_object_or_404(Colaborador.objects.select_related('departamento', 'centro_costo'), pk=pk)
    # Obtenemos los equipos asignados actualmente
    equipos = colaborador.equipos_asignados.select_related('modelo__tipo_dispositivo', 'modelo__fabricante', 'estado')
    
    context = {
        'c': colaborador,
        'equipos': equipos,
    }
    
    # Si es HTMX, devolvemos la versión para el Side-Over
    if request.headers.get('HX-Request'):
        return render(request, 'colaboradores/colaborador_side_over.html', context)
    
    # Si es una carga normal, la página completa
    return render(request, 'colaboradores/colaborador_detail.html', context)

@login_required
@permission_required('colaboradores.delete_colaborador', raise_exception=True)
def colaborador_delete(request, pk):
    """Baja lógica de colaborador."""
    colaborador = get_object_or_404(Colaborador, pk=pk)
    try:
        colaborador.delete() # El método delete() ya está sobrescrito en el modelo para ser lógico
    except Exception as e:
        # Por si alguna restricción a nivel base de datos o similar falla
        if request.headers.get('HX-Request'):
            from core.htmx import htmx_trigger_response
            return htmx_trigger_response(
                trigger={
                    'show-notification': {
                        'message': f"Error al desactivar el colaborador: {str(e)}",
                        'type': 'error'
                    }
                },
                status_code=204
            )
        messages.error(request, f"Error al desactivar: {str(e)}")
        return redirect('colaboradores:colaborador_list')
    
    if request.headers.get('HX-Request'):
        return HttpResponse("") # Elimina la fila en el cliente
        
    return redirect('colaboradores:colaborador_list')


@login_required
def colaborador_exportar_excel(request):
    """Exporta el padron completo de colaboradores a formato Excel."""
    dataset = ColaboradorResource().export(Colaborador.objects.select_related(
        'departamento', 'centro_costo'
    ).all().order_by('first_name'))
    response = HttpResponse(
        dataset.export('xlsx'),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="Colaboradores_JMIE_{timezone.now().date()}.xlsx"'
    )
    return response
