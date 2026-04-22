from django import forms
from .models import Colaborador
from core.forms import BaseStyledForm
import re

def validar_rut(rut):
    """
    Validador de RUT chileno robusto.
    Acepta formatos: 12.345.678-k, 12345678-k, 12345678k, etc.
    """
    if not rut:
        return False
        
    # Limpiar todo lo que no sea dígito o K
    rut = re.sub(r'[^0-9kK]', '', str(rut)).upper()
    
    if len(rut) < 8 or len(rut) > 9:
        return False
    
    cuerpo = rut[:-1]
    dv = rut[-1]
    
    try:
        suma = 0
        multiplo = 2
        for c in reversed(cuerpo):
            suma += int(c) * multiplo
            multiplo = 2 if multiplo == 7 else multiplo + 1
        
        dvr = 11 - (suma % 11)
        dv_esperado = 'K' if dvr == 10 else '0' if dvr == 11 else str(dvr)
        
        return dv == dv_esperado
    except (ValueError, TypeError):
        return False

class ColaboradorForm(BaseStyledForm):
    class Meta:
        model = Colaborador
        fields = [
            'username', 'first_name', 'last_name', 'email', 
            'rut', 'cargo', 'departamento', 'centro_costo', 'azure_id'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Ej: jdoe'}),
            'rut': forms.TextInput(attrs={'placeholder': '12.345.678-k'}),
        }

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if rut:
            if not validar_rut(rut):
                raise forms.ValidationError("El RUT ingresado no es válido o tiene un formato incorrecto.")
            
            # Limpiar para procesar: solo números y K
            rut_limpio = re.sub(r'[^0-9kK]', '', str(rut)).upper()
            cuerpo = rut_limpio[:-1]
            dv = rut_limpio[-1]
            
            # Formatear cuerpo con puntos (DRY: Lógica de puntos)
            cuerpo_formateado = ""
            for i, char in enumerate(reversed(cuerpo)):
                if i > 0 and i % 3 == 0:
                    cuerpo_formateado += "."
                cuerpo_formateado += char
            cuerpo_formateado = cuerpo_formateado[::-1]
            
            return f"{cuerpo_formateado}-{dv}"
        return rut
