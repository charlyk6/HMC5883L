import math
import time
import json
from smbus2 import SMBus
from qmc5883p import QMC5883P


CALIBRATION_FILE = "compass_calibration.json"


class RPiI2C:
    def __init__(self, bus_num=1):
        self.bus = SMBus(bus_num)
        self._last_reg = None

    def writeto(self, addr, data):
        data = bytes(data)

        if len(data) == 1:
            self._last_reg = data[0]
            return

        reg = data[0]
        payload = list(data[1:])

        if len(payload) == 1:
            self.bus.write_byte_data(addr, reg, payload[0])
        else:
            self.bus.write_i2c_block_data(addr, reg, payload)

        self._last_reg = reg

    def readfrom(self, addr, nbytes):
        if self._last_reg is None:
            raise RuntimeError("Register address was not set before readfrom()")
        data = self.bus.read_i2c_block_data(addr, self._last_reg, nbytes)
        return bytes(data)

    def close(self):
        self.bus.close()


def normalize_angle_deg(angle):
    angle %= 360.0
    if angle < 0:
        angle += 360.0
    return angle


def smooth_angle_deg(prev_angle, new_angle, alpha=0.15):
    if prev_angle is None:
        return new_angle

    delta = new_angle - prev_angle
    while delta > 180.0:
        delta -= 360.0
    while delta < -180.0:
        delta += 360.0

    return normalize_angle_deg(prev_angle + alpha * delta)


def load_calibration(filename=CALIBRATION_FILE):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_calibration(x, y, calib):
    x_corr = (x - calib["offset_x"]) * calib["scale_x"]
    y_corr = (y - calib["offset_y"]) * calib["scale_y"]
    return x_corr, y_corr


def main():
    i2c = RPiI2C(1)
    sensor = QMC5883P(i2c)
    calib = load_calibration()

    declination_deg = 0.0
    smoothed_yaw = None

    print("QMC5883P yaw started. Formula: atan2(y_corr, -x_corr)")
    print("Ctrl+C to stop.\n")

    try:
        while True:
            x, y, z, _ = sensor.read_scaled()

            x_corr, y_corr = apply_calibration(x, y, calib)

            # Формула №4
            yaw_deg = math.degrees(math.atan2(y_corr, -x_corr))
            yaw_deg += declination_deg
            yaw_deg = normalize_angle_deg(yaw_deg)

            smoothed_yaw = smooth_angle_deg(smoothed_yaw, yaw_deg, alpha=0.15)

            print(
                f"Yaw={smoothed_yaw:7.2f}°   "
                f"Xc={x_corr:8.4f}   "
                f"Yc={y_corr:8.4f}   "
                f"Z={z:8.4f}"
            )

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        i2c.close()


if __name__ == "__main__":
    main()