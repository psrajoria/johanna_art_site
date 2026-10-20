from datetime import timedelta

from django.db.models import Count, Max, Q
from django.utils import timezone

from .models import Event, PageView


def _since(days):
    return timezone.localdate() - timedelta(days=days - 1)


def daily_series(days):
    start = _since(days)
    rows = {
        r["day"]: r
        for r in PageView.objects.filter(day__gte=start)
        .values("day")
        .annotate(views=Count("id"), visitors=Count("visitor", distinct=True))
    }
    series = []
    for i in range(days):
        day = start + timedelta(days=i)
        row = rows.get(day, {})
        series.append({"day": day, "views": row.get("views", 0), "visitors": row.get("visitors", 0)})
    peak = max([s["views"] for s in series] + [1])
    width = 100 / days
    for i, s in enumerate(series):
        s["x"] = round(i * width, 3)
        s["w"] = round(width * 0.7, 3)
        s["h"] = round(s["views"] / peak * 100, 2)
        s["hv"] = round(s["visitors"] / peak * 100, 2)
    return series, peak


def _top(kind, days, limit=8):
    start = _since(days)
    views = (
        PageView.objects.filter(day__gte=start, kind=kind)
        .values("group")
        .annotate(title=Max("title"), views=Count("id"), visitors=Count("visitor", distinct=True))
        .order_by("-views")[:limit]
    )
    groups = [v["group"] for v in views]
    ev = {}
    for row in (
        Event.objects.filter(day__gte=start, group__in=groups)
        .values("group", "name")
        .annotate(n=Count("id"))
    ):
        ev.setdefault(row["group"], {})[row["name"]] = row["n"]
    out = []
    for v in views:
        e = ev.get(v["group"], {})
        out.append(
            {
                **v,
                "hearts": max(e.get("like", 0) - e.get("unlike", 0), 0),
                "carts": e.get("add_to_cart", 0) + e.get("buy_now", 0),
                "enquiries": e.get("enquiry", 0),
            }
        )
    return out


def most_loved(days, limit=5):
    start = _since(days)
    rows = (
        Event.objects.filter(day__gte=start, name__in=["like", "unlike"])
        .exclude(group="")
        .values("group")
        .annotate(
            title=Max("title"),
            net=Count("id", filter=Q(name="like")) - Count("id", filter=Q(name="unlike")),
        )
        .order_by("-net")[:limit]
    )
    return [r for r in rows if r["net"] > 0]


def _breakdown(field, days, limit=8, empty=""):
    rows = (
        PageView.objects.filter(day__gte=_since(days))
        .values(field)
        .annotate(n=Count("id"))
        .order_by("-n")[:limit]
    )
    total = sum(r["n"] for r in rows) or 1
    return [
        {"label": r[field] or empty, "n": r["n"], "pct": round(r["n"] / total * 100)}
        for r in rows
    ]


def build(days=30):
    series, peak = daily_series(days)
    start = _since(days)
    events = {
        r["name"]: r["n"]
        for r in Event.objects.filter(day__gte=start).values("name").annotate(n=Count("id"))
    }
    today = timezone.localdate()
    return {
        "days": days,
        "series": series,
        "peak": peak,
        "views": sum(s["views"] for s in series),
        "visitors_today": next((s["visitors"] for s in series if s["day"] == today), 0),
        "visitors_total": PageView.objects.filter(day__gte=start).values("visitor", "day").distinct().count(),
        "artworks": _top("artwork", days),
        "posts": _top("blog", days, 5),
        "pages": _top("page", days, 6),
        "loved": most_loved(days),
        "referrers": _breakdown("referrer", days, empty="Direct / typed in"),
        "languages": _breakdown("lang", days, 3),
        "devices": _breakdown("device", days, 3),
        "events": events,
        "hearts": max(events.get("like", 0) - events.get("unlike", 0), 0),
        "carts": events.get("add_to_cart", 0) + events.get("buy_now", 0),
        "instagram": events.get("instagram", 0),
    }
