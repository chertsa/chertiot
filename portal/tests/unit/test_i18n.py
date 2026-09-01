from fastapi.testclient import TestClient

from app.main import app


def test_arabic_toggle_switches_language_and_direction() -> None:
    c = TestClient(app, follow_redirects=False)
    r = c.get("/lang/ar", headers={"referer": "/"})
    assert r.status_code == 303 and "lang=ar" in r.headers.get("set-cookie", "")
    r = c.get("/", cookies={"lang": "ar"})
    assert 'dir="rtl"' in r.text and 'lang="ar"' in r.text
    assert "مختبرك الخاص لإنترنت الأشياء" in r.text  # hero headline in Arabic
    assert ">English<" in r.text  # toggle offers the other language
    r = c.get("/", cookies={"lang": "en"})
    assert 'dir="ltr"' in r.text and "Your own IoT lab" in r.text and ">العربية<" in r.text
