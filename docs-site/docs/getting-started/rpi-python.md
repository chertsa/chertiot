# Raspberry Pi (or any Linux computer) with Python

**You need:** Python 3.9+ and `pip install paho-mqtt`.

1. Download `chertiot_starter.py` from your device page.
2. `python3 chertiot_starter.py` — it prints one reading every 10 seconds.
3. Open **My dashboard**.

Turn it into a service with `systemd` or `cron @reboot` once your sensor code works. To read a DS18B20 on 1-Wire, replace the random values with the contents of `/sys/bus/w1/devices/28-*/w1_slave`.
