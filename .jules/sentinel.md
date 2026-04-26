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

## 2026-04-26 - Username Enumeration via Timing Attack in Authentication
**Vulnerability:** The `authenticate` function returned immediately if a user was not found, but performed a slow password hash verification if the user existed, allowing an attacker to determine valid usernames by measuring response times.
**Learning:** Security-sensitive operations like authentication must maintain consistent timing characteristics regardless of the outcome to prevent side-channel information leakage.
**Prevention:** Perform a "dummy" hash verification with a fixed salt/hash when a user is not found to ensure the computational cost is similar for both existing and non-existing users.

## 2026-04-26 - Inconsistent Authorization Enforcement Across API
**Vulnerability:** While some endpoints required an API key, most did not respect the `ENABLE_LOGIN` setting, allowing unauthorized access to sensitive data (gallery, search, delete) if only an API key (which could be bypassed if not set) was used.
**Learning:** Security decorators must be applied consistently across all sensitive routes, and middleware should support the multiple authentication modes (session vs. API key) used by different parts of the system.
**Prevention:** Enhance the central `login_required` decorator to handle both session and API key validation, and ensure it is applied to all endpoints that handle sensitive user data.
