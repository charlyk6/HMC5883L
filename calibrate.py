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


def save_calibration(calib, filename=CALIBRATION_FILE):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(calib, f, indent=2, ensure_ascii=False)


def calibrate_2d(sensor, seconds=30):
    print("\n=== КАЛИБРОВКА КОМПАСА ===")
    print("Держи датчик как можно горизонтальнее.")
    print("Медленно вращай его по кругу.")
    print("Сделай несколько полных оборотов за 30 секунд.\n")

    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")

    start = time.time()
    last_print = -1
    samples = 0

    while True:
        elapsed = time.time() - start
        if elapsed >= seconds:
            break

        x, y, z, _ = sensor.read_scaled()

        min_x = min(min_x, x)
        max_x = max(max_x, x)
        min_y = min(min_y, y)
        max_y = max(max_y, y)

        samples += 1

        remaining = int(seconds - elapsed)
        if remaining != last_print:
            last_print = remaining
            print(
                f"Осталось ~ {remaining:2d} c | "
                f"X:[{min_x:8.4f}, {max_x:8.4f}] "
                f"Y:[{min_y:8.4f}, {max_y:8.4f}]"
            )

        time.sleep(0.05)

    offset_x = (max_x + min_x) / 2.0
    offset_y = (max_y + min_y) / 2.0

    radius_x = (max_x - min_x) / 2.0
    radius_y = (max_y - min_y) / 2.0

    if radius_x <= 0 or radius_y <= 0:
        raise RuntimeError("Слишком маленький разброс данных для калибровки.")

    avg_radius = (radius_x + radius_y) / 2.0
    scale_x = avg_radius / radius_x
    scale_y = avg_radius / radius_y

    calib = {
        "offset_x": offset_x,
        "offset_y": offset_y,
        "scale_x": scale_x,
        "scale_y": scale_y,
        "radius_x": radius_x,
        "radius_y": radius_y,
        "samples": samples
    }

    return calib


def main():
    i2c = RPiI2C(1)
    sensor = QMC5883P(i2c)

    try:
        calib = calibrate_2d(sensor, seconds=30)

        print("\n=== ГОТОВО ===")
        print(json.dumps(calib, indent=2, ensure_ascii=False))

        save_calibration(calib)
        print(f"\nКалибровка сохранена в файл: {CALIBRATION_FILE}")

    except KeyboardInterrupt:
        print("\nКалибровка остановлена пользователем.")
    finally:
        i2c.close()


if __name__ == "__main__":
    main()