#! /usr/bin/env python3

# based on https://gist.github.com/Sennevds/1ff538ba80978810019af3d5da92118f
from subprocess import check_output
from re import findall
import psutil
import sys
import os
import threading, time, signal
from datetime import timedelta
import datetime as dt
import paho.mqtt.client as mqtt
import pytz
import json
from pytz import timezone


# Config
broker_url = os.getenv('MQTT_HOST') #MQTT server IP
deviceName = os.getenv('DEVICE_NAME') #Name off your PI

DEFAULT_TIME_ZONE = timezone(os.getenv('TZ','Europe/Moscow'))#Local Time zone
broker_port = int(os.getenv('MQTT_PORT', 1883)) #MQTT server port
broker_user = os.getenv('MQTT_USER', '')
broker_pass = os.getenv('MQTT_PASS' ,'')
trackedMounts = os.getenv('TRACKED_MOUNTS',  'root:/')

WAIT_TIME_SECONDS = int(os.getenv("SLEEP_TIME", 60))

PROCFS_PATH = os.getenv("PROC_PATH", "/proc")
MODEL_PATH = os.getenv("MODEL_PATH", "/sys/firmware/devicetree/base/model")
VCGENCMD = os.getenv("VCGENCMD", "vcgencmd")

psutil.PROCFS_PATH = PROCFS_PATH

UTC = pytz.utc
SYSFILE = '/sys/devices/platform/soc/soc:firmware/get_throttled'

client = mqtt.Client()
client.username_pw_set(broker_user, broker_pass)

class ProgramKilled(Exception):
    pass

def signal_handler(signum, frame):
    raise ProgramKilled

class Job(threading.Thread):
    def __init__(self, interval, execute, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = False
        self.stopped = threading.Event()
        self.interval = interval
        self.execute = execute
        self.args = args
        self.kwargs = kwargs
        
    def stop(self):
                self.stopped.set()
                self.join()
    def run(self):
            while not self.stopped.wait(self.interval.total_seconds()):
                self.execute(*self.args, **self.kwargs)

def utc_from_timestamp(timestamp: float) -> dt.datetime:
    """Return a UTC time from a timestamp."""
    return UTC.localize(dt.datetime.utcfromtimestamp(timestamp))

def as_local(dattim: dt.datetime) -> dt.datetime:
    """Convert a UTC datetime object to local time zone."""
    if dattim.tzinfo == DEFAULT_TIME_ZONE:
        return dattim
    if dattim.tzinfo is None:
        dattim = UTC.localize(dattim)

    return dattim.astimezone(DEFAULT_TIME_ZONE)

def get_last_boot():
    return str(as_local(utc_from_timestamp(psutil.boot_time())).isoformat())

def update_sensors():
    mounts = {}
    
    for pair in trackedMounts.split(";"):
        mountConf = pair.split(":")
        mountPath = mountConf[1]
        mountName = mountConf[0]
        
        mounts[mountName] = get_disk_usage(mountPath)


    client.publish(
        topic=get_state_topic(), 
        payload=json.dumps({
            "temperature": get_temp(),
            "disk_use": mounts,
            "memory_use": get_memory_usage(),
            "cpu_usage": get_cpu_usage(),
            "power_status": get_rpi_power_status(),
            "last_boot": get_last_boot(),
        }),
        qos=1, retain=False
    )

def get_temp():
    temp = check_output([VCGENCMD,"measure_temp"]).decode("UTF-8")
    return str(findall("\d+\.\d+",temp)[0])

def get_model():
    model = check_output(["cat", MODEL_PATH]).decode("UTF-8")
    return str(model)


def get_disk_usage(mountPath):
    return str(psutil.disk_usage(mountPath).percent)

def get_memory_usage():
    return str(psutil.virtual_memory().percent)

def get_cpu_usage():
    return str(psutil.cpu_percent(interval=None))

def get_rpi_power_status():
    _throttled = open(SYSFILE, 'r').read()[:-1]
    _throttled = _throttled[:4]
    if _throttled == '0':
        return 'OK'
    elif _throttled == '1000':
        return 'Undervoltage'
    elif _throttled == '2000':
        return 'Throttling due to power outage'
    elif _throttled == '3000':
        return 'Throttling due to power outage'
    elif _throttled == '4000':
        return 'Heavy throttling due to power outage'
    elif _throttled == '5000':
        return 'Heavy throttling due to power outage'
    elif _throttled == '8000':
        return 'Overheating'
    else:
        return 'Unable to get power status'

def get_state_topic():
    return "homeassistant/sensor/"+ deviceName +"/state"

def configure_device(): 
    deviceInfo = {
        "identifiers": [deviceName],
        "name": deviceName,
        "manufacturer": "Raspberry PI Foundation",
        "model": get_model()
    }
    
    client.publish(
        topic="homeassistant/sensor/"+ deviceName +"/temperature/config",  
        payload=json.dumps({
        "unique_id": deviceName + "_temperature",
            "device": deviceInfo,
            "name": deviceName + " Temperature",
            "icon": "mdi:coolant-temperature",
            "state_topic": get_state_topic(),
            "device_class": "temperature",
            "unit_of_measurement": "°C", 
            "value_template": "{{ value_json.temperature}}",
            "enabled_by_default": True,
        }, default=dumper), qos=1, retain=True
    )

    for pair in trackedMounts.split(";"):
        mountConf = pair.split(":")
        mountPath = mountConf[1]
        mountName = mountConf[0]

        client.publish(
            topic="homeassistant/sensor/"+ deviceName +"/disk_usage_"+mountName+"/config",  
            payload=json.dumps({
                "unique_id": deviceName + "_disk_usage_" + mountName,
                "device": deviceInfo,
                "name": deviceName + " Disk Usage (" + mountName + ")",
                "icon": "mdi:harddisk",
                "state_topic": get_state_topic(),
                "unit_of_measurement": "%", 
                "value_template": "{{ value_json.disk_use."+mountName+"}}",
                "enabled_by_default": True,
            }, default=dumper), qos=1, retain=True
        )
    
    client.publish(
        topic="homeassistant/sensor/"+ deviceName +"/memory_usage/config",  
        payload=json.dumps({
            "unique_id": deviceName + "_memory_usage",
            "device": deviceInfo,
            "name": deviceName + " Memory Usage",
            "icon": "mdi:memory",
            "state_topic": get_state_topic(),
            "unit_of_measurement": "%", 
            "value_template": "{{ value_json.memory_use}}",
            "enabled_by_default": True,
        }, default=dumper), qos=1, retain=True
    )

    client.publish(
        topic="homeassistant/sensor/"+ deviceName +"/cpu_usage/config",  
        payload=json.dumps({
            "unique_id": deviceName + "_cpu_usage",
            "device": deviceInfo,
            "name": deviceName + " Cpu Usage",
            "icon": "mdi:cpu-64-bit",
            "state_topic": get_state_topic(),
            "unit_of_measurement": "%", 
            "value_template": "{{ value_json.cpu_usage}}",
            "enabled_by_default": True,
        }, default=dumper), qos=1, retain=True
    )

    client.publish(
        topic="homeassistant/sensor/"+ deviceName +"/power_status/config",  
        payload=json.dumps({
            "unique_id": deviceName + "_power_status",
            "device": deviceInfo,
            "name": deviceName + " Power Status",
            "icon": "mdi:power-plug",
            "state_topic": get_state_topic(),
            "value_template": "{{ value_json.power_status}}",
            "enabled_by_default": True,
        }, default=dumper), qos=1, retain=True
    )

    client.publish(
        topic="homeassistant/sensor/"+ deviceName +"/last_boot/config",  
        payload=json.dumps({
            "unique_id": deviceName + "_last_boot",
            "device": deviceInfo,
            "name": deviceName + " Last Boot",
            "icon": "mdi:clock",
            "state_topic": get_state_topic(),
            "device_class": "timestamp",
            "unit_of_measurement": "°C", 
            "value_template": "{{ value_json.last_boot}}",
            "enabled_by_default": True,
        }, default=dumper), qos=1, retain=True
    )

def dumper(obj):
    try:
        return obj.toJSON()
    except:
        return obj.__dict__

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    client.connect(broker_url, broker_port)
    
    configure_device()
    update_sensors()

    job = Job(interval=timedelta(seconds=WAIT_TIME_SECONDS), execute=update_sensors)
    job.start()
    client.loop_forever()
   
    while True:
            try:
                time.sleep(1)
            except ProgramKilled:
                print ("Program killed: running cleanup code")
                sys.stdout.flush()
                job.stop()
                break
    
