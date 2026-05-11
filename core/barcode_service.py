import barcode
import qrcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64


def meter_barcode_png(meter_number: str) -> bytes:
    writer = ImageWriter()
    code = barcode.get('code128', meter_number, writer=writer)
    buf = BytesIO()
    code.write(buf, options={
        'module_width': 0.2,
        'module_height': 15.0,
        'font_size': 8,
        'write_text': True,
    })
    return buf.getvalue()


def meter_qr_png(meter_number: str, tenant_domain: str) -> bytes:
    url = f"https://{tenant_domain}/billing/meters/?search={meter_number}"
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()
