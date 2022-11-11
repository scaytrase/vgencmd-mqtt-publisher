# vgencmd-mqtt-publisher
Gather stats with vgencmd and publish them to the MQTT

# Installation

1. Checkout
2. ln -s <path-to>/publisher.py /usr/bin/mqtt-publisher
3. cp mqtt-sensors.service /etc/systemd/system/mqtt-sensors.service
4. systemctl edit mqtt-sensors.service

```
[Service]
Environment="TZ=Europe/Moscow"
Environment="MQTT_HOST=mqtt.sthome"
Environment="MQTT_PORT=1883"
Environment="MQTT_USER="
Environment="MQTT_PASS="
Environment="DEVICE_NAME=st-node-3"
Environment="WAIT_TIME_SECONDS=15"
Environment="TRACKED_MOUNTS=root:/;docker:/docker"
```

5. systemctl enable mqtt-sensors.service
6. systemctl start mqtt-sensors.service
7. Enjoy

# Testing

You can modify `publisher.py` and test it without messing with systemctl first

1. Put you envs into `test.env` file
```
TZ=Europe/Moscow
MQTT_HOST=mqtt.sthome
MQTT_PORT=1883
MQTT_USER=
MQTT_PASS=
DEVICE_NAME=st-node-3
WAIT_TIME_SECONDS=15
TRACKED_MOUNTS=root:/;docker:/docker
```
2. Run `test.sh`
