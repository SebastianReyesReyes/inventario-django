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
    def _get_cached_obj(cls, key, model, **kwargs):
        """Cache interno para evitar consultas repetitivas a estados/tipos estáticos."""
        if key not in cls._static_cache:
            cls._static_cache[key] = model.objects.filter(**kwargs).first()
        return cls._static_cache[key]

    @classmethod
    def _get_cached_ids(cls, key, model, **kwargs):
        """Cache de IDs para evitar JOINS repetitivos en filtrados por nombre."""
        if key not in cls._static_cache:
            cls._static_cache[key] = list(model.objects.filter(**kwargs).values_list("id", flat=True))
        return cls._static_cache[key]

    @classmethod
    def get_hardware_availability(cls):
        """
        Retorna la disponibilidad actual de hardware agrupada por TipoDispositivo.
        Aplica semáforo según el umbral_disponibilidad de cada tipo.
        """
        tipos = TipoDispositivo.objects.all().order_by('nombre')
        estados_disponibles = ["Disponible", "Reservado"]
        
        hardware_list = []
        for tipo in tipos:
            disponibles_count = Dispositivo.objects.filter(
                modelo__tipo_dispositivo=tipo,
                estado__nombre__in=estados_disponibles
            ).count()
            
            # Semáforo
            if disponibles_count == 0:
                status = "red"
            elif disponibles_count <= tipo.umbral_disponibilidad:
                status = "yellow"
            else:
                status = "green"
                
            hardware_list.append({
                "tipo": tipo,
                "disponibles": disponibles_count,
                "umbral": tipo.umbral_disponibilidad,
                "status": status
            })
            
        # Ordenamos por semáforo (rojo primero, luego amarillo, luego verde) y alfabéticamente
        return sorted(hardware_list, key=lambda x: (
            0 if x["status"] == "red" else (1 if x["status"] == "yellow" else 2),
            x["tipo"].nombre
        ))

    @classmethod
    def get_suministros_packs(cls):
        """
        Agrupa los suministros activos por su fingerprint de compatibilidad.
        Estructura alineada con dashboard/partials/tab_suministros.html
        """
        from suministros.models import Suministro
        
        suministros = Suministro.objects.activos().select_related('categoria', 'fabricante').prefetch_related('modelos_compatibles')
        
        packs_dict = {}
        
        for s in suministros:
            modelos = list(s.modelos_compatibles.all())
            
            if not modelos:
                key = "Generales"
                nombres = "Compatibilidad General"
                ids_list = []
            else:
                # Ordenamos IDs para que el fingerprint sea consistente
                model_ids = sorted([m.id for m in modelos])
                key = frozenset(model_ids)
                nombres = ", ".join([m.nombre for m in modelos])
                ids_list = model_ids
                
            if key not in packs_dict:
                packs_dict[key] = {
                    "modelos_names": nombres,
                    "modelos_ids_list": ids_list,
                    "suministros": [],
                    "resumen_semaforo": 'green'
                }
                
            packs_dict[key]["suministros"].append(s)
            
            # Actualizar semáforo del grupo si hay stock crítico
            if s.stock_critico:
                packs_dict[key]["resumen_semaforo"] = 'red'

        # Convertir a lista y ordenar: los que tienen stock crítico (red) primero
        resultado = list(packs_dict.values())
        return sorted(resultado, key=lambda x: (0 if x["resumen_semaforo"] == 'red' else 1, x["modelos_names"]))

    @staticmethod
    def _semaforo_suministro(stock, stock_minimo):
        if stock == 0: return 'red'
        if stock <= stock_minimo: return 'yellow'
        return 'green'


    @classmethod
    def build_strategic_context(cls, filtered_qs, filterset, top10_metric):
        total_dispositivos = filtered_qs.count()

        disponible_estado = cls._get_cached_obj(
            "disponible_estado", EstadoDispositivo, nombre__in=["Disponible", "Reservado"]
        )
        mantenimiento_estado = cls._get_cached_obj(
            "mantenimiento_estado", EstadoDispositivo, nombre__icontains="Reparación"
        )

        tipo_notebook = cls._get_cached_obj(
            "tipo_notebook", TipoDispositivo, nombre__icontains="Notebook"
        )
        tipo_smartphone = cls._get_cached_obj(
            "tipo_smartphone", TipoDispositivo, nombre__icontains="Smartphone"
        )
        tipo_impresora = cls._get_cached_obj(
            "tipo_impresora", TipoDispositivo, nombre__icontains="Impresora"
        )

        # Cache IDs for common filters to avoid repetitive JOINS on every .count()
        disponible_ids = cls._get_cached_ids("disponible_ids", EstadoDispositivo, nombre__in=["Disponible", "Reservado"])
        asignado_ids = cls._get_cached_ids("asignado_ids", EstadoDispositivo, nombre__in=["Asignado", "En uso"])
        mantenimiento_ids = cls._get_cached_ids("mantenimiento_ids", EstadoDispositivo, nombre__icontains="Reparación")
        baja_ids = cls._get_cached_ids(
            "baja_ids", EstadoDispositivo, nombre__in=["Fuera de Inventario", "De Baja", "Inactivo"]
        )

        total_disponibles = filtered_qs.filter(estado_id__in=disponible_ids).count()
        total_asignados = filtered_qs.filter(estado_id__in=asignado_ids).count()
        total_mantenimiento = filtered_qs.filter(estado_id__in=mantenimiento_ids).count()
        total_baja = filtered_qs.filter(estado_id__in=baja_ids).count()

        total_valor = filtered_qs.aggregate(total=Sum("valor_contable"))["total"] or 0
        costo_mantenimiento = (
            BitacoraMantenimiento.objects.filter(dispositivo__in=filtered_qs).aggregate(total=Sum("costo_reparacion"))["total"]
            or 0
        )

        total_activos = total_dispositivos - total_baja
        porcentaje_asignados = round((total_asignados / total_activos * 100) if total_activos > 0 else 0)

        total_notebooks_disponibles = (
            filtered_qs.filter(
                modelo__tipo_dispositivo=tipo_notebook,
                estado_id__in=disponible_ids,
            ).count()
            if tipo_notebook
            else 0
        )
        total_smartphones_disponibles = (
            filtered_qs.filter(
                modelo__tipo_dispositivo=tipo_smartphone,
                estado_id__in=disponible_ids,
            ).count()
            if tipo_smartphone
            else 0
        )
        total_impresoras_disponibles = (
            filtered_qs.filter(
                modelo__tipo_dispositivo=tipo_impresora,
                estado_id__in=disponible_ids,
            ).count()
            if tipo_impresora
            else 0
        )

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
            "total_disponibles_id": disponible_estado.id if disponible_estado else "",
            "total_asignados": total_asignados,
            "total_mantenimiento": total_mantenimiento,
            "total_mantenimiento_id": mantenimiento_estado.id if mantenimiento_estado else "",
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
            "tipo_notebook_id": tipo_notebook.id if tipo_notebook else "",
            "tipo_smartphone_id": tipo_smartphone.id if tipo_smartphone else "",
            "tipo_impresora_id": tipo_impresora.id if tipo_impresora else "",
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

