import math
import time
import json
import os
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


def smooth_angle_deg(prev_angle, new_angle, alpha=0.2):
    if prev_angle is None:
        return new_angle

    delta = new_angle - prev_angle
    while delta > 180.0:
        delta -= 360.0
    while delta < -180.0:
        delta += 360.0

    smoothed = prev_angle + alpha * delta
    return normalize_angle_deg(smoothed)


def save_calibration(calib, filename=CALIBRATION_FILE):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(calib, f, indent=2)


def load_calibration(filename=CALIBRATION_FILE):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def calibrate_2d(sensor, seconds=30):
    print("\n=== КАЛИБРОВКА КОМПАСА ===")
    print("1. Держи модуль как можно ГОРИЗОНТАЛЬНЕЕ.")
    print("2. Медленно вращай его по кругу.")
    print("3. Лучше сделать несколько полных оборотов за 30 секунд.")
    print("4. Держи подальше от металла, магнитов, проводов питания и Raspberry Pi.\n")

    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")

    start = time.time()
    last_second_printed = -1
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
        if remaining != last_second_printed:
            last_second_printed = remaining
            print(
                f"Осталось ~ {remaining:2d} c | "
                f"X:[{min_x:8.4f}, {max_x:8.4f}] "
                f"Y:[{min_y:8.4f}, {max_y:8.4f}]"
            )

        time.sleep(0.05)

    if min_x == float("inf") or min_y == float("inf"):
        raise RuntimeError("Не удалось собрать данные калибровки.")

    offset_x = (max_x + min_x) / 2.0
    offset_y = (max_y + min_y) / 2.0

    radius_x = (max_x - min_x) / 2.0
    radius_y = (max_y - min_y) / 2.0

    if radius_x <= 0 or radius_y <= 0:
        raise RuntimeError("Слишком маленький разброс данных. Попробуй покрутить датчик шире и дольше.")

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

    print("\n=== КАЛИБРОВКА ЗАВЕРШЕНА ===")
    print(json.dumps(calib, indent=2, ensure_ascii=False))
    print()

    return calib


def apply_calibration(x, y, calib):
    x_corr = (x - calib["offset_x"]) * calib["scale_x"]
    y_corr = (y - calib["offset_y"]) * calib["scale_y"]
    return x_corr, y_corr


def main():
    i2c = RPiI2C(1)
    sensor = QMC5883P(i2c)

    # Если нужно менять формулу yaw, меняй только этот блок.
    # Стартуем с самого стандартного варианта:
    use_formula = "atan2(y, x)"

    # Магнитное склонение пока оставим 0.
    # Можно потом добавить поправку, если понадобится.
    declination_deg = 0.0

    # Сглаживание угла
    alpha = 0.15
    smoothed_yaw = None

    try:
        print("Выбери режим:")
        print("1 - новая калибровка")
        print("2 - использовать сохранённую калибровку")
        choice = input("Введи 1 или 2: ").strip()

        if choice == "2" and os.path.exists(CALIBRATION_FILE):
            calib = load_calibration(CALIBRATION_FILE)
            print("\nЗагружена сохранённая калибровка:")
            print(json.dumps(calib, indent=2, ensure_ascii=False))
            print()
        else:
            calib = calibrate_2d(sensor, seconds=30)
            save_calibration(calib)
            print(f"Калибровка сохранена в файл: {CALIBRATION_FILE}\n")

        print("=== РЕЖИМ YAW ===")
        print("Ctrl+C для остановки.\n")

        while True:
            x, y, z, _ = sensor.read_scaled()
            x_corr, y_corr = apply_calibration(x, y, calib)

            if use_formula == "atan2(y, x)":
                yaw_deg = math.degrees(math.atan2(y_corr, x_corr))
            elif use_formula == "atan2(x, y)":
                yaw_deg = math.degrees(math.atan2(x_corr, y_corr))
            elif use_formula == "atan2(-y, x)":
                yaw_deg = math.degrees(math.atan2(-y_corr, x_corr))
            elif use_formula == "atan2(y, -x)":
                yaw_deg = math.degrees(math.atan2(y_corr, -x_corr))
            else:
                yaw_deg = math.degrees(math.atan2(y_corr, x_corr))

            yaw_deg += declination_deg
            yaw_deg = normalize_angle_deg(yaw_deg)
            smoothed_yaw = smooth_angle_deg(smoothed_yaw, yaw_deg, alpha=alpha)

            print(
                f"Yaw={smoothed_yaw:7.2f}°   "
                f"Xc={x_corr:8.4f}   "
                f"Yc={y_corr:8.4f}   "
                f"Z={z:8.4f}"
            )

            time.sleep(0.10)

    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")
    finally:
        i2c.close()


if __name__ == "__main__":
    main()