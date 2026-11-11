from app.scraper.html_clean import clean_html

PAGE = """<html><head><title>Wireless Headphones Pro | Shop</title>
<meta name="description" content="Great headphones.">
<script>trackEvent("view")</script>
<script type="application/ld+json">{"@type": "Product", "name": "Wireless Headphones Pro", "offers": {"price": "42.99"}}</script>
<style>.x{color:red}</style></head>
<body><nav>Home | Cart</nav><h1>Wireless Headphones Pro</h1><p>Price:&nbsp;$42.99</p><footer>(c) Shop</footer></body></html>"""


def test_keeps_content_and_drops_noise():
    page = clean_html(PAGE)
    assert page.title == "Wireless Headphones Pro | Shop"
    assert "Wireless Headphones Pro" in page.text
    assert "Price: $42.99" in page.text
    assert "trackEvent" not in page.text
    assert "color:red" not in page.text
    assert "Cart" not in page.text  # navigation removed
    assert page.text.startswith("Great headphones.")


def test_extracts_json_ld():
    page = clean_html(PAGE)
    assert '"price":"42.99"' in page.json_ld
