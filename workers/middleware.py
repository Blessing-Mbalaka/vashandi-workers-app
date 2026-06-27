from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.crypto import get_random_string

from .error_utils import send_exception_alert


class FrontendSafeExceptionMiddleware:
    """Hide server internals from end users while emailing the real error details."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as exc:
            error_reference = get_random_string(12).upper()
            send_exception_alert(error_reference=error_reference, request=request, exc=exc)

            wants_json = (
                request.path.startswith('/api/')
                or 'application/json' in request.headers.get('Accept', '')
                or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            )
            if wants_json:
                return JsonResponse(
                    {
                        'error': 'We hit a snag. The issue has been logged and the team has been notified.',
                        'reference': error_reference,
                    },
                    status=500,
                )

            response = redirect(f'/we-hit-a-snag/?ref={error_reference}')
            response.status_code = 302
            return response
