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
        print(f"Угол: {angle_deg:.2f}° | X: {m[0]} | Y: {m[1]} | Z: {m[2]}", end='\r', flush=True)
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\nЗавершено")