from django.conf import settings
from django.db import connection

class TenantDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            host = request.get_host()
        except Exception as e:
            host = f"ERROR: {e}"
            print(f"DEBUG ALLOWED_HOSTS={settings.ALLOWED_HOSTS}")
        print(f"DEBUG: Host={host} | Schema={connection.schema_name}")
        response = self.get_response(request)
        return response
