import pytest
from django.http import HttpRequest
from django.core.paginator import Paginator
from core.pagination import paginate_queryset


@pytest.mark.django_db
class TestPaginateQueryset:
    def test_returns_correct_page(self):
        request = HttpRequest()
        request.GET = {'page': '2'}
        qs = list(range(25))  # simula 25 items
        page_obj = paginate_queryset(request, qs, per_page=10)
        assert page_obj.number == 2
        assert len(page_obj) == 10

    def test_invalid_string_page_fallback_to_one(self):
        request = HttpRequest()
        request.GET = {'page': 'abc'}
        request.path = '/test/'
        qs = list(range(25))
        page_obj = paginate_queryset(request, qs, per_page=10)
        assert page_obj.number == 1

    def test_empty_page_fallback_to_one(self):
        request = HttpRequest()
        request.GET = {'page': '999'}
        request.path = '/test/'
        qs = list(range(5))
        page_obj = paginate_queryset(request, qs, per_page=10)
        assert page_obj.number == 1
