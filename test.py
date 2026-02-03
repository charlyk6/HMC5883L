from qmc5883l import QMC5883L
import math
import time

sensor = QMC5883L(0x2C)

print("Направление от магнитного севера:")
try:
    while True:
        # Получаем вектор магнитного поля
        m = sensor.get_magnet()  # Возвращает (x, y, z) в микроТеслах
        
        # ВРУЧНУЮ вычисляем азимут из вектора
        # x - направление на Восток, y - на Север
        x, y = m[0], m[1]  # Берем только горизонтальные компоненты
        
        # Вычисляем угол в радианах (atan2(y, x) дает угол от оси X)
        # Но нам нужен угол от севера (оси Y)
        angle_rad = math.atan2(x, y)  # Для географической системы: atan2(x, y)
        
        # Конвертируем в градусы и нормализуем
        angle_deg = math.degrees(angle_rad)
        if angle_deg < 0:
            angle_deg += 360
        
        print(f"\rАзимут: {angle_deg:6.1f}°  |  Вектор: X:{m[0]:6.1f} Y:{m[1]:6.1f} Z:{m[2]:6.1f} μT", end="")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nЗавершено")