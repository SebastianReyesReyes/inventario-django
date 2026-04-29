import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

logger = logging.getLogger(__name__)


def paginate_queryset(request, queryset, per_page=10):
    """
    Devuelve un page_obj paginado y maneja páginas inválidas
    redirigiendo silenciosamente a la página 1.
    """
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
        logger.warning(
            'Página inválida "%s" para %s, fallback a página 1',
            page_number, request.path
        )
    return page_obj
