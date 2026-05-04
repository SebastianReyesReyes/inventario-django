"""Servicios de lectura para métricas y series del dashboard."""

from datetime import timedelta
import json

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from colaboradores.models import Colaborador
from core.models import EstadoDispositivo, TipoDispositivo
from dispositivos.models import BitacoraMantenimiento, Dispositivo


class DashboardMetricsService:
    """Calcula métricas y datasets para la vista principal del dashboard."""

    MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    _static_cache = {}

    @classmethod
    def _get_cached_id(cls, key, model, **kwargs):
        """Cache interno de PKs para evitar consultas repetitivas a estados/tipos estáticos."""
        if key not in cls._static_cache:
            pk = model.objects.filter(**kwargs).values_list("id", flat=True).first()
            if pk is not None:
                cls._static_cache[key] = pk
        return cls._static_cache.get(key, "")

    @classmethod
    def build_context(cls, filtered_qs, filterset, top10_metric):
        total_dispositivos = filtered_qs.count()

        disponible_estado_id = cls._get_cached_id(
            "disponible_estado", EstadoDispositivo, nombre__in=["Disponible", "Reservado"]
        )
        mantenimiento_estado_id = cls._get_cached_id(
            "mantenimiento_estado", EstadoDispositivo, nombre__icontains="Reparación"
        )

        tipo_notebook_id = cls._get_cached_id(
            "tipo_notebook", TipoDispositivo, nombre__icontains="Notebook"
        )
        tipo_smartphone_id = cls._get_cached_id(
            "tipo_smartphone", TipoDispositivo, nombre__icontains="Smartphone"
        )
        tipo_impresora_id = cls._get_cached_id(
            "tipo_impresora", TipoDispositivo, nombre__icontains="Impresora"
        )

        total_disponibles = filtered_qs.filter(estado__nombre__in=["Disponible", "Reservado"]).count()
        total_asignados = filtered_qs.filter(estado__nombre__in=["Asignado", "En uso"]).count()
        total_mantenimiento = filtered_qs.filter(estado__nombre__icontains="Reparación").count()
        total_baja = filtered_qs.filter(estado__nombre__in=["Fuera de Inventario", "De Baja", "Inactivo"]).count()

        total_valor = filtered_qs.aggregate(total=Sum("valor_contable"))["total"] or 0
        costo_mantenimiento = (
            BitacoraMantenimiento.objects.filter(dispositivo__in=filtered_qs).aggregate(total=Sum("costo_reparacion"))["total"]
            or 0
        )

        total_activos = total_dispositivos - total_baja
        porcentaje_asignados = round((total_asignados / total_activos * 100) if total_activos > 0 else 0)

        total_notebooks_disponibles = filtered_qs.filter(
            modelo__tipo_dispositivo__nombre__icontains="Notebook",
            estado__nombre__in=["Disponible", "Reservado"],
        ).count()
        total_smartphones_disponibles = filtered_qs.filter(
            modelo__tipo_dispositivo__nombre__icontains="Smartphone",
            estado__nombre__in=["Disponible", "Reservado"],
        ).count()
        total_impresoras_disponibles = Dispositivo.objects.filter(
            modelo__tipo_dispositivo__nombre__icontains="Impresora",
            estado__nombre__in=["Disponible", "Reservado"],
        ).count()

        total_colaboradores = Colaborador.objects.filter(esta_activo=True).count()
        mantenimientos_recientes = BitacoraMantenimiento.objects.filter(
            dispositivo__in=filtered_qs,
            fecha__gte=timezone.now() - timedelta(days=30),
        ).count()

        chart_tipo_data = list(filtered_qs.values("modelo__tipo_dispositivo__nombre").annotate(total=Count("id")).order_by("-total"))
        chart_estado_data = list(filtered_qs.values("estado__nombre").annotate(total=Count("id")).order_by("-total"))

        if top10_metric == "precio":
            cc_query = (
                filtered_qs.values("centro_costo__codigo_contable", "centro_costo__nombre")
                .annotate(total=Sum("valor_contable"))
                .order_by("-total")[:10]
            )
        else:
            cc_query = (
                filtered_qs.values("centro_costo__codigo_contable", "centro_costo__nombre")
                .annotate(total=Count("id"))
                .order_by("-total")[:10]
            )
        chart_cc_data = list(cc_query)

        doce_meses_atras = timezone.now() - timedelta(days=365)
        chart_adquisiciones_data = list(
            filtered_qs.filter(fecha_compra__gte=doce_meses_atras)
            .annotate(mes_compra=TruncMonth("fecha_compra"))
            .values("mes_compra")
            .annotate(total=Count("id"))
            .order_by("mes_compra")
        )

        chart_adq_labels_list = [cls._format_month(item["mes_compra"]) for item in chart_adquisiciones_data]
        chart_adq_values_list = [item["total"] for item in chart_adquisiciones_data]

        return {
            "filter": filterset,
            "top10_metric": top10_metric,
            "total_disponibles": total_disponibles,
            "total_disponibles_id": disponible_estado_id,
            "total_asignados": total_asignados,
            "total_mantenimiento": total_mantenimiento,
            "total_mantenimiento_id": mantenimiento_estado_id,
            "total_baja": total_baja,
            "total_dispositivos": total_dispositivos,
            "total_colaboradores": total_colaboradores,
            "porcentaje_asignados": porcentaje_asignados,
            "mantenimientos_recientes": mantenimientos_recientes,
            "total_valor": total_valor,
            "costo_mantenimiento": costo_mantenimiento,
            "total_notebooks_disponibles": total_notebooks_disponibles,
            "total_smartphones_disponibles": total_smartphones_disponibles,
            "total_impresoras_disponibles": total_impresoras_disponibles,
            "tipo_notebook_id": tipo_notebook_id,
            "tipo_smartphone_id": tipo_smartphone_id,
            "tipo_impresora_id": tipo_impresora_id,
            "chart_tipo_labels": json.dumps([item["modelo__tipo_dispositivo__nombre"] or "Sin Categoría" for item in chart_tipo_data]),
            "chart_tipo_values": json.dumps([item["total"] for item in chart_tipo_data]),
            "chart_estado_labels": json.dumps([item["estado__nombre"] or "Estado Desconocido" for item in chart_estado_data]),
            "chart_estado_values": json.dumps([item["total"] for item in chart_estado_data]),
            "chart_cc_labels": json.dumps(
                [
                    f"{item['centro_costo__codigo_contable']} - {item['centro_costo__nombre']}"
                    if item["centro_costo__codigo_contable"]
                    else "Central/Stock"
                    for item in chart_cc_data
                ]
            ),
            "chart_cc_values": json.dumps([float(item["total"]) if item["total"] else 0 for item in chart_cc_data]),
            "chart_adq_labels": json.dumps(chart_adq_labels_list),
            "chart_adq_values": json.dumps(chart_adq_values_list),
        }

    @classmethod
    def _format_month(cls, dt):
        if not dt:
            return ""
        return f"{cls.MESES_ES[dt.month - 1]} {dt.year}"
