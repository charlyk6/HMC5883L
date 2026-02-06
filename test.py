from qmc5883l import QMC5883L
import math
import time

sensor = QMC5883L(0x2C)

try:
    while True:
        # Получаем вектор магнитного поля
        m = sensor.get_magnet()
        
        angle_rad = math.atan2(m[0], m[1])
        
        # Конвертируем в градусы
        angle_deg = math.degrees(angle_rad)
        
        # Нормализуем в диапазон 0-360°
        if angle_deg < 0:
            angle_deg += 360
        
        # Добавляем магнитное склонение
        print(angle_deg)
        print(m[0])
        print(m[1])
        print(m[2])
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\nЗавершено")