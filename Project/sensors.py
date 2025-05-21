import random
import math
import datetime
import time

class Sensor:
    def __init__(self, sensor_id, name, unit, min_value, max_value, frequency=1):
        self.sensor_id = sensor_id
        self.name = name
        self.unit = unit
        self.min_value = min_value
        self.max_value = max_value
        self.frequency = frequency
        self.active = True
        self.last_value = None
        self.last_read_time = None
        self.history = []

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")
        now = time.time()
        if self.last_read_time is not None and now - self.last_read_time < self.frequency:
            return self.last_value

        value = self.generate_value()
        self.last_value = value
        self.last_read_time = now
        self.history.append(value)
        return value

    def generate_value(self):
        return random.uniform(self.min_value, self.max_value)

    def calibrate(self, calibration_factor):
        if self.last_value is None:
            self.read_value()
        self.last_value *= calibration_factor
        return self.last_value

    def get_last_value(self):
        if self.last_value is None:
            return self.read_value()
        return self.last_value

    def start(self):
        self.active = True

    def stop(self):
        self.active = False

    def get_status(self):
        return "aktywny" if self.active else "nieaktywny"

    def __str__(self):
        return f"Sensor(id={self.sensor_id}, name={self.name}, unit={self.unit}, status={self.get_status()})"


class TemperatureSensor(Sensor):
    def __init__(self, sensor_id="T1"):
        super().__init__(sensor_id, "Temperatura zewnętrzna", "°C", -20, 50, frequency=1)

    def generate_value(self):
        hour = datetime.datetime.now().hour
        base = 15 + 10 * math.sin((math.pi / 12) * (hour - 6))
        noise = random.uniform(-2, 2)
        return min(max(base + noise, self.min_value), self.max_value)


class HumiditySensor(Sensor):
    def __init__(self, sensor_id="H1"):
        super().__init__(sensor_id, "Wilgotność względna", "%", 0, 100, frequency=2)

    def generate_value(self):
        temp_effect = -0.2 * (self.last_value if self.last_value else 20)
        value = random.uniform(40, 70) + temp_effect + random.uniform(-5, 5)
        return min(max(value, self.min_value), self.max_value)


class PressureSensor(Sensor):
    def __init__(self, sensor_id="P1"):
        super().__init__(sensor_id, "Ciśnienie atmosferyczne", "hPa", 950, 1050, frequency=4)

    def generate_value(self):
        base = 1013.25
        variation = random.uniform(-10, 10)
        return min(max(base + variation, self.min_value), self.max_value)


class LightSensor(Sensor):
    def __init__(self, sensor_id="L1"):
        super().__init__(sensor_id, "Natężenie światła", "lx", 0, 10000, frequency=2)

    def generate_value(self):
        hour = datetime.datetime.now().hour
        base = max(0, 10000 * math.sin((math.pi / 12) * (hour - 6)))
        noise = random.uniform(-200, 200)
        return min(max(base + noise, self.min_value), self.max_value)
