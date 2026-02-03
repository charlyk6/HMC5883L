from qmc5883l import QMC5883L
import math
import time

sensor = QMC5883L(0x2C)

def normalize_raw_value(raw_value, max_range=32768):
    """
    Преобразует сырое 16-битное значение с дополнением до двух
    в нормализованное значение в микроТеслах
    
    raw_value: сырое значение от датчика
    max_range: максимальное значение (32768 для 16-бит)
    """
    # Если значение отрицательное (старший бит = 1)
    if raw_value >= 0x8000:  # 32768 в десятичной
        raw_value -= 0x10000  # 65536 в десятичной
    
    # Масштабируем к микроТеслам
    # Для QMC5883L при диапазоне ±8 Гаусс:
    # Чувствительность = 0.48828125 мГаусс/LSB
    # 1 Гаусс = 100,000 микроТесла
    # Поэтому: 0.48828125 * 0.1 = 0.048828125 μT/LSB
    scale_factor = 0.048828125  # μT на единицу сырого значения
    
    return raw_value * scale_factor

print("Направление от магнитного севера:")
print("Повращайте датчик на 360 градусов для калибровки...")

# Собираем калибровочные данные
calibration_samples = []
for i in range(100):
    m = sensor.get_magnet()
    calibration_samples.append((m[0], m[1]))
    time.sleep(0.01)

# Находим min/max для калибровки
x_vals = [s[0] for s in calibration_samples]
y_vals = [s[1] for s in calibration_samples]

x_min, x_max = min(x_vals), max(x_vals)
y_min, y_max = min(y_vals), max(y_vals)

# Смещение (offset) и масштаб (scale) для калибровки
x_offset = (x_max + x_min) / 2
y_offset = (y_max + y_min) / 2
x_scale = (x_max - x_min) / 2
y_scale = (y_max - y_min) / 2

# Используем средний масштаб для обоих осей
avg_scale = (x_scale + y_scale) / 2

print(f"Калибровка: X offset={x_offset:.1f}, Y offset={y_offset:.1f}, scale={avg_scale:.1f}")

# Магнитное склонение для Москвы (~10°)
MOSCOW_DECLINATION = 10.0

try:
    while True:
        # Получаем вектор магнитного поля
        m = sensor.get_magnet()
        
        # Калибруем значения
        x_calibrated = (m[0] - x_offset) / avg_scale
        y_calibrated = (m[1] - y_offset) / avg_scale
        
        # Вычисляем азимут
        # atan2(y, x) дает угол от оси X (Восток)
        # Но нам нужен угол от севера (оси Y)
        angle_rad = math.atan2(x_calibrated, y_calibrated)
        
        # Конвертируем в градусы
        angle_deg = math.degrees(angle_rad)
        
        # Нормализуем в диапазон 0-360°
        if angle_deg < 0:
            angle_deg += 360
        
        # Добавляем магнитное склонение
        true_heading = (angle_deg + MOSCOW_DECLINATION) % 360
        
        # Определяем сторону света
        directions = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
        dir_idx = int((true_heading + 22.5) / 45) % 8
        
        # Выводим информацию
        print(f"\r"
              f"Азимут: {true_heading:6.1f}° {directions[dir_idx]:3} | "
              f"X:{m[0]:8.1f}→{x_calibrated:5.2f} | "
              f"Y:{m[1]:8.1f}→{y_calibrated:5.2f} | "
              f"Z:{m[2]:8.1f} μT", end="")
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\nЗавершено")