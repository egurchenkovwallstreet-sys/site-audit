from __future__ import annotations

from bs4 import BeautifulSoup

from app.compliance.form_consent import script_url_is_vendor_bundle

RU_ANALYTICS_MARKERS = (
    "mc.yandex.ru",
    "metrika.yandex",
    "yandex.ru/metrika",
)

FOREIGN_ANALYTICS_MARKERS = (
    "googletagmanager.com",
    "google-analytics.com",
    "google-analytics",
    "/gtag/js",
    "gtag(",
    "analytics.js",
    "googleadservices.com",
    "facebook.net",
    "connect.facebook.net",
    "fbevents.js",
    "doubleclick.net",
    "hotjar.com",
    "amplitude.com",
    "cdn.amplitude",
    "mixpanel.com",
    "segment.com",
    "segment.io",
    "tiktok.com/i18n",
    "clarity.ms",
    "linkedin.com/px",
    "pinimg.com",
    "pinterest.com/tag",
    "snapchat.com/p",
    "twitter.com/uwt",
    "static.ads-twitter.com",
)

RU_EXTRA_TRACKING = (
    "top-fwz1.mail.ru",
    "top.mail.ru",
    "vk.com/rtrg",
    "vk-pixel",
    "api.getbeamer.com",
    "carrotquest.io",
    "jivosite",
    "envybox.io",
)


def _tracking_haystack(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    parts: list[str] = []
    for tag in soup.find_all("script"):
        src = tag.get("src")
        if src:
            if not script_url_is_vendor_bundle(str(src)):
                parts.append(str(src))
        elif tag.string:
            parts.append(tag.string[:4000])
    return " ".join(parts).lower()


def detect_ru_analytics(html: str) -> list[str]:
    haystack = _tracking_haystack(html)
    markers = RU_ANALYTICS_MARKERS + RU_EXTRA_TRACKING
    return [m for m in markers if m in haystack]


def detect_foreign_analytics(html: str) -> list[str]:
    haystack = _tracking_haystack(html)
    return [m for m in FOREIGN_ANALYTICS_MARKERS if m in haystack]


def detect_measurable_tracking(html: str) -> list[str]:
    return sorted(set(detect_ru_analytics(html) + detect_foreign_analytics(html)))