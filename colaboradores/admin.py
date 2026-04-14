from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Colaborador

@admin.register(Colaborador)
class ColaboradorAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'rut', 'centro_costo', 'esta_activo')
    list_filter = ('esta_activo', 'centro_costo', 'departamento')
    fieldsets = UserAdmin.fieldsets + (
        ('Información Corporativa', {'fields': ('rut', 'cargo', 'departamento', 'centro_costo', 'azure_id', 'esta_activo')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Corporativa', {'fields': ('rut', 'cargo', 'departamento', 'centro_costo', 'azure_id', 'esta_activo')}),
    )
    search_fields = ('username', 'first_name', 'last_name', 'rut')
