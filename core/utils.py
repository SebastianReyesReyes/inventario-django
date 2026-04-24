import re
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


def validar_rut_chileno(rut: str) -> bool:
    """
    Valida un RUT chileno usando el algoritmo Módulo 11.

    Acepta formatos con o sin puntos y con guión, por ejemplo:
      - "12.345.678-9"
      - "12345678-9"
      - "123456789" (sin guión)

    Maneja el dígito verificador 'K'/'k' correctamente.
    """
    if not rut:
        return False

    # Limpiar: conservar solo dígitos y K
    rut_limpio = re.sub(r"[^0-9kK]", "", str(rut)).upper()

    if len(rut_limpio) < 8 or len(rut_limpio) > 9:
        return False

    cuerpo = rut_limpio[:-1]
    dv = rut_limpio[-1]

    if not cuerpo.isdigit():
        return False

    try:
        suma = 0
        multiplo = 2
        for c in reversed(cuerpo):
            suma += int(c) * multiplo
            multiplo = 2 if multiplo == 7 else multiplo + 1

        dvr = 11 - (suma % 11)
        dv_esperado = "K" if dvr == 10 else "0" if dvr == 11 else str(dvr)

        return dv == dv_esperado
    except (ValueError, TypeError):
        return False


@deconstructible
class RUTChilenoValidator:
    """
    Validador de Django para campos de modelo o formulario que contengan RUT chileno.
    """

    message = "El RUT ingresado no es válido o tiene un formato incorrecto."
    code = "invalid_rut"

    def __call__(self, value):
        if not validar_rut_chileno(value):
            raise ValidationError(self.message, code=self.code)

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.message == other.message
            and self.code == other.code
        )
