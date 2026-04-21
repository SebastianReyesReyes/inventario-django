"""Helpers para views HTMX del módulo dispositivos."""
from django.shortcuts import render, redirect
from django.http import HttpResponse


def is_htmx(request):
    """Detecta si el request proviene de HTMX."""
    return request.headers.get('HX-Request') == 'true'


def htmx_success(request, template, context, redirect_url, trigger=None):
    """
    Si es HTMX, renderiza el template parcial con trigger opcional.
    Si no, redirige a la URL indicada.
    """
    if is_htmx(request):
        response = render(request, template, context)
        if trigger:
            response['HX-Trigger'] = trigger
        return response
    return redirect(redirect_url)


def htmx_delete_success(request, redirect_url):
    """
    Respuesta para eliminación exitosa vía HTMX (204 + HX-Redirect)
    o redirect estándar.
    """
    if is_htmx(request):
        response = HttpResponse(status=204)
        response['HX-Redirect'] = redirect_url
        return response
    return redirect(redirect_url)
