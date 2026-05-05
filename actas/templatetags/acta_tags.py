from django import template

register = template.Library()

@register.filter(name='format_rut')
def format_rut(value):
    """
    Formatea un RUT string (ej: 12345678K) a formato XX.XXX.XXX-X
    """
    if not value or len(str(value).strip()) == 0:
        return ""
    
    # Limpiar el RUT de cualquier caracter que no sea número o K
    import re
    cleaned = re.sub(r'[^0-9kK]', '', str(value))
    
    if len(cleaned) < 2:
        return cleaned.upper()
    
    rut = cleaned.upper()
    cuerpo = rut[:-1]
    dv = rut[-1]
    
    # Formatear el cuerpo con puntos
    cuerpo_formateado = ""
    while len(cuerpo) > 3:
        cuerpo_formateado = "." + cuerpo[-3:] + cuerpo_formateado
        cuerpo = cuerpo[:-3]
    cuerpo_formateado = cuerpo + cuerpo_formateado
    
    return f"{cuerpo_formateado}-{dv}"

@register.filter(name='currency_clp')
def currency_clp(value):
    """
    Formatea un valor numérico a formato moneda chilena con puntos (ej: 1.000)
    """
    if value is None or value == "":
        return "0"
    try:
        # Convertir a entero y usar el separador de miles de Python (,) para luego cambiarlo a (.)
        return f"{int(float(value)):,}".replace(",", ".")
    except (ValueError, TypeError):
        return value
