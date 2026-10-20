from .cart import SESSION_KEY


def cart(request):
    """Cart item count for the header badge (no database access)."""
    data = request.session.get(SESSION_KEY, {}) if hasattr(request, "session") else {}
    return {"cart_count": sum(data.values())}
