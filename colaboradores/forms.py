from django import forms
from .models import Colaborador
import re

def validar_rut(rut):
    """
    Validador simple de RUT chileno.
    """
    rut = rut.replace(".", "").replace("-", "").replace(" ", "").upper()
    if not re.match(r"^\d{7,8}[0-9K]$", rut):
        return False
    
    cuerpo = rut[:-1]
    dv = rut[-1]
    
    suma = 0
    multiplo = 2
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1
    
    dvr = 11 - (suma % 11)
    dv_esperado = 'K' if dvr == 10 else '0' if dvr == 11 else str(dvr)
    
    return dv == dv_esperado

class ColaboradorForm(forms.ModelForm):
    class Meta:
        model = Colaborador
        fields = [
            'username', 'first_name', 'last_name', 'email', 
            'rut', 'cargo', 'departamento', 'centro_costo', 'azure_id'
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full bg-surface-container-high border border-white/10 rounded-xl px-4 py-2 text-sm text-on-background focus:ring-2 focus:ring-jmie-blue/50 outline-none',
                'placeholder': 'Ej: jdoe'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full bg-surface-container-high border border-white/10 rounded-xl px-4 py-2 text-sm text-on-background focus:ring-2 focus:ring-jmie-blue/50 outline-none'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full bg-surface-container-high border border-white/10 rounded-xl px-4 py-2 text-sm text-on-background focus:ring-2 focus:ring-jmie-blue/50 outline-none'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full bg-surface-container-high border border-white/10 rounded-xl px-4 py-2 text-sm text-on-background focus:ring-2 focus:ring-jmie-blue/50 outline-none'
            }),
            'rut': forms.TextInput(attrs={
                'class': 'w-full bg-surface-container-high border border-white/10 rounded-xl px-4 py-2 text-sm text-on-background focus:ring-2 focus:ring-jmie-blue/50 outline-none',
                'placeholder': '12.345.678-k'
            }),
            'cargo': forms.TextInput(attrs={
                'class': 'w-full bg-surface-container-high border border-white/10 rounded-xl px-4 py-2 text-sm text-on-background focus:ring-2 focus:ring-jmie-blue/50 outline-none',
            }),
            'departamento': forms.Select(attrs={
                'class': 'w-full bg-surface-container-high border border-white/10 rounded-xl px-4 py-2 text-sm text-on-background focus:ring-2 focus:ring-jmie-blue/50 outline-none h-10'
            }),
            'centro_costo': forms.Select(attrs={
                'class': 'w-full bg-surface-container-high border border-white/10 rounded-xl px-4 py-2 text-sm text-on-background focus:ring-2 focus:ring-jmie-blue/50 outline-none h-10'
            }),
            'azure_id': forms.TextInput(attrs={
                'class': 'w-full bg-surface-container-high border border-white/10 rounded-xl px-4 py-2 text-sm text-on-background focus:ring-2 focus:ring-jmie-blue/50 outline-none'
            }),
        }

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if rut:
            # Limpiar formato
            rut_limpio = rut.replace(".", "").replace("-", "").upper()
            if not validar_rut(rut_limpio):
                raise forms.ValidationError("El RUT ingresado no es válido.")
            return rut_limpio
        return rut
