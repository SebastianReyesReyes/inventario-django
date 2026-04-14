import os
import pytest
import django

def pytest_configure():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario_jmie.settings')
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    django.setup()
