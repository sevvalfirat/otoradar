import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from listings.catalog import CITY_PLATES

register = template.Library()


@register.filter
def tl(value):
    """1234567.89 -> '1.234.568'  (Türk usulü binlik ayraç, kuruşsuz)"""
    try:
        return f"{float(value):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return value


@register.filter
def km(value):
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return value


@register.filter
def plate_code(city):
    return CITY_PLATES.get(city, "··")


@register.filter
def simple_markdown(text):
    """
    Asistan cevaplarındaki basit markdown'ı güvenli HTML'e çevirir:
    **kalın**, '- ' / '* ' ile başlayan maddeler ve satır sonları.
    Önce her şey escape edilir, yani kullanıcı/LLM metni HTML enjekte edemez.
    """
    html_lines, in_list = [], False
    for raw in escape(text or "").splitlines():
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", raw.strip())
        bullet = re.match(r"^[-*•]\s+(.*)", line)
        if bullet:
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{bullet.group(1)}</li>")
            continue
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        if line:
            html_lines.append(f"<p>{line}</p>")
    if in_list:
        html_lines.append("</ul>")
    return mark_safe("\n".join(html_lines))
