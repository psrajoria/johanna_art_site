"""
Session-based shopping cart plus the logic that turns a cart into an order.

Guests and logged-in customers share the same cart (it lives in the session).
"""

from dataclasses import dataclass
from decimal import Decimal

from django.db import models, transaction
from django.utils import translation
from django.utils.translation import gettext as _

from wagtail.models import Site

from artworks.models import ArtworkPage, Offer

from . import emails
from .models import DiscountCode, Order, OrderItem, ShopSettings
from .shipping import calculate_shipping

SESSION_KEY = "cart"
CODE_KEY = "discount_code"
MAX_QTY = 20


@dataclass
class CartLine:
    offer: Offer
    quantity: int
    page: ArtworkPage  # artwork page in the visitor's language
    problem: str = ""

    @property
    def unit_price(self):
        return self.offer.price

    @property
    def line_total(self):
        return self.offer.price * self.quantity

    @property
    def max_quantity(self):
        if self.offer.kind in (Offer.KIND_ORIGINAL, Offer.KIND_DIGITAL):
            return 1
        if self.offer.stock is None:
            return MAX_QTY
        return max(1, min(MAX_QTY, self.offer.stock))


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.data = dict(self.session.get(SESSION_KEY, {}))

    # --- editing ------------------------------------------------------

    def _save(self):
        self.session[SESSION_KEY] = self.data
        self.session.modified = True

    def add(self, offer, quantity=1):
        key = str(offer.pk)
        current = self.data.get(key, 0)
        limit = 1 if offer.kind in (Offer.KIND_ORIGINAL, Offer.KIND_DIGITAL) else MAX_QTY
        if offer.stock is not None and offer.kind == Offer.KIND_PRINT:
            limit = min(limit, offer.stock)
        self.data[key] = max(1, min(current + quantity, limit))
        self._save()

    def set_quantity(self, offer_id, quantity):
        key = str(offer_id)
        if key not in self.data:
            return
        if quantity <= 0:
            del self.data[key]
        else:
            self.data[key] = min(quantity, MAX_QTY)
        self._save()

    def remove(self, offer_id):
        self.data.pop(str(offer_id), None)
        self._save()

    def clear(self):
        self.data = {}
        self._save()

    # --- reading ------------------------------------------------------

    def __len__(self):
        return sum(self.data.values())

    def __bool__(self):
        return bool(self.data)

    def lines(self):
        ids = [int(k) for k in self.data]
        offers = {
            o.pk: o
            for o in Offer.objects.select_related("artwork").filter(pk__in=ids)
        }
        language = translation.get_language()
        keys = [o.artwork.translation_key for o in offers.values()]
        pages = {
            p.translation_key: p
            for p in ArtworkPage.objects.filter(
                translation_key__in=keys, locale__language_code=language
            ).select_related("main_image")
        }

        lines = []
        for key, quantity in self.data.items():
            offer = offers.get(int(key))
            if offer is None:
                continue
            page = pages.get(offer.artwork.translation_key, offer.artwork)
            line = CartLine(offer=offer, quantity=quantity, page=page)
            line.problem = self.problem_for(line)
            lines.append(line)
        return lines

    @staticmethod
    def problem_for(line):
        offer = line.offer
        if not offer.is_purchasable(offer.artwork.status):
            if offer.kind == Offer.KIND_ORIGINAL:
                return _("This original is no longer available.")
            return _("This item is sold out.")
        if offer.stock is not None and line.quantity > offer.stock:
            return _("Only %(n)d left in stock.") % {"n": offer.stock}
        return ""

    @staticmethod
    def subtotal(lines):
        return sum((line.line_total for line in lines), Decimal("0.00"))

    # --- discount code ------------------------------------------------

    @property
    def code(self):
        return self.session.get(CODE_KEY, "")

    def set_code(self, code):
        self.session[CODE_KEY] = code
        self.session.modified = True

    def clear_code(self):
        self.session.pop(CODE_KEY, None)
        self.session.modified = True

    def pricing(self, lines):
        """Subtotal, discount and what is left to pay for goods (shipping is added later)."""
        subtotal = self.subtotal(lines)
        result = {
            "subtotal": subtotal,
            "code": None,
            "discount": Decimal("0.00"),
            "free_shipping": False,
            "problem": "",
        }
        if self.code:
            code = DiscountCode.objects.filter(code=self.code).first()
            problem = code.problem(subtotal) if code else _("This code is not valid.")
            if problem:
                result["problem"] = problem
            else:
                result["code"] = code
                result["discount"], result["free_shipping"] = code.amounts(subtotal)
        result["goods_total"] = subtotal - result["discount"]
        return result


class OrderError(Exception):
    """Raised when an order can't be placed (e.g. item sold in the meantime)."""


def shop_settings():
    site = Site.objects.filter(is_default_site=True).first()
    return ShopSettings.for_site(site) if site else None


@transaction.atomic
def place_order(cart, data, user, language):
    """
    Turn the cart into an Order and reserve stock.

    `data` holds the validated checkout form fields. Raises OrderError with a
    visitor-friendly message if something sold out while they were checking out.
    """
    lines = cart.lines()
    if not lines:
        raise OrderError(_("Your cart is empty."))

    # Re-read offers locked, so two simultaneous checkouts can't oversell.
    locked = {
        o.pk: o
        for o in Offer.objects.select_for_update()
        .select_related("artwork")
        .filter(pk__in=[line.offer.pk for line in lines])
    }
    for line in lines:
        line.offer = locked[line.offer.pk]
        line.problem = cart.problem_for(line)
        if line.problem:
            raise OrderError(f"{line.page.title}: {line.problem}")

    has_physical = any(line.offer.is_physical for line in lines)
    has_digital = any(not line.offer.is_physical for line in lines)

    settings_obj = shop_settings()
    free_over = settings_obj.free_shipping_over if settings_obj else None

    if has_physical:
        shipping, _estimate = calculate_shipping(
            lines, data.get("country", ""), free_over
        )
    else:
        shipping = Decimal("0.00")
    subtotal = Cart.subtotal(lines)

    # a discount code is checked again, locked, so one-use codes cannot be used twice
    code = None
    discount = Decimal("0.00")
    if cart.code:
        code = DiscountCode.objects.select_for_update().filter(code=cart.code).first()
        problem = code.problem(subtotal) if code else _("This code is not valid.")
        if problem:
            raise OrderError(problem)
        discount, free_shipping = code.amounts(subtotal)
        if free_shipping and has_physical:
            shipping = Decimal("0.00")

    order = Order.objects.create(
        user=user if user and user.is_authenticated else None,
        language=language,
        payment_method=data["payment_method"],
        name=data["name"],
        email=data["email"],
        phone=data.get("phone", ""),
        address_line1=data.get("address_line1", ""),
        address_line2=data.get("address_line2", ""),
        postal_code=data.get("postal_code", ""),
        city=data.get("city", ""),
        country=data.get("country", "") if has_physical else "",
        customer_note=data.get("customer_note", ""),
        subtotal=subtotal,
        discount_code=code.code if code else "",
        discount_amount=discount,
        shipping_cost=shipping,
        total=subtotal - discount + shipping,
        has_physical=has_physical,
        has_digital=has_digital,
    )

    for line in lines:
        offer = line.offer
        OrderItem.objects.create(
            order=order,
            offer=offer,
            title=line.page.title,
            option_label=(
                offer.short_label() if offer.kind != Offer.KIND_ORIGINAL else ""
            ),
            kind=offer.kind,
            quantity=line.quantity,
            unit_price=offer.price,
            download_name=offer.download_file.name if offer.download_file else "",
        )
        if offer.kind == Offer.KIND_ORIGINAL:
            offer.artwork.set_status(ArtworkPage.STATUS_RESERVED)
        elif offer.stock is not None:
            Offer.objects.filter(pk=offer.pk).update(
                stock=models.F("stock") - line.quantity
            )

    if code:
        code.used_count += 1
        if code.kind == DiscountCode.GIFT:
            code.remaining = max((code.remaining or Decimal("0")) - discount, Decimal("0"))
        code.save()
        cart.clear_code()

    transaction.on_commit(lambda: emails.send_order_placed(order))
    return order
