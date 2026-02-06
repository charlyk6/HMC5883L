import py_qmc5883l
import time

# Инициализация компаса
sensor = py_qmc5883l.QMC5883L()

# Опционально: установить магнитное склонение для вашего местоположения
# sensor.declination = 10.02  # пример: 10 градусов 1.2 минуты

try:
    while True:
        # Получаем вектор магнитного поля [X, Y, Z]
        m = sensor.get_magnet()
        
        # Получаем азимут в градусах (уже включает магнитное склонение, если установлено)
        bearing = sensor.get_bearing()
        
        # Выводим данные, перезаписывая строку
        print(f"Азимут: {bearing:.2f}° | X: {m[0]} | Y: {m[1]} | Z: {m[2]}", end='\r', flush=True)
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\nЗавершено")