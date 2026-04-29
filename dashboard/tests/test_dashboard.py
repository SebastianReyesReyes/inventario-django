import pytest
from django.urls import reverse
from core.tests.factories import (
    ColaboradorFactory, DispositivoFactory, 
    EstadoDispositivoFactory, TipoDispositivoFactory, ModeloFactory
)
from core.models import EstadoDispositivo, TipoDispositivo

@pytest.mark.django_db
class TestDashboardAnalytics:
    @pytest.fixture
    def setup_data(self):
        # Aseguramos que existan los estados que la vista dashboard/views.py busca
        # (Usa nombres exactos como 'Disponible', 'Asignado', etc.)
        self.est_disponible = EstadoDispositivoFactory(nombre='Disponible')
        self.est_reparacion = EstadoDispositivoFactory(nombre='En Reparación')
        self.est_baja = EstadoDispositivoFactory(nombre='De Baja')
        
        self.tipo_nb = TipoDispositivoFactory(nombre='Notebook')
        self.tipo_sp = TipoDispositivoFactory(nombre='Smartphone')
        
        self.modelo_nb = ModeloFactory(tipo_dispositivo=self.tipo_nb)
        self.modelo_sp = ModeloFactory(tipo_dispositivo=self.tipo_sp)

        # Crear dispositivos con diferentes estados y modelos
        DispositivoFactory.create_batch(3, estado=self.est_disponible, modelo=self.modelo_nb)
        DispositivoFactory.create_batch(2, estado=self.est_reparacion, modelo=self.modelo_sp)
        DispositivoFactory.create_batch(1, estado=self.est_baja, modelo=self.modelo_nb)

    def test_dashboard_metrics_no_filter(self, client, setup_data):
        """Validar que el dashboard cuenta correctamente sin filtros aplicados"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        
        url = reverse('dashboard:principal')
        response = client.get(url)
        
        assert response.status_code == 200
        context = response.context
        
        # 3 disponibles + 2 reparación + 1 baja = 6 total
        assert context['total_dispositivos'] == 6
        assert context['total_disponibles'] == 3
        assert context['total_mantenimiento'] == 2
        assert context['total_baja'] == 1
        
        # Notebooks disponibles (3 creadas)
        assert context['total_notebooks_disponibles'] == 3

    def test_dashboard_metrics_with_filter(self, client, setup_data):
        """Validar que el dashboard reacciona a los filtros (ej. filtrar por Notebook)"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        
        url = reverse('dashboard:principal')
        # Filtramos por tipo Notebook (ID de self.tipo_nb)
        response = client.get(url, {'tipo': self.tipo_nb.id})
        
        assert response.status_code == 200
        context = response.context
        
        # Solo hay 4 Notebooks en total (3 disp + 1 baja)
        assert context['total_dispositivos'] == 4
        assert context['total_disponibles'] == 3
        assert context['total_mantenimiento'] == 0 # Las de reparación eran Smartphones
        assert context['total_baja'] == 1

    def test_dashboard_charts_json_data(self, client, setup_data):
        """Validar que los datos para Chart.js se serializan correctamente"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        
        url = reverse('dashboard:principal')
        response = client.get(url)
        
        import json
        # chart_tipo_values debería tener [4, 2] (4 notebooks, 2 smartphones)
        values = json.loads(context := response.context['chart_tipo_values'])
        assert 4 in values
        assert 2 in values
        assert len(values) == 2

    def test_dashboard_htmx_partial(self, client, setup_data):
        """Validar que el dashboard soporta actualizaciones parciales vía HTMX"""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')
        
        url = reverse('dashboard:principal')
        response = client.get(url, HTTP_HX_REQUEST='true')
        
        assert response.status_code == 200
        # Debe usar el partial, no el layout completo
        assert 'dashboard/partials/dashboard_content.html' in [t.name for t in response.templates]
        assert '<html' not in response.content.decode('utf-8')

    def test_dashboard_context_keys_integrity(self, client, setup_data):
        """Validar que las llaves de contexto críticas sigan disponibles."""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')

        url = reverse('dashboard:principal')
        response = client.get(url)
        assert response.status_code == 200

        context = response.context
        expected_keys = [
            'total_dispositivos',
            'total_disponibles',
            'total_asignados',
            'total_mantenimiento',
            'total_baja',
            'chart_tipo_labels',
            'chart_tipo_values',
            'chart_estado_labels',
            'chart_estado_values',
            'chart_cc_labels',
            'chart_cc_values',
            'chart_adq_labels',
            'chart_adq_values',
        ]
        for key in expected_keys:
            assert key in context

    def test_dashboard_top10_metric_precio(self, client, setup_data):
        """Validar cálculo de top10 por precio sin romper el contexto."""
        user = ColaboradorFactory(is_staff=True, is_superuser=True)
        user.set_password('password')
        user.save()
        client.login(username=user.username, password='password')

        url = reverse('dashboard:principal')
        response = client.get(url, {'top10_metric': 'precio'})
        assert response.status_code == 200
        assert response.context['top10_metric'] == 'precio'
