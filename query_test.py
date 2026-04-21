from dispositivos.models import Notebook, Smartphone, Monitor, Dispositivo
from django.utils.timezone import localtime

print('=== ÚLTIMO DISPOSITIVO GENERAL ===')
d = Dispositivo.objects.order_by('-ultima_actualizacion').first()
if d:
    print(f' - ID: {d.identificador_interno}')
    print(f' - Última Modificación: {localtime(d.ultima_actualizacion).strftime("%d/%m/%Y %H:%M:%S")}')
    print(f' - Tipo: {d.tipo.nombre}')
    print(f' - Modelo: {d.modelo.nombre}')

print('\n=== ÚLTIMO NOTEBOOK ===')
n = Notebook.objects.order_by('-ultima_actualizacion').first()
if n:
    print(f' - ID: {n.identificador_interno}')
    print(f' - Procesador: {n.procesador}')
    print(f' - RAM: {n.ram_gb} GB')
    print(f' - Fecha Mod: {localtime(n.ultima_actualizacion).strftime("%d/%m/%Y %H:%M:%S")}')
else:
    print(' - Ninguno')

print('\n=== ÚLTIMO SMARTPHONE ===')
s = Smartphone.objects.order_by('-ultima_actualizacion').first()
if s:
    print(f' - ID: {s.identificador_interno}')
    print(f' - IMEI 1: {s.imei_1}')
    print(f' - Fecha Mod: {localtime(s.ultima_actualizacion).strftime("%d/%m/%Y %H:%M:%S")}')
else:
    print(' - Ninguno')

print('\n=== ÚLTIMO MONITOR ===')
m = Monitor.objects.order_by('-ultima_actualizacion').first()
if m:
    print(f' - ID: {m.identificador_interno}')
    print(f' - Pulgadas: {m.pulgadas}')
    print(f' - Resolucion: {m.resolucion}')
    print(f' - Fecha Mod: {localtime(m.ultima_actualizacion).strftime("%d/%m/%Y %H:%M:%S")}')
else:
    print(' - Ninguno')
