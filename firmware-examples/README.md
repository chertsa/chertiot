# firmware-examples/
Student starter code, one folder per track. The portal renders these with the student's values
(`portal/app/snippets.py`) — never edit placeholders into real tokens here.

| Placeholder | Meaning |
|---|---|
| `{{MQTT_HOST}}` | MQTT broker hostname (the platform domain) |
| `{{MQTT_PORT}}` | 8883 (TLS) in staging/prod; 1883 in local dev |
| `{{HTTP_URL}}` | TB HTTP transport base URL (browser track) |
| `{{ACCESS_TOKEN}}` | the device's access token (MQTT username) |
| `{{DEVICE_NAME}}` | the device name, used as MQTT client id |

Every file must stay compilable/runnable with the placeholder text in place of values.
