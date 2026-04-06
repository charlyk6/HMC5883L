import math
import time
from smbus2 import SMBus
from qmc5883p import QMC5883P


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


def main():
    i2c = RPiI2C(1)
    sensor = QMC5883P(i2c)

    # Если хочешь добавить поправку на локальное магнитное склонение,
    # можешь поменять это значение, например на +4.7 или -3.2
    declination_deg = 0.0

    print("QMC5883P yaw output started. Ctrl+C to stop.\n")

    try:
        while True:
            x, y, z, _ = sensor.read_scaled()

            # yaw / heading по магнитометру
            yaw_deg = math.degrees(math.atan2(y, x))
            yaw_deg += declination_deg
            yaw_deg = normalize_angle_deg(yaw_deg)

            print(f"Yaw: {yaw_deg:7.2f}°   X={x:8.4f}  Y={y:8.4f}  Z={z:8.4f}")
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        i2c.close()


if __name__ == "__main__":
    main()