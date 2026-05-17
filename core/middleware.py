class FeatureFlagMiddleware:
    FEATURE_MAP = {
        'api_access': ['pro', 'enterprise'],
        'ewallet':    ['pro', 'enterprise'],
        'sms':        ['basic', 'pro', 'enterprise'],
        'field_app':  ['pro', 'enterprise'],
        'barcode':    ['basic', 'pro', 'enterprise'],
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'tenant') and request.tenant and request.tenant.schema_name != 'public':
            # Since Plan model was removed during localization, grant all features by default
            plan_tier = 'enterprise'
            request.available_features = {
                feature: plan_tier in tiers
                for feature, tiers in self.FEATURE_MAP.items()
            }
        else:
            request.available_features = {}
        return self.get_response(request)

class TenantSecurityMiddleware:
    """
    Prevents cross-tenant access. Ensures that a user logged into the global 
    session can only access the tenant they are assigned to via TenantUser.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'tenant') and request.tenant.schema_name != 'public':
            if request.user.is_authenticated:
                if not request.user.is_superuser:
                    # Check if the user belongs to the requested tenant
                    try:
                        tenant_profile = request.user.tenant_profile
                        if tenant_profile.tenant != request.tenant:
                            from django.http import HttpResponseForbidden
                            return HttpResponseForbidden("Access Denied: You do not belong to this tenant.")
                    except Exception:
                        from django.http import HttpResponseForbidden
                        return HttpResponseForbidden("Access Denied: No tenant profile found.")
        return self.get_response(request)

