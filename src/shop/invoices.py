"""PDF invoice and packing slip for an order (plain, printable, German-business friendly)."""

from decimal import Decimal

from anyascii import anyascii
from django.utils import translation
from fpdf import FPDF

TEXT = {
    "en": {
        "invoice": "Invoice",
        "packing": "Packing slip",
        "number": "Invoice no.",
        "order": "Order no.",
        "date": "Invoice date",
        "service_date": "Date of delivery / service",
        "bill_to": "Billed to",
        "ship_to": "Ship to",
        "qty": "Qty",
        "item": "Item",
        "price": "Price",
        "total": "Total",
        "subtotal": "Subtotal",
        "discount": "Discount",
        "shipping": "Shipping",
        "free": "Free",
        "grand": "Total amount",
        "vat_exempt": "No VAT is charged in accordance with Section 19 UStG (small business regulation).",
        "vat_included": "Includes {rate}% VAT: EUR {vat}",
        "tax_no": "Tax no.",
        "vat_id": "VAT ID",
        "paid": "Paid. Thank you very much!",
        "thanks": "Thank you for supporting my art. It means the world to me.",
        "digital": "Digital download (no shipment)",
        "note": "Note",
        "page": "Page",
    },
    "de": {
        "invoice": "Rechnung",
        "packing": "Lieferschein",
        "number": "Rechnungsnr.",
        "order": "Bestellnr.",
        "date": "Rechnungsdatum",
        "service_date": "Liefer-/Leistungsdatum",
        "bill_to": "Rechnung an",
        "ship_to": "Lieferadresse",
        "qty": "Anz.",
        "item": "Artikel",
        "price": "Preis",
        "total": "Summe",
        "subtotal": "Zwischensumme",
        "discount": "Rabatt",
        "shipping": "Versand",
        "free": "Kostenlos",
        "grand": "Gesamtbetrag",
        "vat_exempt": "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.",
        "vat_included": "Enthält {rate} % MwSt.: {vat} EUR",
        "tax_no": "Steuernr.",
        "vat_id": "USt-IdNr.",
        "paid": "Bezahlt. Vielen Dank!",
        "thanks": "Danke, dass du meine Kunst unterstützt. Das bedeutet mir sehr viel.",
        "digital": "Digitaler Download (kein Versand)",
        "note": "Anmerkung",
        "page": "Seite",
    },
}

INK = (42, 36, 32)
SOFT = (110, 98, 88)
ACCENT = (196, 85, 59)


def _t(value):
    """The built-in PDF fonts speak Latin-1; anything else is transliterated, never dropped."""
    text = str(value)
    try:
        text.encode("latin-1")
        return text
    except UnicodeEncodeError:
        return "".join(c if ord(c) < 256 else anyascii(c) for c in text)


def _money(value, lang):
    text = f"{Decimal(value):,.2f}"
    if lang == "de":
        text = text.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} EUR"


class _Doc(FPDF):
    def __init__(self, seller_name, lang):
        super().__init__(format="A4")
        self.seller_name = seller_name
        self.lang = lang
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(20, 18, 20)
        self.set_title(_t(seller_name))
        self.set_author(_t(seller_name))

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*SOFT)
        self.cell(0, 6, _t(f"{self.seller_name}  -  {TEXT[self.lang]['page']} {self.page_no()}"), align="C")


def _header(pdf, title, shop, order, lang, number=None, date=None):
    t = TEXT[lang]
    pdf.add_page()
    pdf.set_fill_color(232, 165, 160)
    pdf.rect(0, 0, 210, 4, style="F")
    pdf.set_fill_color(227, 169, 59)
    pdf.rect(52.5, 0, 52.5, 4, style="F")
    pdf.set_fill_color(134, 169, 139)
    pdf.rect(105, 0, 52.5, 4, style="F")
    pdf.set_fill_color(91, 131, 168)
    pdf.rect(157.5, 0, 52.5, 4, style="F")

    pdf.set_y(14)
    pdf.set_font("Times", "B", 24)
    pdf.set_text_color(*INK)
    pdf.cell(110, 10, _t(shop["name"]))
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 10, _t(title), align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Times", "I", 11)
    pdf.set_text_color(*ACCENT)
    pdf.cell(110, 6, "Just keep layering")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*SOFT)
    meta = [(t["order"], order.number)]
    if number:
        meta.insert(0, (t["number"], number))
    if date:
        meta.append((t["date"], date))
    pdf.multi_cell(0, 4.6, _t("\n".join(f"{k}: {v}" for k, v in meta)), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # sender line and address block
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*SOFT)
    sender = " - ".join(x for x in [shop["name"], shop["address_line"]] if x)
    pdf.cell(0, 4, _t(sender), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _address(order, lang="en", with_country=True):
    lines = [order.name, order.address_line1, order.address_line2]
    lines.append(" ".join(x for x in [order.postal_code, order.city] if x))
    if with_country and order.country:
        with translation.override(lang):
            lines.append(str(order.get_country_display()))
    return [line for line in lines if line]


def _shop_info(settings_obj):
    name = (getattr(settings_obj, "seller_name", "") or "Johanna Lackner").strip()
    address = (getattr(settings_obj, "seller_address", "") or "").strip()
    return {
        "name": name,
        "address": address.splitlines(),
        "address_line": ", ".join(line.strip() for line in address.splitlines() if line.strip()),
        "tax_number": getattr(settings_obj, "tax_number", ""),
        "vat_id": getattr(settings_obj, "vat_id", ""),
        "email": getattr(settings_obj, "notify_email", ""),
        "exempt": getattr(settings_obj, "small_business_vat_exempt", True),
        "vat_rate": getattr(settings_obj, "vat_rate", Decimal("19")),
    }


def _bytes(pdf):
    return bytes(pdf.output())


def invoice_pdf(order, settings_obj):
    lang = order.language if order.language in TEXT else "en"
    t = TEXT[lang]
    shop = _shop_info(settings_obj)
    pdf = _Doc(shop["name"], lang)
    paid_on = order.paid_at or order.created_at
    date = (paid_on.strftime("%d.%m.%Y") if lang == "de" else paid_on.strftime("%Y-%m-%d"))
    _header(pdf, t["invoice"], shop, order, lang, number=order.invoice_number, date=date)

    # customer
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*SOFT)
    pdf.cell(0, 5, _t(t["bill_to"].upper()), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*INK)
    for line in _address(order, lang):
        pdf.cell(0, 5.4, _t(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # items
    widths = (14, 100, 28, 28)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(244, 236, 223)
    pdf.set_text_color(*INK)
    for w, label, align in zip(widths, (t["qty"], t["item"], t["price"], t["total"]), ("C", "L", "R", "R")):
        pdf.cell(w, 8, _t(label), fill=True, align=align)
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 10)
    for item in order.items.all():
        title = item.title + (f" ({item.option_label})" if item.option_label else "")
        if item.kind == "digital":
            title += f" - {t['digital']}"
        y = pdf.get_y()
        pdf.set_xy(20 + widths[0], y)
        pdf.multi_cell(widths[1], 5.6, _t(title), new_x="LMARGIN", new_y="NEXT")
        height = max(pdf.get_y() - y, 6)
        pdf.set_xy(20, y)
        pdf.cell(widths[0], height, str(item.quantity), align="C")
        pdf.set_xy(20 + widths[0] + widths[1], y)
        pdf.cell(widths[2], height, _t(_money(item.unit_price, lang)), align="R")
        pdf.cell(widths[3], height, _t(_money(item.line_total, lang)), align="R")
        pdf.set_xy(20, y + height + 1.5)
        pdf.set_draw_color(227, 216, 197)
        pdf.line(20, pdf.get_y() - 0.7, 190, pdf.get_y() - 0.7)

    pdf.ln(3)

    def total_row(label, value, bold=False):
        pdf.set_font("Helvetica", "B" if bold else "", 11 if bold else 10)
        pdf.cell(60, 7, "")
        pdf.cell(60, 7, _t(label), align="R")
        pdf.cell(50, 7, _t(value), align="R", new_x="LMARGIN", new_y="NEXT")

    total_row(t["subtotal"], _money(order.subtotal, lang))
    if order.discount_code:
        amount = _money(-order.discount_amount, lang) if order.discount_amount else t["free"]
        total_row(f"{t['discount']} {order.discount_code}", amount)
    if order.has_physical:
        total_row(t["shipping"], t["free"] if order.shipping_cost == 0 else _money(order.shipping_cost, lang))
    pdf.set_draw_color(*INK)
    pdf.line(100, pdf.get_y() + 1, 190, pdf.get_y() + 1)
    pdf.ln(2)
    pdf.set_text_color(*ACCENT)
    total_row(t["grand"], _money(order.total, lang), bold=True)
    pdf.set_text_color(*INK)

    pdf.ln(6)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*SOFT)
    if shop["exempt"]:
        pdf.multi_cell(0, 4.8, _t(t["vat_exempt"]), new_x="LMARGIN", new_y="NEXT")
    else:
        rate = Decimal(shop["vat_rate"])
        vat = (order.total * rate / (100 + rate)).quantize(Decimal("0.01"))
        pdf.multi_cell(
            0, 4.8, _t(t["vat_included"].format(rate=f"{rate.normalize():f}", vat=f"{vat:.2f}")),
            new_x="LMARGIN", new_y="NEXT",
        )
    pdf.multi_cell(0, 4.8, _t(f"{t['service_date']}: {date}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, _t(t["paid"]), new_x="LMARGIN", new_y="NEXT")

    # sender details at the bottom
    pdf.set_y(-52)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*SOFT)
    pdf.set_draw_color(227, 216, 197)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(2)
    details = [shop["name"], *shop["address"]]
    if shop["email"]:
        details.append(shop["email"])
    if shop["tax_number"]:
        details.append(f"{t['tax_no']}: {shop['tax_number']}")
    if shop["vat_id"]:
        details.append(f"{t['vat_id']}: {shop['vat_id']}")
    pdf.multi_cell(0, 4.4, _t("\n".join(d for d in details if d)), new_x="LMARGIN", new_y="NEXT")
    return _bytes(pdf)


def packing_slip_pdf(order, settings_obj):
    lang = order.language if order.language in TEXT else "en"
    t = TEXT[lang]
    shop = _shop_info(settings_obj)
    pdf = _Doc(shop["name"], lang)
    _header(pdf, t["packing"], shop, order, lang)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*SOFT)
    pdf.cell(0, 5, _t(t["ship_to"].upper()), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*INK)
    for line in _address(order, lang):
        pdf.cell(0, 6.4, _t(line), new_x="LMARGIN", new_y="NEXT")
    if order.phone:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, _t(order.phone), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(244, 236, 223)
    pdf.cell(18, 8, _t(t["qty"]), fill=True, align="C")
    pdf.cell(0, 8, _t(t["item"]), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for item in order.items.all():
        if item.kind == "digital":
            continue
        title = item.title + (f" ({item.option_label})" if item.option_label else "")
        pdf.cell(18, 8, str(item.quantity), align="C")
        pdf.cell(0, 8, _t(title), new_x="LMARGIN", new_y="NEXT")
    if order.customer_note:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*SOFT)
        pdf.cell(0, 5, _t(t["note"].upper()), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10.5)
        pdf.set_text_color(*INK)
        pdf.multi_cell(0, 5.4, _t(order.customer_note), new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(-60)
    pdf.set_font("Times", "I", 14)
    pdf.set_text_color(*ACCENT)
    pdf.multi_cell(0, 7, _t(t["thanks"]), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Times", "B", 16)
    pdf.set_text_color(*INK)
    pdf.cell(0, 8, _t(shop["name"]), align="C")
    return _bytes(pdf)
