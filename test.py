from qmc5883l import QMC5883L
import math
import time
from collections import deque
from smbus2 import SMBus

sensor = QMC5883L(0x2C)

# Регистры для чтения данных
REG_OUT_X_LSB = 0x00
REG_OUT_Y_LSB = 0x02
REG_OUT_Z_LSB = 0x04

# Создаем прямое подключение к I2C для чтения сырых данных с правильным порядком байтов
bus = SMBus(1)  # Используем ту же шину, что и библиотека
address = 0x2C

def read_magnet_raw_correct():
    """
    Читает сырые данные магнитометра напрямую из I2C с правильным порядком байтов
    Согласно C++ библиотеке: Wire.read() | Wire.read() << 8 (LSB | MSB << 8)
    """
    # Читаем 6 байт данных начиная с REG_OUT_X_LSB
    data = bus.read_i2c_block_data(address, REG_OUT_X_LSB, 6)
    
    # Правильный порядок байтов: LSB | MSB << 8 (как в C++ библиотеке)
    x_raw = (data[0] | (data[1] << 8))
    y_raw = (data[2] | (data[3] << 8))
    z_raw = (data[4] | (data[5] << 8))
    
    # Преобразуем в знаковое 16-битное число
    if x_raw > 32767:
        x_raw -= 65536
    if y_raw > 32767:
        y_raw -= 65536
    if z_raw > 32767:
        z_raw -= 65536
    
    # Нормализуем в Гауссы (как делает библиотека, но с правильными байтами)
    # Библиотека использует: magval * max_mag / 2 ** 15
    max_mag = 8  # full_scale = True
    x = x_raw * max_mag / 2 ** 15
    y = y_raw * max_mag / 2 ** 15
    z = z_raw * max_mag / 2 ** 15
    
    return [x, y, z]

# Буферы для сглаживания значений магнитометра (скользящее среднее)
buffer_size = 20
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
        # Получаем вектор магнитного поля с правильным порядком байтов
        # Используем прямое чтение из I2C вместо библиотеки для правильной обработки байтов
        m = read_magnet_raw_correct()
        
        # Добавляем в буферы для сглаживания
        x_buffer.append(m[0])
        y_buffer.append(m[1])
        z_buffer.append(m[2])
        if (len(x_buffer) >= buffer_size):
            x_buffer=x_buffer[1:]
            y_buffer=y_buffer[1:]
            z_buffer=z_buffer[1:]

        
        # Вычисляем сглаженные значения
        x_smooth = sum(x_buffer) / len(x_buffer)
        y_smooth = sum(y_buffer) / len(y_buffer)
        z_smooth = sum(z_buffer) / len(z_buffer)
        
        # Вычисляем угол из сглаженных значений X и Y
        # Согласно C++ библиотеке QMC5883LCompass: atan2(getY(), getX())
        # В C++: float heading = atan2( getY(), getX() ) * 180.0 / PI;
        angle_rad = math.atan2(y_smooth, x_smooth)
        angle_deg = math.degrees(angle_rad)
        
        # Если нужно скорректировать угол (например, добавить или вычесть 90°)
        # раскомментируйте следующую строку:
        # angle_deg += 90  # или -90, или другое значение
        
        # Нормализуем в диапазон 0-360° (как в C++ библиотеке)
        # В C++: heading += _magneticDeclinationDegrees; return (int)heading % 360;
        if angle_deg < 0:
            angle_deg += 360
        angle_deg = angle_deg % 360
        
        # Выводим данные с информацией о значениях
        # Если углы повторяются, возможно нужно поменять местами X и Y или использовать другой вариант
        print(f"Угол: {angle_deg:.2f}° | X: {x_smooth:.3f} | Y: {y_smooth:.3f} | Z: {z_smooth:.3f}", end='\r', flush=True)
        
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\n\nЗавершено")