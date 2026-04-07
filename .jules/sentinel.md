## 2025-05-22 - [Flask Decorator Ordering Bypass]
**Vulnerability:** In this Flask application, placing authentication decorators (like `@api_key_required`) above the route decorator (e.g., `@bp.route`) causes the route to register the undecorated function, bypassing security checks.
**Learning:** Flask's `@route` decorator registers the function it wraps *at the time it is called*. If other decorators are above it, they have not yet wrapped the function when the route is registered.
**Prevention:** Always place authentication and other middleware decorators immediately *below* the route decorator to ensure they are included in the registered route handler.

## 2025-05-22 - [Timing Attack on API Key]
**Vulnerability:** Using standard string comparison (`==`) for API keys or secrets is vulnerable to timing attacks.
**Learning:** Standard comparison returns as soon as a mismatch is found, allowing an attacker to deduce the key character-by-character.
**Prevention:** Use `secrets.compare_digest` for all secret or API key comparisons to ensure constant-time execution.
