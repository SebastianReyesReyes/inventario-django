from django import template

register = template.Library()

@register.simple_tag
def status_badge(estado):
    """
    Devuelve las clases CSS de Tailwind para un badge de estado.
    Acepta un string o un objeto con atributo .nombre
    """
    if estado is None:
        return "bg-white/5 text-jmie-gray border border-white/10"

    nombre = str(estado).lower() if isinstance(estado, str) else str(getattr(estado, 'nombre', '')).lower()

    if 'disponible' in nombre or 'bueno' in nombre:
        return "bg-success/10 text-success border border-success/20"
    elif 'asignado' in nombre:
        return "bg-jmie-blue/10 text-jmie-blue border border-jmie-blue/20"
    elif 'reparación' in nombre or 'falla' in nombre or 'daño' in nombre or 'dañado' in nombre:
        return "bg-jmie-orange/10 text-jmie-orange border border-jmie-orange/20"
    else:
        return "bg-white/5 text-jmie-gray border border-white/10"

@register.simple_tag
def acta_badge(esta_firmada):
    """
    Devuelve las clases CSS para el badge de acta (Firmada/Pendiente/Sin Acta).
    """
    if esta_firmada is True:
        return "bg-success/10 text-success border border-success/20"
    elif esta_firmada is False:
        return "bg-jmie-orange/10 text-jmie-orange border border-jmie-orange/20"
    else:
        return "bg-white/5 text-jmie-gray border border-white/10"

@register.simple_tag
def device_icon(tipo_nombre):
    """
    Devuelve el nombre del icono de Material Symbols basado en el tipo de dispositivo.
    """
    nombre = str(tipo_nombre).lower()
    
    if 'notebook' in nombre or 'laptop' in nombre or 'portátil' in nombre:
        return 'laptop_mac'
    elif 'desktop' in nombre or 'pc' in nombre or 'torre' in nombre:
        return 'desktop_windows'
    elif 'monitor' in nombre or 'pantalla' in nombre or 'display' in nombre:
        return 'monitor'
    elif 'teléfono' in nombre or 'smartphone' in nombre or 'celular' in nombre or 'phone' in nombre:
        return 'smartphone'
    elif 'tablet' in nombre or 'ipad' in nombre:
        return 'tablet_mac'
    elif 'impresora' in nombre or 'printer' in nombre:
        return 'print'
    elif 'servidor' in nombre or 'server' in nombre:
        return 'dns'
    elif 'router' in nombre or 'switch' in nombre or 'red' in nombre:
        return 'router'
    elif 'ups' in nombre or 'batería' in nombre:
        return 'battery_charging_full'
    elif 'proyector' in nombre or 'projector' in nombre:
        return 'videocam'
    elif 'scanner' in nombre or 'escáner' in nombre:
        return 'scanner'
    elif 'cámara' in nombre or 'camara' in nombre or 'camera' in nombre:
        return 'photo_camera'
    elif 'audífono' in nombre or 'headset' in nombre or 'auricular' in nombre:
        return 'headphones'
    elif 'teclado' in nombre or 'keyboard' in nombre:
        return 'keyboard'
    elif 'mouse' in nombre:
        return 'mouse'
    else:
        return 'devices'

@register.inclusion_tag('partials/empty_state.html')
def empty_state(icon='search_off', title='Sin resultados', subtitle='No se encontraron registros.', action_url=None, action_label=None, colspan=1):
    """
    Renderiza un estado vacío estandarizado para tablas y listas.
    """
    return {
        'icon': icon,
        'title': title,
        'subtitle': subtitle,
        'action_url': action_url,
        'action_label': action_label,
        'colspan': colspan,
    }
