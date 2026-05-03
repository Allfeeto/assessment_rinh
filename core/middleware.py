from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


class AuthRateLimitMiddleware:
    """Rate limit failed login attempts for project login and Django admin."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._should_limit(request):
            return self.get_response(request)

        cache_key = self._cache_key(request)
        attempts = cache.get(cache_key, 0)
        max_attempts = getattr(settings, 'AUTH_RATE_LIMIT_ATTEMPTS', 5)
        window_seconds = getattr(settings, 'AUTH_RATE_LIMIT_WINDOW_SECONDS', 300)

        if attempts >= max_attempts:
            return HttpResponse(
                'Слишком много неудачных попыток входа. Повторите позже.',
                status=429,
            )

        response = self.get_response(request)
        if response.status_code not in {301, 302, 303, 307, 308}:
            cache.set(cache_key, attempts + 1, window_seconds)
        else:
            cache.delete(cache_key)
        return response

    @staticmethod
    def _should_limit(request):
        if not getattr(settings, 'AUTH_RATE_LIMIT_ENABLED', True):
            return False
        if request.method != 'POST':
            return False
        limited_paths = set(
            getattr(
                settings,
                'AUTH_RATE_LIMIT_PATHS',
                ('/login/', '/accounts/login/', '/admin/login/'),
            )
        )
        return request.path in limited_paths

    @staticmethod
    def _cache_key(request):
        remote_addr = request.META.get('REMOTE_ADDR') or 'unknown'
        return f'auth-rate-limit:{request.path}:{remote_addr}'
