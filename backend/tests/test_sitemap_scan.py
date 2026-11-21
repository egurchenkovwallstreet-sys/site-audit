from app.scan.site_pages import plan_scan_page_urls, sitemap_page_urls

CIAN_INDEX = """<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>https://www.cian.ru/sitemap1.xml.gz</loc></sitemap>
<sitemap><loc>https://www.cian.ru/sitemap2.xml.gz</loc></sitemap>
</sitemapindex>"""


def test_sitemap_index_skips_gz():
    urls = sitemap_page_urls("https://www.cian.ru/", CIAN_INDEX, limit=20)
    assert urls == []


def test_plan_includes_legal_not_gz():
    html = "<html><body><a href='/cat/1/'>x</a></body></html>"
    plan = plan_scan_page_urls(
        "https://www.cian.ru/",
        html,
        extra_urls=sitemap_page_urls("https://www.cian.ru/", CIAN_INDEX),
        max_pages=15,
    )
    assert not any(".gz" in u for u in plan)
    assert any("legal-documents" in u for u in plan)