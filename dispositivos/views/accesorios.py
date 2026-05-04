from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, permission_required

from colaboradores.models import Colaborador
from ..forms import AccesorioForm
from ..services import TrazabilidadService
from core.htmx import htmx_render_or_redirect


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
