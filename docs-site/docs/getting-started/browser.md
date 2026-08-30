# Browser — no hardware needed

Download `index.html` from your device page and open it in any browser. It posts a reading every 10 seconds over HTTPS to ThingsBoard's HTTP transport, so you can try the dashboard before your board arrives. Move the two sliders and watch the chart follow.

Under the hood it does exactly this — useful for scripts, curl, or a phone app:

```
POST https://app.chertiot.com/api/v1/<ACCESS_TOKEN>/telemetry
Content-Type: application/json

{"temperature": 22.5, "humidity": 45}
```
