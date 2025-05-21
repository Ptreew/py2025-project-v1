from sensors import TemperatureSensor, HumiditySensor, PressureSensor, LightSensor
import time

sensors = [
    TemperatureSensor(),
    HumiditySensor(),
    PressureSensor(),
    LightSensor()
]

for _ in range(10):
    print("Odczyty:")
    for s in sensors:
        print(f"{s.name} ({s.unit}): {s.read_value():.2f}")
    print("---")
    time.sleep(2)
