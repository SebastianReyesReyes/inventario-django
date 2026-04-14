from django.apps import AppConfig


class DispositivosConfig(AppConfig):
    name = 'dispositivos'

    def ready(self):
        import dispositivos.signals
