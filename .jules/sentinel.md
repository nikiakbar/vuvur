## 2026-04-05 - Improper Decorator Placement Bypassing Auth
**Vulnerability:** Security decorators (like `@api_key_required`) were being bypassed because they were placed *above* the Flask `@app.route` decorator.
**Learning:** Flask's `@app.route` registers the view function at the time it's called. If a security decorator is placed above it, the route is registered with the *original* function before the decorator has a chance to wrap it with security checks.
**Prevention:** Always place security, authentication, and authorization decorators *below* the `@app.route` (or `@bp.route`) decorator to ensure the wrapped function is what gets registered with the router.

## 2026-04-05 - Timing Attack Vulnerability in API Key Comparison
**Vulnerability:** API keys were compared using standard equality (`==`), which is susceptible to timing attacks.
**Learning:** Standard string comparison returns as soon as a mismatch is found, allowing an attacker to brute-force a key by measuring how long the server takes to respond.
**Prevention:** Use `secrets.compare_digest()` for constant-time comparison of secrets and API keys.

## 2026-04-19 - Information Leakage via Raw Exception Strings
**Vulnerability:** API endpoints were returning raw exception messages (`str(e)`) to the client, exposing internal implementation details.
**Learning:** Using `str(e)` in a production API response is a shortcut that often leaks sensitive information about the environment, database schema, or code structure.
**Prevention:** Always catch exceptions, log the detailed error server-side (using `logger.error(..., exc_info=True)`), and return a generic, non-descriptive error message to the client.
