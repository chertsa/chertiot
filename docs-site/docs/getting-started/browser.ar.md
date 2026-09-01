# المتصفح — بلا عتاد

نزّل `index.html` من صفحة جهازك وافتحه في أي متصفح. يرسل قراءة كل 10 ثوانٍ عبر HTTPS إلى منفذ HTTP في ThingsBoard، لتجرب لوحة التحكم قبل وصول لوحتك. حرّك القيمتين وشاهد الرسم يتبعهما.

خلف الكواليس يفعل هذا بالضبط — مفيد للسكربتات أو curl:

```
POST https://app.chertiot.com/api/v1/<ACCESS_TOKEN>/telemetry
Content-Type: application/json

{"temperature": 22.5, "humidity": 45}
```
