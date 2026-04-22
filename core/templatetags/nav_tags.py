from django import template
from django.urls import reverse, resolve

register = template.Library()

@register.simple_tag(takes_context=True)
def active_url(context, url_name, active_class="text-on-background bg-white/5 border-l-2 border-jmie-orange rounded-none", inactive_class="text-jmie-gray hover:text-on-background hover:bg-white/5", exact=False):
    """
    Returns active_class if the current request path matches the url_name.
    Otherwise returns inactive_class.
    If exact is True, requires an exact match.
    If exact is False, it also matches if the current path starts with the reverse(url_name).
    """
    request = context.get('request')
    if not request:
        return inactive_class

    try:
        current_path = request.path
        target_path = reverse(url_name)

        if exact:
            if current_path == target_path:
                return active_class
        else:
            # Special case for the root / so it doesn't match everything
            if target_path == '/' and current_path != '/':
                return inactive_class
            if current_path.startswith(target_path):
                return active_class
    except Exception:
        pass

    return inactive_class

@register.simple_tag(takes_context=True)
def active_icon(context, url_name, active_class="text-jmie-orange", inactive_class="group-hover:text-jmie-orange", exact=False):
    """
    Similar to active_url but for icons. Returns active_class if matched, else inactive_class.
    """
    request = context.get('request')
    if not request:
        return inactive_class

    try:
        current_path = request.path
        target_path = reverse(url_name)

        if exact:
            if current_path == target_path:
                return active_class
        else:
            if target_path == '/' and current_path != '/':
                return inactive_class
            if current_path.startswith(target_path):
                return active_class
    except Exception:
        pass

    return inactive_class
