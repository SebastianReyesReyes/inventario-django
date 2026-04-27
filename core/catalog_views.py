from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views import View

from dispositivos.models import Dispositivo

from .forms import (
    CentroCostoForm,
    DepartamentoForm,
    EstadoDispositivoForm,
    FabricanteForm,
    ModeloForm,
    TipoDispositivoForm,
)
from .htmx import htmx_success_or_redirect, htmx_trigger_response
from .models import CentroCosto, Departamento, EstadoDispositivo, Fabricante, Modelo, TipoDispositivo


class FabricanteFormBaseView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Base para crear/editar fabricantes conservando contrato HTMX actual."""

    template_name = "core/partials/fabricante_form.html"
    success_url = "core:fabricante_list"
    trigger_message = ""
    permission_required = ""
    raise_exception = True

    def get_instance(self, pk=None):
        return None

    def get_context_data(self, form, instance=None):
        context = {"form": form}
        if instance is not None:
            context["fabricante"] = instance
        return context

    def get(self, request, pk=None):
        instance = self.get_instance(pk)
        form = FabricanteForm(instance=instance)
        return render(request, self.template_name, self.get_context_data(form, instance))

    def post(self, request, pk=None):
        instance = self.get_instance(pk)
        form = FabricanteForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return htmx_success_or_redirect(
                request,
                redirect_url=self.success_url,
                trigger={"fabricanteListChanged": True, "showNotification": self.trigger_message},
            )
        return render(request, self.template_name, self.get_context_data(form, instance))


class FabricanteCreateView(FabricanteFormBaseView):
    permission_required = "core.add_fabricante"
    trigger_message = "Fabricante creado con éxito"


class FabricanteUpdateView(FabricanteFormBaseView):
    permission_required = "core.change_fabricante"
    trigger_message = "Fabricante actualizado"

    def get_instance(self, pk=None):
        return get_object_or_404(Fabricante, pk=pk)


class FabricanteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "core.delete_fabricante"
    raise_exception = True

    def _delete(self, pk):
        fabricante = get_object_or_404(Fabricante, pk=pk)
        if fabricante.modelos.exists():
            return htmx_trigger_response({"showNotification": {"message": "No se puede eliminar: tiene modelos asociados", "type": "error"}})
        fabricante.delete()
        return htmx_trigger_response({"fabricanteListChanged": True, "showNotification": "Fabricante eliminado"})

    def delete(self, request, pk):
        return self._delete(pk)

    def post(self, request, pk):
        return self._delete(pk)


class CatalogCreateViewBase(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Base para vistas de creación con contrato HTMX uniforme."""

    form_class = None
    template_name = ""
    success_url = ""
    trigger_payload = None
    raise_exception = True

    def get_initial(self, request):
        return {}

    def get_context_data(self, form):
        return {"form": form}

    def get(self, request):
        form = self.form_class(initial=self.get_initial(request))
        return render(request, self.template_name, self.get_context_data(form))

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            return htmx_success_or_redirect(
                request,
                redirect_url=self.success_url,
                trigger=self.trigger_payload,
            )
        return render(request, self.template_name, self.get_context_data(form))


class CatalogUpdateViewBase(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Base para vistas de edición con contrato HTMX uniforme."""

    model = None
    form_class = None
    template_name = ""
    success_url = ""
    trigger_payload = None
    context_object_name = ""
    raise_exception = True

    def get_object(self, pk):
        return get_object_or_404(self.model, pk=pk)

    def get_context_data(self, form, obj):
        context = {"form": form}
        if self.context_object_name:
            context[self.context_object_name] = obj
        return context

    def get(self, request, pk):
        obj = self.get_object(pk)
        form = self.form_class(instance=obj)
        return render(request, self.template_name, self.get_context_data(form, obj))

    def post(self, request, pk):
        obj = self.get_object(pk)
        form = self.form_class(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return htmx_success_or_redirect(
                request,
                redirect_url=self.success_url,
                trigger=self.trigger_payload,
            )
        return render(request, self.template_name, self.get_context_data(form, obj))


class CatalogDeleteViewBase(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Base para eliminación con validaciones custom por entidad."""

    model = None
    trigger_payload = None
    raise_exception = True

    def get_object(self, pk):
        return get_object_or_404(self.model, pk=pk)

    def get_protection_response(self, obj):
        return None

    def _delete(self, pk):
        obj = self.get_object(pk)
        protection_response = self.get_protection_response(obj)
        if protection_response is not None:
            return protection_response
        obj.delete()
        return htmx_trigger_response(self.trigger_payload)

    def delete(self, request, pk):
        return self._delete(pk)

    def post(self, request, pk):
        return self._delete(pk)


class ModeloCreateView(CatalogCreateViewBase):
    permission_required = "core.add_modelo"
    form_class = ModeloForm
    template_name = "core/partials/modelo_form.html"
    success_url = "core:modelo_list"
    trigger_payload = {
        "modeloListChanged": True,
        "fabricanteListChanged": True,
        "showNotification": "Modelo creado",
    }

    def get_initial(self, request):
        initial = {}
        if request.GET.get("fabricante_id"):
            fabricante_id = request.GET.get("fabricante_id")
            initial["fabricante"] = fabricante_id
            # Preseleccionar tipo desde el primer modelo existente del fabricante (si existe)
            modelo_existente = Modelo.objects.filter(fabricante_id=fabricante_id).select_related("tipo_dispositivo").first()
            if modelo_existente:
                initial["tipo_dispositivo"] = modelo_existente.tipo_dispositivo_id
        return initial


class ModeloUpdateView(CatalogUpdateViewBase):
    permission_required = "core.change_modelo"
    model = Modelo
    form_class = ModeloForm
    template_name = "core/partials/modelo_form.html"
    success_url = "core:modelo_list"
    context_object_name = "modelo"
    trigger_payload = {
        "modeloListChanged": True,
        "fabricanteListChanged": True,
        "showNotification": "Modelo actualizado",
    }


class ModeloDeleteView(CatalogDeleteViewBase):
    permission_required = "core.delete_modelo"
    model = Modelo
    trigger_payload = {"modeloListChanged": True, "fabricanteListChanged": True, "showNotification": "Modelo eliminado"}

    def get_protection_response(self, obj):
        if Dispositivo.objects.filter(modelo=obj).exists():
            return htmx_trigger_response({"showNotification": {"message": "Protegido: Existen dispositivos de este modelo", "type": "error"}})
        return None


class TipoCreateView(CatalogCreateViewBase):
    permission_required = "core.add_tipodispositivo"
    form_class = TipoDispositivoForm
    template_name = "core/partials/tipo_form.html"
    success_url = "core:tipodispositivo_list"
    trigger_payload = {"tipoListChanged": True, "showNotification": "Tipo de dispositivo creado"}


class TipoUpdateView(CatalogUpdateViewBase):
    permission_required = "core.change_tipodispositivo"
    model = TipoDispositivo
    form_class = TipoDispositivoForm
    template_name = "core/partials/tipo_form.html"
    success_url = "core:tipodispositivo_list"
    context_object_name = "tipo"
    trigger_payload = {"tipoListChanged": True, "showNotification": "Tipo de dispositivo actualizado"}


class TipoDeleteView(CatalogDeleteViewBase):
    permission_required = "core.delete_tipodispositivo"
    model = TipoDispositivo
    trigger_payload = {"tipoListChanged": True, "showNotification": "Tipo de dispositivo eliminado"}

    def get_protection_response(self, obj):
        if Dispositivo.objects.filter(modelo__tipo_dispositivo=obj).exists():
            return htmx_trigger_response({"showNotification": {"message": "Protegido: Existen dispositivos de este tipo", "type": "error"}})
        return None


class CentroCostoCreateView(CatalogCreateViewBase):
    permission_required = "core.add_centrocosto"
    form_class = CentroCostoForm
    template_name = "core/partials/cc_form.html"
    success_url = "core:centrocosto_list"
    trigger_payload = {"ccListChanged": True, "showNotification": "Centro de costo creado"}


class CentroCostoUpdateView(CatalogUpdateViewBase):
    permission_required = "core.change_centrocosto"
    model = CentroCosto
    form_class = CentroCostoForm
    template_name = "core/partials/cc_form.html"
    success_url = "core:centrocosto_list"
    context_object_name = "cc"
    trigger_payload = {"ccListChanged": True, "showNotification": "Centro de costo actualizado"}


class EstadoCreateView(CatalogCreateViewBase):
    permission_required = "core.add_estadodispositivo"
    form_class = EstadoDispositivoForm
    template_name = "core/partials/estado_form.html"
    success_url = "core:estadodispositivo_list"
    trigger_payload = {"estadoListChanged": True, "showNotification": "Estado creado"}


class EstadoUpdateView(CatalogUpdateViewBase):
    permission_required = "core.change_estadodispositivo"
    model = EstadoDispositivo
    form_class = EstadoDispositivoForm
    template_name = "core/partials/estado_form.html"
    success_url = "core:estadodispositivo_list"
    context_object_name = "estado"
    trigger_payload = {"estadoListChanged": True, "showNotification": "Estado actualizado"}


class EstadoDeleteView(CatalogDeleteViewBase):
    permission_required = "core.delete_estadodispositivo"
    model = EstadoDispositivo
    trigger_payload = {"estadoListChanged": True, "showNotification": "Estado eliminado"}

    def get_protection_response(self, obj):
        if Dispositivo.objects.filter(estado=obj).exists():
            return htmx_trigger_response({"showNotification": {"message": "Protegido: Existen dispositivos en este estado", "type": "error"}})
        return None


class DepartamentoCreateView(CatalogCreateViewBase):
    permission_required = "core.add_departamento"
    form_class = DepartamentoForm
    template_name = "core/partials/departamento_form.html"
    success_url = "core:departamento_list"
    trigger_payload = {"departamentoListChanged": True, "showNotification": "Departamento creado"}


class DepartamentoUpdateView(CatalogUpdateViewBase):
    permission_required = "core.change_departamento"
    model = Departamento
    form_class = DepartamentoForm
    template_name = "core/partials/departamento_form.html"
    success_url = "core:departamento_list"
    context_object_name = "departamento"
    trigger_payload = {"departamentoListChanged": True, "showNotification": "Departamento actualizado"}


class DepartamentoDeleteView(CatalogDeleteViewBase):
    permission_required = "core.delete_departamento"
    model = Departamento
    trigger_payload = {"departamentoListChanged": True, "showNotification": "Departamento eliminado"}

    def get_protection_response(self, obj):
        from colaboradores.models import Colaborador
        if Colaborador.objects.filter(departamento=obj).exists():
            return htmx_trigger_response({"showNotification": {"message": "Protegido: Existen colaboradores en este departamento", "type": "error"}})
        return None
