from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from artworks.models import Offer

from .cart import Cart, OrderError, place_order, shop_settings
from .forms import CheckoutForm, OrderLookupForm, RegisterForm
from .models import Order, OrderItem
from .shipping import ShippingUnavailable, calculate_shipping, country_choices
from config.storage import private_storage

SESSION_ORDERS = "my_order_tokens"


# --- cart ------------------------------------------------------------------


def cart_detail(request):
    cart = Cart(request)
    lines = cart.lines()
    return render(
        request,
        "shop/cart.html",
        {
            "lines": lines,
            "subtotal": Cart.subtotal(lines),
            "has_problem": any(line.problem for line in lines),
            "has_physical": any(line.offer.is_physical for line in lines),
        },
    )


@require_POST
def cart_add(request, offer_id):
    offer = get_object_or_404(
        Offer.objects.select_related("artwork"), pk=offer_id, is_active=True
    )
    if not offer.is_purchasable(offer.artwork.status):
        messages.error(request, _("Sorry, this item is no longer available."))
        return redirect(_safe_next(request) or "shop:cart")

    Cart(request).add(offer)
    messages.success(request, _("Added to your cart."))
    if request.POST.get("buy_now"):
        return redirect("shop:checkout")
    return redirect(_safe_next(request) or "shop:cart")


@require_POST
def cart_update(request):
    cart = Cart(request)
    for key, value in request.POST.items():
        if key.startswith("qty_"):
            try:
                cart.set_quantity(int(key[4:]), int(value))
            except ValueError:
                continue
    return redirect("shop:cart")


@require_POST
def cart_remove(request, offer_id):
    Cart(request).remove(offer_id)
    messages.info(request, _("Removed from your cart."))
    return redirect("shop:cart")


def _safe_next(request):
    target = request.POST.get("next", "")
    if target.startswith("/") and not target.startswith("//"):
        return target
    return ""


# --- checkout --------------------------------------------------------------


def _payment_choices(shop):
    choices = []
    if shop and (shop.paypal_email or shop.paypal_me_handle):
        choices.append((Order.PAYMENT_PAYPAL, "PayPal"))
    if shop and shop.bank_iban:
        choices.append((Order.PAYMENT_BANK, _("Bank transfer")))
    return choices or [(Order.PAYMENT_PAYPAL, "PayPal")]


def _shipping_table(lines, shop):
    """Shipping cost per country, so the page can update without a reload."""
    free_over = shop.free_shipping_over if shop else None
    table = {}
    for code, _label in country_choices():
        try:
            cost, estimate = calculate_shipping(lines, code, free_over)
            table[code] = {"cost": str(cost), "estimate": estimate}
        except ShippingUnavailable:
            table[code] = None
    return table


def checkout(request):
    cart = Cart(request)
    lines = cart.lines()
    if not lines:
        messages.info(request, _("Your cart is empty."))
        return redirect("shop:cart")
    if any(line.problem for line in lines):
        messages.error(request, _("Please fix the items in your cart first."))
        return redirect("shop:cart")

    shop = shop_settings()
    needs_shipping = any(line.offer.is_physical for line in lines)
    has_digital = any(not line.offer.is_physical for line in lines)
    subtotal = Cart.subtotal(lines)

    initial = {}
    if request.user.is_authenticated:
        initial = {
            "email": request.user.email,
            "name": request.user.get_full_name() or request.user.first_name,
        }
        last = request.user.orders.first()
        if last:
            for field in (
                "phone", "address_line1", "address_line2",
                "postal_code", "city", "country",
            ):
                initial[field] = getattr(last, field)

    form_kwargs = {
        "needs_shipping": needs_shipping,
        "has_digital": has_digital,
        "payment_choices": _payment_choices(shop),
    }

    if request.method == "POST":
        form = CheckoutForm(request.POST, **form_kwargs)
        if form.is_valid():
            try:
                order = place_order(
                    cart,
                    form.cleaned_data,
                    request.user,
                    translation.get_language(),
                )
            except OrderError as exc:
                messages.error(request, str(exc))
                return redirect("shop:cart")
            except ShippingUnavailable:
                form.add_error(
                    "country",
                    _("Sorry, we can't ship to this country yet. Please get in touch."),
                )
            else:
                cart.clear()
                tokens = request.session.get(SESSION_ORDERS, [])
                request.session[SESSION_ORDERS] = tokens + [order.token]
                return redirect("shop:order", token=order.token)
    else:
        form = CheckoutForm(initial=initial, **form_kwargs)

    shipping_table = _shipping_table(lines, shop) if needs_shipping else {}

    return render(
        request,
        "shop/checkout.html",
        {
            "form": form,
            "lines": lines,
            "subtotal": subtotal,
            "needs_shipping": needs_shipping,
            "has_digital": has_digital,
            "shipping_table": shipping_table,
            "shop": shop,
        },
    )


# --- orders ----------------------------------------------------------------


def order_detail(request, token):
    order = get_object_or_404(Order, token=token)
    shop = shop_settings()

    paypal_url = ""
    if shop and shop.paypal_me_handle:
        paypal_url = f"https://www.paypal.com/paypalme/{quote(shop.paypal_me_handle)}/{order.total}EUR"

    return render(
        request,
        "shop/order_detail.html",
        {
            "order": order,
            "items": order.items.all(),
            "shop": shop,
            "paypal_url": paypal_url,
            "awaiting": order.status == Order.STATUS_AWAITING,
            "steps": _progress_steps(order),
            "expires": order.download_expires,
        },
    )


def _progress_steps(order):
    """Steps for the order timeline: [(label, state)] with state done/current/todo."""
    cancelled = order.status == Order.STATUS_CANCELLED
    if cancelled:
        return []
    order_of = [
        Order.STATUS_AWAITING,
        Order.STATUS_PAID,
        Order.STATUS_PACKED,
        Order.STATUS_SHIPPED,
        Order.STATUS_COMPLETED,
    ]
    labels = {
        Order.STATUS_AWAITING: _("Order placed"),
        Order.STATUS_PAID: _("Payment received"),
        Order.STATUS_PACKED: _("Being prepared"),
        Order.STATUS_SHIPPED: _("Shipped"),
        Order.STATUS_COMPLETED: _("Completed"),
    }
    if not order.has_physical and order.status in (
        Order.STATUS_AWAITING,
        Order.STATUS_PAID,
        Order.STATUS_COMPLETED,
    ):
        order_of = [Order.STATUS_AWAITING, Order.STATUS_PAID, Order.STATUS_COMPLETED]
    index = order_of.index(order.status)
    steps = []
    for i, status in enumerate(order_of):
        if i < index:
            state = "done"
        elif i == index:
            state = "current"
        else:
            state = "todo"
        steps.append((labels[status], state))
    return steps


def order_lookup(request):
    form = OrderLookupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        order = Order.objects.filter(
            number__iexact=form.cleaned_data["number"].strip(),
            email__iexact=form.cleaned_data["email"].strip(),
        ).first()
        if order:
            return redirect("shop:order", token=order.token)
        messages.error(
            request,
            _("We couldn't find an order with that number and email."),
        )
    return render(request, "shop/order_lookup.html", {"form": form})


def download(request, token, item_id):
    item = get_object_or_404(OrderItem, pk=item_id, order__token=token)
    if not item.can_download:
        raise Http404
    storage = private_storage()
    if not storage.exists(item.download_name):
        raise Http404
    OrderItem.objects.filter(pk=item.pk).update(
        download_count=item.download_count + 1
    )
    handle = storage.open(item.download_name, "rb")
    filename = item.download_name.rsplit("/", 1)[-1]
    return FileResponse(handle, as_attachment=True, filename=filename)


# --- accounts --------------------------------------------------------------


def _claim_session_orders(request, user):
    tokens = request.session.get(SESSION_ORDERS, [])
    if tokens:
        Order.objects.filter(token__in=tokens, user__isnull=True).update(user=user)


def register(request):
    if request.user.is_authenticated:
        return redirect("shop:account")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        _claim_session_orders(request, user)
        messages.success(request, _("Welcome! Your account is ready."))
        return redirect("shop:account")
    return render(request, "shop/register.html", {"form": form})


@login_required
def account(request):
    _claim_session_orders(request, request.user)
    orders = request.user.orders.prefetch_related("items")
    return render(request, "shop/account.html", {"orders": orders})
