# LoRaWAN gateways and devices

CHERT IoT runs a full LoRaWAN network server (ChirpStack). Your LoRa uplinks arrive on the same dashboard as your Wi-Fi devices.

## 1. Register a device
In the portal, open **LoRaWAN → Register a LoRa device**. You get a **DevEUI** and an **AppKey** (OTAA, EU868, LoRaWAN 1.0.3). A matching device is created for you automatically.

## 2. Flash your node
Program your LoRaWAN node (Arduino MKR WAN, Heltec, RAK, …) for **OTAA** with:

- **DevEUI** — from the portal
- **AppKey** — from the portal
- **JoinEUI/AppEUI** — all zeros (`0000000000000000`)
- Region **EU868**

## 3. Point a gateway at the platform
Configure your gateway's **Semtech UDP packet forwarder** to send to:

- **Server address:** `chertiot.com`
- **Port (uplink & downlink):** `1700`
- **Region:** EU868

That's it — once the gateway is online and your node joins, decoded uplinks appear as telemetry on your device in **My dashboard**. Send a numeric payload (a decoded `object` in your codec) and it charts automatically; raw payloads arrive as `raw_hex` plus `rssi`/`snr`.

## No hardware yet?
The platform includes a simulator so you can see the flow end to end before a gateway arrives — ask your instructor, or watch your dashboard after registering (a demo uplink is injected for new LoRa devices on staging).
