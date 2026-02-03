from qmc5883l import QMC5883L
import time

# Автопоиск датчика на адресах 0x0D и 0x2C
sensor = QMC5883L()

print("Направление от магнитного севера:")
try:
    while True:
        m = sensor.get_magnet()  # Получаем вектор (x, y, z)
        angle = sensor.get_bearing()  # Встроенная функция для азимута
        print(f"\rАзимут: {angle:6.1f}°  |  Вектор: X:{m[0]:6.1f} Y:{m[1]:6.1f} Z:{m[2]:6.1f} μT", end="")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nЗавершено")