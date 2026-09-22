from fastapi.testclient import TestClient

from app.main import app


def test_arabic_is_translation_only_ltr() -> None:
    """CHERT IoT is translation-only: Arabic sets lang=ar but the layout stays LTR (no RTL)."""
    c = TestClient(app, follow_redirects=False)
    r = c.get("/lang/ar", headers={"referer": "/"})
    assert r.status_code == 303 and "lang=ar" in r.headers.get("set-cookie", "")
    r = c.get("/", cookies={"lang": "ar"})
    # Arabic language, but LTR layout — never dir="rtl"
    assert 'lang="ar"' in r.text and 'dir="ltr"' in r.text
    assert 'dir="rtl"' not in r.text
    assert "مختبرك الخاص لإنترنت الأشياء" in r.text  # hero headline in Arabic (translated)
    assert ">English<" in r.text  # toggle offers the other language
    # English unchanged: lang=en, dir=ltr
    r = c.get("/", cookies={"lang": "en"})
    assert 'lang="en"' in r.text and 'dir="ltr"' in r.text
    assert "Your own IoT lab" in r.text and ">العربية<" in r.text
