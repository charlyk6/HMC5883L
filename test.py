from qmc5883l import QMC5883L
import math
import time
from collections import deque

sensor = QMC5883L(0x2C)

# Буферы для сглаживания (скользящее среднее)
angle_buffer = deque(maxlen=10)  # Храним последние 10 значений угла
x_buffer = deque(maxlen=5)
y_buffer = deque(maxlen=5)
z_buffer = deque(maxlen=5)

def normalize_angle(angle):
    """Нормализует угол в диапазон 0-360°"""
    while angle < 0:
        angle += 360
    while angle >= 360:
        angle -= 360
    return angle

def smooth_angle(new_angle, buffer):
    """Сглаживает угол с учетом циклической природы (0° и 360° рядом)"""
    if len(buffer) == 0:
        buffer.append(new_angle)
        return new_angle
    
    # Находим ближайшее значение с учетом циклической природы
    last_angle = buffer[-1]
    diff = new_angle - last_angle
    
    # Корректируем разницу, если она больше 180° (переход через 0/360)
    if diff > 180:
        diff -= 360
    elif diff < -180:
        diff += 360
    
    adjusted_angle = last_angle + diff
    adjusted_angle = normalize_angle(adjusted_angle)
    buffer.append(adjusted_angle)
    
    # Вычисляем среднее значение
    angles = list(buffer)
    # Учитываем циклическую природу при вычислении среднего
    sin_sum = sum(math.sin(math.radians(a)) for a in angles)
    cos_sum = sum(math.cos(math.radians(a)) for a in angles)
    avg_angle = math.degrees(math.atan2(sin_sum / len(angles), cos_sum / len(angles)))
    return normalize_angle(avg_angle)

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
        
        # Вычисляем угол
        angle_rad = math.atan2(x_smooth, y_smooth)
        angle_deg = math.degrees(angle_rad)
        angle_deg = normalize_angle(angle_deg)
        
        # Сглаживаем угол
        angle_smooth = smooth_angle(angle_deg, angle_buffer)
        
        # Выводим данные
        print(f"Угол: {angle_smooth:.2f}° | X: {int(x_smooth)} | Y: {int(y_smooth)} | Z: {int(z_smooth)}", end='\r', flush=True)
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\nЗавершено")