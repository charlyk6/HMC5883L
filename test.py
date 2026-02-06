from QMC5883LCompass import QMC5883LCompass
import time

# Инициализация компаса
compass = QMC5883LCompass(address=0x0D)  # Адрес по умолчанию для QMC5883L
compass.init()

# Опционально: установить магнитное склонение для вашего местоположения
# compass.setMagneticDeclination(degrees, minutes)

try:
    while True:
        # Читаем данные с компаса
        compass.read()
        
        # Получаем значения осей
        x = compass.getX()
        y = compass.getY()
        z = compass.getZ()
        
        # Получаем азимут (уже включает магнитное склонение, если установлено)
        azimuth = compass.getAzimuth()
        
        # Получаем направление
        direction = compass.getDirection()
        
        # Выводим данные, перезаписывая строку
        print(f"Азимут: {azimuth}° ({direction}) | X: {x} | Y: {y} | Z: {z}", end='\r', flush=True)
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\nЗавершено")