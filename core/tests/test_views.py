import json

import pytest
from django.urls import reverse

from core.tests.factories import (
    ColaboradorFactory,
    DispositivoFactory,
    EstadoDispositivoFactory,
    FabricanteFactory,
    ModeloFactory,
    TipoDispositivoFactory,
    CentroCostoFactory,
)


@pytest.mark.django_db
class TestCoreCatalogViews:
    @pytest.fixture
    def admin_client(self, client):
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password("password")
        user.save()
        client.login(username=user.username, password="password")
        return client

    @pytest.fixture
    def no_perms_client(self, client):
        user = ColaboradorFactory(is_staff=True, is_superuser=False)
        user.set_password("password")
        user.save()
        client.login(username=user.username, password="password")
        return client

    # --- Permisos negativos (403) ---
    def test_fabricante_create_no_permission_returns_403(self, no_perms_client):
        response = no_perms_client.post(reverse("core:fabricante_create"), {"nombre": "HP"})
        assert response.status_code == 403

    def test_fabricante_edit_no_permission_returns_403(self, no_perms_client):
        fabricante = FabricanteFactory()
        response = no_perms_client.post(
            reverse("core:fabricante_update", kwargs={"pk": fabricante.pk}),
            {"nombre": "HP"},
        )
        assert response.status_code == 403

    def test_fabricante_delete_no_permission_returns_403(self, no_perms_client):
        fabricante = FabricanteFactory()
        response = no_perms_client.delete(
            reverse("core:fabricante_delete", kwargs={"pk": fabricante.pk})
        )
        assert response.status_code == 403

    def test_modelo_create_no_permission_returns_403(self, no_perms_client):
        response = no_perms_client.post(reverse("core:modelo_create"), {"nombre": "X"})
        assert response.status_code == 403

    def test_modelo_edit_no_permission_returns_403(self, no_perms_client):
        modelo = ModeloFactory()
        response = no_perms_client.post(
            reverse("core:modelo_update", kwargs={"pk": modelo.pk}),
            {"nombre": "X"},
        )
        assert response.status_code == 403

    def test_modelo_delete_no_permission_returns_403(self, no_perms_client):
        modelo = ModeloFactory()
        response = no_perms_client.delete(
            reverse("core:modelo_delete", kwargs={"pk": modelo.pk})
        )
        assert response.status_code == 403

    def test_tipo_create_no_permission_returns_403(self, no_perms_client):
        response = no_perms_client.post(
            reverse("core:tipodispositivo_create"), {"nombre": "Tablet", "sigla": "T"}
        )
        assert response.status_code == 403

    def test_tipo_edit_no_permission_returns_403(self, no_perms_client):
        tipo = TipoDispositivoFactory()
        response = no_perms_client.post(
            reverse("core:tipodispositivo_update", kwargs={"pk": tipo.pk}),
            {"nombre": "Tablet", "sigla": "T"},
        )
        assert response.status_code == 403

    def test_tipo_delete_no_permission_returns_403(self, no_perms_client):
        tipo = TipoDispositivoFactory()
        response = no_perms_client.delete(
            reverse("core:tipodispositivo_delete", kwargs={"pk": tipo.pk})
        )
        assert response.status_code == 403

    def test_cc_create_no_permission_returns_403(self, no_perms_client):
        response = no_perms_client.post(reverse("core:centrocosto_create"), {"nombre": "X"})
        assert response.status_code == 403

    def test_cc_edit_no_permission_returns_403(self, no_perms_client):
        cc = CentroCostoFactory()
        response = no_perms_client.post(
            reverse("core:centrocosto_update", kwargs={"pk": cc.pk}),
            {"nombre": "X"},
        )
        assert response.status_code == 403

    def test_estado_create_no_permission_returns_403(self, no_perms_client):
        response = no_perms_client.post(
            reverse("core:estadodispositivo_create"), {"nombre": "X", "color": "#000"}
        )
        assert response.status_code == 403

    def test_estado_edit_no_permission_returns_403(self, no_perms_client):
        estado = EstadoDispositivoFactory()
        response = no_perms_client.post(
            reverse("core:estadodispositivo_update", kwargs={"pk": estado.pk}),
            {"nombre": "X", "color": "#000"},
        )
        assert response.status_code == 403

    def test_estado_delete_no_permission_returns_403(self, no_perms_client):
        estado = EstadoDispositivoFactory()
        response = no_perms_client.delete(
            reverse("core:estadodispositivo_delete", kwargs={"pk": estado.pk})
        )
        assert response.status_code == 403

    def test_cc_toggle_activa_no_permission_returns_403(self, no_perms_client):
        cc = CentroCostoFactory()
        response = no_perms_client.post(
            reverse("core:centrocosto_toggle_activa", kwargs={"pk": cc.pk})
        )
        assert response.status_code == 403

    # --- Flujos exitosos HTMX ---
    def test_fabricante_create_htmx_trigger(self, admin_client):
        response = admin_client.post(
            reverse("core:fabricante_create"),
            {"nombre": "HP"},
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 204
        trigger = json.loads(response["HX-Trigger"])
        assert trigger["fabricanteListChanged"] is True
        assert trigger["showNotification"] == "Fabricante creado con éxito"

    def test_fabricante_create_redirect_non_htmx(self, admin_client):
        response = admin_client.post(reverse("core:fabricante_create"), {"nombre": "Lenovo"})
        assert response.status_code == 302
        assert response.url == reverse("core:fabricante_list")

    def test_fabricante_delete_protected(self, admin_client):
        fabricante = FabricanteFactory(nombre="Dell")
        ModeloFactory(fabricante=fabricante)

        response = admin_client.delete(reverse("core:fabricante_delete", kwargs={"pk": fabricante.pk}))
        assert response.status_code == 204
        trigger = json.loads(response["HX-Trigger"])
        assert "No se puede eliminar" in trigger["showNotification"]["message"]

    def test_fabricante_delete_success_trigger(self, admin_client):
        fabricante = FabricanteFactory(nombre="Acer")

        response = admin_client.delete(reverse("core:fabricante_delete", kwargs={"pk": fabricante.pk}))
        assert response.status_code == 204
        trigger = json.loads(response["HX-Trigger"])
        assert trigger["fabricanteListChanged"] is True

    def test_modelo_create_htmx_trigger(self, admin_client):
        fabricante = FabricanteFactory(nombre="Samsung")
        tipo = TipoDispositivoFactory()
        response = admin_client.post(
            reverse("core:modelo_create"),
            {"nombre": "Galaxy Book", "fabricante": fabricante.pk, "tipo_dispositivo": tipo.pk},
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 204
        trigger = json.loads(response["HX-Trigger"])
        assert trigger["modeloListChanged"] is True
        assert trigger["fabricanteListChanged"] is True

    def test_modelo_delete_protected(self, admin_client):
        modelo = ModeloFactory()
        DispositivoFactory(modelo=modelo)

        response = admin_client.delete(reverse("core:modelo_delete", kwargs={"pk": modelo.pk}))
        assert response.status_code == 204
        trigger = json.loads(response["HX-Trigger"])
        assert "Protegido" in trigger["showNotification"]["message"]

    def test_modelo_delete_success_trigger(self, admin_client):
        modelo = ModeloFactory()

        response = admin_client.delete(reverse("core:modelo_delete", kwargs={"pk": modelo.pk}))
        assert response.status_code == 204
        trigger = json.loads(response["HX-Trigger"])
        assert trigger["modeloListChanged"] is True
        assert trigger["fabricanteListChanged"] is True

    def test_tipo_create_htmx_trigger(self, admin_client):
        response = admin_client.post(
            reverse("core:tipodispositivo_create"),
            {"nombre": "Tablet", "sigla": "TBLT"},
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 204
        trigger = json.loads(response["HX-Trigger"])
        assert trigger["tipoListChanged"] is True

    def test_tipo_delete_protected_trigger(self, admin_client):
        tipo = TipoDispositivoFactory(nombre="Servidor")
        modelo = ModeloFactory(tipo_dispositivo=tipo)
        DispositivoFactory(modelo=modelo)

        response = admin_client.delete(reverse("core:tipodispositivo_delete", kwargs={"pk": tipo.pk}))
        assert response.status_code == 204
        trigger = json.loads(response["HX-Trigger"])
        assert "Protegido" in trigger["showNotification"]["message"]

    def test_cc_toggle_activa_trigger(self, admin_client):
        cc = CentroCostoFactory(activa=True)

        response = admin_client.post(reverse("core:centrocosto_toggle_activa", kwargs={"pk": cc.pk}))
        assert response.status_code == 204
        trigger = json.loads(response["HX-Trigger"])
        assert trigger["ccListChanged"] is True
        assert "desactivado" in trigger["showNotification"]

    def test_estado_create_htmx_trigger(self, admin_client):
        response = admin_client.post(
            reverse("core:estadodispositivo_create"),
            {"nombre": "Retirado", "color": "#111111"},
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 204
        trigger = json.loads(response["HX-Trigger"])
        assert trigger["estadoListChanged"] is True

    def test_estado_delete_protected_trigger(self, admin_client):
        estado = EstadoDispositivoFactory(nombre="Asignado")
        DispositivoFactory(estado=estado)

        response = admin_client.delete(reverse("core:estadodispositivo_delete", kwargs={"pk": estado.pk}))
        assert response.status_code == 204
        trigger = json.loads(response["HX-Trigger"])
        assert "Protegido" in trigger["showNotification"]["message"]

    def test_fabricante_list_paginated(self, admin_client):
        for i in range(15):
            FabricanteFactory(nombre=f"Fab {i}")
        response = admin_client.get(reverse("core:fabricante_list"))
        assert response.status_code == 200
        assert "page_obj" in response.context
        assert len(response.context["page_obj"]) <= 10

    def test_modelo_list_paginated(self, admin_client):
        fabricante = FabricanteFactory()
        tipo = TipoDispositivoFactory()
        for i in range(15):
            ModeloFactory(nombre=f"Modelo {i}", fabricante=fabricante, tipo_dispositivo=tipo)
        response = admin_client.get(reverse("core:modelo_list"))
        assert response.status_code == 200
        assert "page_obj" in response.context
        assert len(response.context["page_obj"]) <= 10

@pytest.mark.django_db
class TestCoreAuxiliaryViews:
    @pytest.fixture
    def logged_client(self, client):
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password("password")
        user.save()
        client.login(username=user.username, password="password")
        return client

    def test_home_renders_with_context(self, logged_client):
        response = logged_client.get(reverse("home"))
        assert response.status_code == 200
        assert "mantenimientos_pendientes" in response.context
        assert "asignaciones_sin_acta" in response.context
        assert "total_dispositivos" in response.context

    def test_dashboard_drill_down_filter_disponibles(self, logged_client):
        est = EstadoDispositivoFactory(nombre="Disponible")
        DispositivoFactory(estado=est)
        response = logged_client.get(
            reverse("core:dashboard_drill_down"), {"filter_type": "disponibles"}
        )
        assert response.status_code == 200
        assert response.context["title"] == "Equipos Disponibles"

    def test_dashboard_drill_down_filter_asignados(self, logged_client):
        est = EstadoDispositivoFactory(nombre="Asignado")
        DispositivoFactory(estado=est)
        response = logged_client.get(
            reverse("core:dashboard_drill_down"), {"filter_type": "asignados"}
        )
        assert response.status_code == 200
        assert response.context["title"] == "Equipos Asignados"

    def test_dashboard_drill_down_filter_mantenimiento(self, logged_client):
        est = EstadoDispositivoFactory(nombre="En Reparación")
        DispositivoFactory(estado=est)
        response = logged_client.get(
            reverse("core:dashboard_drill_down"), {"filter_type": "mantenimiento"}
        )
        assert response.status_code == 200
        assert response.context["title"] == "Equipos en Mantención"

    def test_dashboard_drill_down_filter_baja(self, logged_client):
        est = EstadoDispositivoFactory(nombre="De Baja")
        DispositivoFactory(estado=est)
        response = logged_client.get(
            reverse("core:dashboard_drill_down"), {"filter_type": "baja"}
        )
        assert response.status_code == 200
        assert response.context["title"] == "Equipos Fuera de Inventario"
