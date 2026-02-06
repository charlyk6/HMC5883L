import py_qmc5883l
import time
import logging

# Отключаем предупреждения от библиотеки py_qmc5883l
logging.basicConfig(level=logging.ERROR)

# Инициализация компаса с указанием I2C адреса 0x2C и диапазона 8 Гаусс
sensor = py_qmc5883l.QMC5883L(address=0x2C, output_range=py_qmc5883l.RNG_8G)

# Опционально: установить магнитное склонение для вашего местоположения
# sensor.declination = 10.02  # пример: 10 градусов 1.2 минуты

try:
    while True:
        # Получаем вектор магнитного поля [X, Y, Z] (используем get_magnet_raw для получения всех трёх значений)
        m = sensor.get_magnet_raw()
        
        # Получаем азимут в градусах (уже включает магнитное склонение, если установлено)
        bearing = sensor.get_bearing()
        
        # Выводим данные, перезаписывая строку
        print(f"Азимут: {bearing:.2f}° | X: {m[0]} | Y: {m[1]} | Z: {m[2]}", end='\r', flush=True)
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\nЗавершено")