"""Helpers compartidos para respuestas HTMX."""

import json

from django.http import HttpResponse
from django.shortcuts import redirect, render


def is_htmx(request):
    """Retorna True si la request viene desde HTMX."""
    return bool(request.headers.get("HX-Request"))


def htmx_trigger_response(trigger, status=204):
    """Construye una respuesta con header HX-Trigger."""
    response = HttpResponse(status=status)
    if trigger is not None:
        response["HX-Trigger"] = json.dumps(trigger) if isinstance(trigger, dict) else str(trigger)
    return response


def htmx_success_or_redirect(request, redirect_url, trigger=None, status=204):
    """Si es HTMX responde con trigger; de lo contrario redirige."""
    if is_htmx(request):
        return htmx_trigger_response(trigger=trigger, status=status)
    return redirect(redirect_url)


def htmx_render_or_redirect(request, template, context, redirect_url, trigger=None):
    """Si es HTMX renderiza parcial con trigger opcional; de lo contrario redirige."""
    if is_htmx(request):
        response = render(request, template, context)
        if trigger is not None:
            response["HX-Trigger"] = json.dumps(trigger) if isinstance(trigger, dict) else str(trigger)
        return response
    return redirect(redirect_url)


def htmx_redirect_or_redirect(request, redirect_url, status=204):
    """Si es HTMX responde con HX-Redirect; de lo contrario redirige."""
    if is_htmx(request):
        response = HttpResponse(status=status)
        response["HX-Redirect"] = redirect_url
        return response
    return redirect(redirect_url)
