from smbus2 import SMBus
from qmc5883p import QMC5883P
import time


class RPiI2C:
    def __init__(self, bus_num=1):
        self.bus = SMBus(bus_num)

    def writeto_mem(self, addr, reg, data):
        if isinstance(data, int):
            self.bus.write_byte_data(addr, reg, data)
        else:
            data = bytes(data)
            if len(data) == 1:
                self.bus.write_byte_data(addr, reg, data[0])
            else:
                self.bus.write_i2c_block_data(addr, reg, list(data))

    def readfrom_mem(self, addr, reg, nbytes):
        data = self.bus.read_i2c_block_data(addr, reg, nbytes)
        return bytes(data)

    def close(self):
        self.bus.close()


def main():
    i2c = RPiI2C(1)
    sensor = QMC5883P(i2c)

    print("QMC5883P started. Press Ctrl+C to stop.\n")

    try:
        while True:
            x, y, z, t = sensor.read_raw()
            print(f"RAW: X={x:6d}  Y={y:6d}  Z={z:6d}  T={t}")
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        i2c.close()


if __name__ == "__main__":
    main()