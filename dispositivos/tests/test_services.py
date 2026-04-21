import pytest
from dispositivos.services import DispositivoFactory as FormFactory
from dispositivos.forms import DispositivoForm, NotebookForm, SmartphoneForm, MonitorForm
from dispositivos.tests.factories import TipoDispositivoFactory

@pytest.mark.django_db
class TestDispositivoService:
    def test_get_form_class_por_nombre(self):
        """El factory de formularios debe mapear adecuadamente el formulario correcto usando el Tipo."""
        tipo_ntbk = TipoDispositivoFactory(nombre="Notebook")
        tipo_smart = TipoDispositivoFactory(nombre="Smartphone")
        tipo_monitor = TipoDispositivoFactory(nombre="Monitor")
        tipo_random = TipoDispositivoFactory(nombre="Router") # No está en los especializados
        
        assert FormFactory.get_form_class(tipo_ntbk.id) == NotebookForm
        assert FormFactory.get_form_class(tipo_smart.id) == SmartphoneForm
        assert FormFactory.get_form_class(tipo_monitor.id) == MonitorForm
        
        # Tipos no mapeados en FORM_MAP caen al default general
        assert FormFactory.get_form_class(tipo_random.id) == DispositivoForm
        
        # Id nulo o faltante
        assert FormFactory.get_form_class(None) == DispositivoForm

    def test_create_form_instance_vacio(self):
        """Debe instanciar NotebookForm basándose en su ID parametrizado al crear uno nuevo."""
        tipo_ntbk = TipoDispositivoFactory(nombre="Notebook")
        form_instance = FormFactory.create_form_instance(tipo_id=tipo_ntbk.id)
        
        assert isinstance(form_instance, NotebookForm)
        assert not form_instance.is_bound # Formulario vacío para GET
