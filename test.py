from qmc5883l import QMC5883L
import math
import time
from collections import deque

sensor = QMC5883L(0x2C)

# Буферы для сглаживания значений магнитометра (скользящее среднее)
x_buffer = deque(maxlen=10)  # Увеличил размер для лучшего сглаживания
y_buffer = deque(maxlen=10)
z_buffer = deque(maxlen=10)

def normalize_angle(angle):
    """Нормализует угол в диапазон 0-360°"""
    while angle < 0:
        angle += 360
    while angle >= 360:
        angle -= 360
    return angle

try:
    while True:
        # Получаем вектор магнитного поля
        m = sensor.get_magnet()
        
        # Добавляем в буферы для сглаживания
        x_buffer.append(m[0])
        y_buffer.append(m[1])
        z_buffer.append(m[2])
        
        # Вычисляем сглаженные значения
        x_smooth = sum(x_buffer) / len(x_buffer)
        y_smooth = sum(y_buffer) / len(y_buffer)
        z_smooth = sum(z_buffer) / len(z_buffer)
        
        # Вычисляем угол из сглаженных значений X и Y
        # atan2(y, x) дает угол от оси X против часовой стрелки
        angle_rad = math.atan2(y_smooth, x_smooth)
        angle_deg = math.degrees(angle_rad)
        angle_deg = normalize_angle(angle_deg)
        
        # Выводим данные (угол вычисляется из уже сглаженных значений, поэтому дополнительное сглаживание не нужно)
        print(f"Угол: {angle_deg:.2f}° | X: {int(x_smooth)} | Y: {int(y_smooth)} | Z: {int(z_smooth)}", end='\r', flush=True)
        
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\n\nЗавершено")