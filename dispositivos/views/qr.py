import io

import qrcode
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from ..models import Dispositivo


@login_required
def dispositivo_qr(request, pk):
    """Genera un código QR dinámico para el equipo."""
    dispositivo = get_object_or_404(Dispositivo, pk=pk)

    # URL absoluta al detalle
    url = request.build_absolute_uri(dispositivo.get_absolute_url())

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return FileResponse(
        buffer,
        as_attachment=False,
        filename=f"qr_{dispositivo.identificador_interno}.png",
        content_type="image/png",
    )
