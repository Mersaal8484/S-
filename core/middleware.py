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
        if hasattr(request, 'tenant') and request.tenant:
            plan_tier = request.tenant.plan.tier if request.tenant.plan else None
            request.available_features = {
                feature: plan_tier in tiers
                for feature, tiers in self.FEATURE_MAP.items()
            }
        return self.get_response(request)
