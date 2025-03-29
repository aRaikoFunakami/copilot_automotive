import qrcode
import base64
from io import BytesIO
from starlette.templating import Jinja2Templates
from starlette.responses import HTMLResponse
from network_utils import get_local_ip

# Set up Jinja2 templates directory (推奨: templates/)
templates = Jinja2Templates(directory="static")

async def generate_qr_code(request, connected_clients, token):
    """Generates a QR code that directs to a connection page."""
    target_id = request.query_params.get("target_id")
    if not target_id or target_id not in connected_clients:
        return HTMLResponse("<h2>Invalid client ID</h2>", status_code=400)

    # Get server local IP
    server_ip = get_local_ip()

    # URL to embed in the QR code
    connect_url = f"http://{server_ip}:3000/dummy_login?target_id={target_id}&token={token}"

    # Generate QR code
    qr = qrcode.make(connect_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)

    # Encode QR code image to Base64
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # Render HTML template
    return templates.TemplateResponse("qr_code.html", {
        "request": request,
        "qr_base64": qr_base64,
        "connect_url": connect_url
    })
