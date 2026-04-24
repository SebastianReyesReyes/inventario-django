import re

from django import forms

from core.forms import BaseStyledForm
from core.utils import validar_rut_chileno
from .models import Colaborador


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
            if not validar_rut_chileno(rut):
                raise forms.ValidationError(
                    "El RUT ingresado no es válido o tiene un formato incorrecto."
                )

            # Limpiar para procesar: solo números y K
            rut_limpio = re.sub(r'[^0-9kK]', '', str(rut)).upper()
            cuerpo = rut_limpio[:-1]
            dv = rut_limpio[-1]

            # Formatear cuerpo con puntos
            cuerpo_formateado = ""
            for i, char in enumerate(reversed(cuerpo)):
                if i > 0 and i % 3 == 0:
                    cuerpo_formateado += "."
                cuerpo_formateado += char
            cuerpo_formateado = cuerpo_formateado[::-1]

            return f"{cuerpo_formateado}-{dv}"
        return rut
