import logging
from django.db import connection

logger = logging.getLogger('billing.api')


class TenantAwareFilter(logging.Filter):
    def filter(self, record):
        record.tenant_schema = getattr(connection, 'schema_name', 'public')
        return True
