from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()

@register.inclusion_tag('partials/action_buttons.html', takes_context=True)
def render_actions(context, obj, action_type='standard'):
    """
    Renderiza un set de botones de acción estandarizados (Ver, Editar, Eliminar).
    Uso: {% render_actions objeto 'inventory' %}
    """
    user = context['request'].user
    app_label = obj._meta.app_label
    model_name = obj._meta.model_name
    pk = obj.pk

    # Verificación de permisos base de Django
    can_change = user.has_perm(f"{app_label}.change_{model_name}")
    can_delete = user.has_perm(f"{app_label}.delete_{model_name}")
    can_view = user.has_perm(f"{app_label}.view_{model_name}")

    # URLs estándar siguiendo la convención JMIE: app:modelo_accion
    def get_url(action):
        try:
            return reverse(f"{app_label}:{model_name}_{action}", args=[pk])
        except NoReverseMatch:
            return None

    return {
        'obj': obj,
        'url_view': get_url('detail'),
        'url_update': get_url('update') or get_url('edit'),
        'url_delete': get_url('delete'),
        'url_toggle': get_url('toggle_activa') or get_url('toggle'),
        'can_change': can_change,
        'can_delete': can_delete,
        'can_view': can_view,
        'action_type': action_type, # 'inventory', 'personnel', 'catalog'
    }
