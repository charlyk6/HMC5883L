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


def normalize_angle(angle):
    angle %= 360.0
    if angle < 0:
        angle += 360.0
    return angle


def smooth(prev, new, alpha=0.15):
    if prev is None:
        return new

    delta = new - prev
    while delta > 180:
        delta -= 360
    while delta < -180:
        delta += 360

    return normalize_angle(prev + alpha * delta)


def load_calibration():
    with open(CALIBRATION_FILE, "r") as f:
        return json.load(f)


def main():
    i2c = RPiI2C(1)
    sensor = QMC5883P(i2c)

    calib = load_calibration()

    sm1 = sm2 = sm3 = sm4 = None

    print("All yaw formulas (calibrated). Ctrl+C to stop.\n")

    try:
        while True:
            x, y, z, _ = sensor.read_scaled()

            # --- калибровка ---
            x_corr = (x - calib["offset_x"]) * calib["scale_x"]
            y_corr = (y - calib["offset_y"]) * calib["scale_y"]

            # --- 4 формулы ---
            yaw1 = normalize_angle(math.degrees(math.atan2(y_corr, x_corr)))
            yaw2 = normalize_angle(math.degrees(math.atan2(x_corr, y_corr)))
            yaw3 = normalize_angle(math.degrees(math.atan2(-y_corr, x_corr)))
            yaw4 = normalize_angle(math.degrees(math.atan2(y_corr, -x_corr)))

            # --- сглаживание ---
            sm1 = smooth(sm1, yaw1)
            sm2 = smooth(sm2, yaw2)
            sm3 = smooth(sm3, yaw3)
            sm4 = smooth(sm4, yaw4)

            print(
                f"Y1={sm1:7.2f}°  "
                f"Y2={sm2:7.2f}°  "
                f"Y3={sm3:7.2f}°  "
                f"Y4={sm4:7.2f}°"
            )

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        i2c.close()


if __name__ == "__main__":
    main()