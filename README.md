# vgencmd-mqtt-publisher
Gather stats with vgencmd and publish them to the MQTT in Home Assistant compatible format

# Installation

1. Checkout
2. pip install -r requirements.txt
3. ln -s <path-to>/publisher.py /usr/bin/mqtt-sensors
4. cp mqtt-sensors.service /etc/systemd/system/mqtt-sensors.service
5. systemctl edit mqtt-sensors.service

```
[Service]
Environment="TZ=Europe/Moscow"
Environment="MQTT_HOST=mqtt.local"
Environment="MQTT_PORT=1883"
Environment="MQTT_USER="
Environment="MQTT_PASS="
Environment="DEVICE_NAME=st-node-3"
Environment="WAIT_TIME_SECONDS=15"
Environment="TRACKED_MOUNTS=root:/;docker:/docker"
```

6. systemctl enable mqtt-sensors.service
7. systemctl start mqtt-sensors.service
8. Enjoy

# Testing

You can modify `publisher.py` and test it without messing with systemctl first

1. Put you envs into `test.env` file
```
TZ=Europe/Moscow
MQTT_HOST=mqtt.local
MQTT_PORT=1883
MQTT_USER=
MQTT_PASS=
DEVICE_NAME=st-node-3
WAIT_TIME_SECONDS=15
TRACKED_MOUNTS=root:/;docker:/docker
```
2. Run `test.sh`

# Screenshots

Script uploads values according to default HA settings in order to create entity around given host

![image](https://user-images.githubusercontent.com/6578413/201254683-d9c83265-8fe6-42dc-bb04-ef40aee409a0.png)

# Credits

Based on gist https://gist.github.com/Sennevds/1ff538ba80978810019af3d5da92118f by @Sennevds

# Other thougts

Tried to make it a docker container, but failed. A ton of volumes is required for container to properly monitor host stats, also there is a trouble getting vcgencmd command working in python:3-alpine or python:3-slim images
