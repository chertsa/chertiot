# ESP32 مع MicroPython

**تحتاج إلى:** ESP32 عليه MicroPython حديث (`esptool` مع ملف `.bin` الرسمي)، وThonny أو `mpremote`.

1. نزّل `main.py` من صفحة جهازك في البوابة.
2. عيّن `WIFI_SSID` و`WIFI_PASSWORD`.
3. انسخ الملف إلى اللوحة (`mpremote cp main.py :main.py`) وأعد تشغيلها. يطبع REPL قراءة كل 10 ثوانٍ.
4. افتح **لوحتي**.

مكتبة `umqtt.simple` مضمنة في البناء الرسمي. الكود يتصل عبر TLS على 8883؛ MQTT غير المشفّر غير متاح على المنصة العامة.
