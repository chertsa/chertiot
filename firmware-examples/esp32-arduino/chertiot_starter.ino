// CHERT IoT starter — ESP32 (Arduino core). Sends a temperature/humidity reading every 10 s.
// Libraries: "PubSubClient" (Nick O'Leary). Board: any ESP32.
// Placeholders {{...}} are filled in by the portal when you download this file.
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

const char* MQTT_HOST  = "{{MQTT_HOST}}";
const int   MQTT_PORT  = {{MQTT_PORT}};        // 8883 = TLS
const char* MQTT_TOKEN = "{{ACCESS_TOKEN}}";   // device access token = MQTT username
const char* TOPIC      = "v1/devices/me/telemetry";

WiFiClientSecure net;
PubSubClient mqtt(net);

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.printf("\nWiFi ok: %s\n", WiFi.localIP().toString().c_str());
}

void connectMqtt() {
  while (!mqtt.connected()) {
    Serial.print("MQTT connecting... ");
    if (mqtt.connect("{{DEVICE_NAME}}", MQTT_TOKEN, NULL)) {
      Serial.println("ok");
    } else {
      Serial.printf("failed rc=%d, retry in 5 s\n", mqtt.state());
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  connectWifi();
  net.setInsecure();   // Let's Encrypt chain is trusted by default on most cores; setInsecure() skips
                       // verification for the lab. Replace with setCACert(...) for production devices.
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
}

void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  // Replace with a real sensor read (DHT22, BME280, ...). Random values keep the demo alive.
  float temperature = 20.0 + (random(0, 100) / 10.0);
  float humidity    = 40.0 + (random(0, 200) / 10.0);
  char payload[96];
  snprintf(payload, sizeof(payload), "{\"temperature\":%.1f,\"humidity\":%.1f}", temperature, humidity);
  mqtt.publish(TOPIC, payload);
  Serial.println(payload);
  delay(10000);
}
