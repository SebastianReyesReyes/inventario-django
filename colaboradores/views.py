from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.hashers import make_password
from .models import Colaborador
from .forms import ColaboradorForm
import secrets

@login_required
def colaborador_list(request):
    """Listado de colaboradores con búsqueda en vivo (HTMX)."""
    query = request.GET.get('q', '')
    # Solo mostrar los que están activos operativamente
    colaboradores = Colaborador.objects.filter(esta_activo=True).select_related('departamento', 'centro_costo')
    
    if query:
        colaboradores = colaboradores.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(rut__icontains=query) |
            Q(username__icontains=query)
        )
    
    context = {
        'colaboradores': colaboradores,
        'query': query,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'colaboradores/partials/colaborador_list_results.html', context)
    
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
    equipos = colaborador.equipos_asignados.select_related('tipo', 'modelo__fabricante', 'estado')
    
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
    colaborador.delete() # El método delete() ya está sobrescrito en el modelo para ser lógico
    
    if request.headers.get('HX-Request'):
        return HttpResponse("") # Elimina la fila en el cliente
        
    return redirect('colaboradores:colaborador_list')
