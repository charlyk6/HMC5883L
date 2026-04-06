import builtins
import time
from smbus2 import SMBus

# --- Совместимость с MicroPython ---
if not hasattr(builtins, "const"):
    builtins.const = lambda x: x

if not hasattr(time, "sleep_ms"):
    def sleep_ms(ms):
        time.sleep(ms / 1000.0)
    time.sleep_ms = sleep_ms

# Импортируем уже существующий драйвер из репозитория
from qmc5883p import QMC5883P


class RPiI2C:
    """
    Адаптер под интерфейс, который ожидает qmc5883p.py:
      - writeto(addr, data)
      - readfrom(addr, nbytes)
    """

    def __init__(self, bus_num=1):
        self.bus = SMBus(bus_num)
        self._last_reg = None

    def writeto(self, addr, data):
        data = bytes(data)

        # Случай 1: драйвер пишет только адрес регистра перед чтением
        # self.i2c.writeto(addr, bytes([reg]))
        if len(data) == 1:
            self._last_reg = data[0]
            return

        # Случай 2: драйвер пишет регистр + данные
        reg = data[0]
        payload = list(data[1:])

        if len(payload) == 1:
            self.bus.write_byte_data(addr, reg, payload[0])
        else:
            self.bus.write_i2c_block_data(addr, reg, payload)

        self._last_reg = reg

    def readfrom(self, addr, nbytes):
        if self._last_reg is None:
            raise RuntimeError("I2C register was not selected before readfrom()")
        data = self.bus.read_i2c_block_data(addr, self._last_reg, nbytes)
        return bytes(data)

    def close(self):
        self.bus.close()


def main():
    i2c = RPiI2C(1)
    sensor = QMC5883P(i2c)

    print("QMC5883P started. Ctrl+C to stop.\n")

    try:
        while True:
            # ВАЖНО: в реальном коде read_raw() возвращает 3 значения, а не 4
            x, y, z = sensor.read_raw()
            xs, ys, zs, _ = sensor.read_scaled()

            print(
                f"RAW  X={x:6d} Y={y:6d} Z={z:6d}   "
                f"SCALED X={xs:7.3f}G Y={ys:7.3f}G Z={zs:7.3f}G"
            )
            time.sleep(0.3)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        i2c.close()


if __name__ == "__main__":
    main()