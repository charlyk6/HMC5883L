"""
QMC5883LCompass.py
Python библиотека для использования чипа QMC5883L в качестве компаса.
Основано на библиотеке от mprograms: https://github.com/mprograms/QMC5883LCompass

Поддерживает:
- Получение значений осей XYZ
- Вычисление азимута
- Получение направления по 16 точкам (0-15)
- Получение названий направлений (N, NNE, NE, и т.д.)
- Сглаживание показаний XYZ через скользящее усреднение
- Опциональные режимы чипа
"""

import math
import smbus2

# Режимы работы
MODE_STANDBY = 0x00
MODE_CONTINUOUS = 0x01

# Частота вывода данных (ODR)
ODR_10HZ = 0x00
ODR_50HZ = 0x04
ODR_100HZ = 0x08
ODR_200HZ = 0x0C

# Полный масштаб (RNG)
RNG_2G = 0x00
RNG_8G = 0x10

# Коэффициент передискретизации (OSR)
OSR_512 = 0x00
OSR_256 = 0x40
OSR_128 = 0x80
OSR_64 = 0xC0

# Направления компаса
BEARINGS = [
    ['N', ' ', ' '],
    ['N', 'N', 'E'],
    ['N', 'E', ' '],
    ['E', 'N', 'E'],
    ['E', ' ', ' '],
    ['E', 'S', 'E'],
    ['S', 'E', ' '],
    ['S', 'S', 'E'],
    ['S', ' ', ' '],
    ['S', 'S', 'W'],
    ['S', 'W', ' '],
    ['W', 'S', 'W'],
    ['W', ' ', ' '],
    ['W', 'N', 'W'],
    ['N', 'W', ' '],
    ['N', 'N', 'W']
]


class QMC5883LCompass:
    def __init__(self, address=0x0D, bus=1):
        """
        Инициализация компаса QMC5883L
        
        Args:
            address: I2C адрес чипа (по умолчанию 0x0D)
            bus: Номер I2C шины (по умолчанию 1 для Raspberry Pi)
        """
        self._ADDR = address
        self._bus = smbus2.SMBus(bus)
        
        # Данные калибровки
        self._offset = [0.0, 0.0, 0.0]
        self._scale = [1.0, 1.0, 1.0]
        
        # Магнитное склонение
        self._magneticDeclinationDegrees = 0.0
        
        # Сглаживание
        self._smoothUse = False
        self._smoothSteps = 0
        self._smoothAdvanced = False
        self._vHistory = []
        self._vTotals = [0.0, 0.0, 0.0]
        self._vScan = 0
        self._vSmooth = [0.0, 0.0, 0.0]
        
        # Сырые и откалиброванные данные
        self._vRaw = [0, 0, 0]
        self._vCalibrated = [0.0, 0.0, 0.0]
        
    def init(self):
        """Инициализация чипа - должен быть вызван перед использованием"""
        self._writeReg(0x0B, 0x01)
        self.setMode(MODE_CONTINUOUS, ODR_200HZ, RNG_8G, OSR_512)
    
    def setADDR(self, address):
        """Установить I2C адрес чипа"""
        self._ADDR = address
    
    def _writeReg(self, reg, value):
        """Записать значение в регистр чипа"""
        self._bus.write_byte_data(self._ADDR, reg, value)
    
    def setMode(self, mode, odr, rng, osr):
        """Установить режим работы чипа"""
        self._writeReg(0x09, mode | odr | rng | osr)
    
    def setMagneticDeclination(self, degrees, minutes=0):
        """
        Установить магнитное склонение для точных градусов
        
        Args:
            degrees: Градусы магнитного склонения
            minutes: Минуты магнитного склонения (опционально)
        """
        self._magneticDeclinationDegrees = degrees + minutes / 60.0
    
    def setReset(self):
        """Сбросить чип"""
        self._writeReg(0x0A, 0x80)
    
    def setSmoothing(self, steps, advanced=False):
        """
        Включить сглаживание показаний
        
        Args:
            steps: Количество шагов для усреднения (максимум 10)
            advanced: Использовать продвинутое сглаживание (исключает min/max)
        """
        self._smoothUse = True
        self._smoothSteps = min(steps, 10)
        self._smoothAdvanced = advanced
        self._vHistory = [[0.0, 0.0, 0.0] for _ in range(self._smoothSteps)]
        self._vTotals = [0.0, 0.0, 0.0]
        self._vScan = 0
    
    def calibrate(self, duration=10):
        """
        Калибровка компаса
        
        Args:
            duration: Длительность калибровки в секундах (по умолчанию 10)
        """
        import time
        
        self.clearCalibration()
        calibrationData = [[65000, -65000], [65000, -65000], [65000, -65000]]
        
        self.read()
        x = calibrationData[0][0] = calibrationData[0][1] = self.getX()
        y = calibrationData[1][0] = calibrationData[1][1] = self.getY()
        z = calibrationData[2][0] = calibrationData[2][1] = self.getZ()
        
        startTime = time.time()
        
        while (time.time() - startTime) < duration:
            self.read()
            
            x = self.getX()
            y = self.getY()
            z = self.getZ()
            
            if x < calibrationData[0][0]:
                calibrationData[0][0] = x
            if x > calibrationData[0][1]:
                calibrationData[0][1] = x
            
            if y < calibrationData[1][0]:
                calibrationData[1][0] = y
            if y > calibrationData[1][1]:
                calibrationData[1][1] = y
            
            if z < calibrationData[2][0]:
                calibrationData[2][0] = z
            if z > calibrationData[2][1]:
                calibrationData[2][1] = z
        
        self.setCalibration(
            calibrationData[0][0], calibrationData[0][1],
            calibrationData[1][0], calibrationData[1][1],
            calibrationData[2][0], calibrationData[2][1]
        )
    
    def setCalibration(self, x_min, x_max, y_min, y_max, z_min, z_max):
        """
        Установить значения калибровки для более точных показаний
        
        Args:
            x_min, x_max: Минимальное и максимальное значения по оси X
            y_min, y_max: Минимальное и максимальное значения по оси Y
            z_min, z_max: Минимальное и максимальное значения по оси Z
        """
        self.setCalibrationOffsets(
            (x_min + x_max) / 2.0,
            (y_min + y_max) / 2.0,
            (z_min + z_max) / 2.0
        )
        
        x_avg_delta = (x_max - x_min) / 2.0
        y_avg_delta = (y_max - y_min) / 2.0
        z_avg_delta = (z_max - z_min) / 2.0
        
        avg_delta = (x_avg_delta + y_avg_delta + z_avg_delta) / 3.0
        
        self.setCalibrationScales(
            avg_delta / x_avg_delta if x_avg_delta != 0 else 1.0,
            avg_delta / y_avg_delta if y_avg_delta != 0 else 1.0,
            avg_delta / z_avg_delta if z_avg_delta != 0 else 1.0
        )
    
    def setCalibrationOffsets(self, x_offset, y_offset, z_offset):
        """Установить смещения калибровки"""
        self._offset[0] = x_offset
        self._offset[1] = y_offset
        self._offset[2] = z_offset
    
    def setCalibrationScales(self, x_scale, y_scale, z_scale):
        """Установить масштабы калибровки"""
        self._scale[0] = x_scale
        self._scale[1] = y_scale
        self._scale[2] = z_scale
    
    def getCalibrationOffset(self, index):
        """Получить смещение калибровки для указанной оси (0=X, 1=Y, 2=Z)"""
        return self._offset[index]
    
    def getCalibrationScale(self, index):
        """Получить масштаб калибровки для указанной оси (0=X, 1=Y, 2=Z)"""
        return self._scale[index]
    
    def clearCalibration(self):
        """Очистить калибровку"""
        self.setCalibrationOffsets(0.0, 0.0, 0.0)
        self.setCalibrationScales(1.0, 1.0, 1.0)
    
    def read(self):
        """Прочитать значения осей XYZ и сохранить их в массиве"""
        try:
            # Читаем 6 байт данных (по 2 байта на каждую ось)
            data = self._bus.read_i2c_block_data(self._ADDR, 0x00, 6)
            
            # Объединяем байты в 16-битные значения (little-endian)
            self._vRaw[0] = self._int16((data[1] << 8) | data[0])
            self._vRaw[1] = self._int16((data[3] << 8) | data[2])
            self._vRaw[2] = self._int16((data[5] << 8) | data[4])
            
            self._applyCalibration()
            
            if self._smoothUse:
                self._smoothing()
        except Exception as e:
            print(f"Ошибка чтения: {e}")
    
    def _int16(self, value):
        """Преобразовать значение в знаковое 16-битное число"""
        return value if value < 32768 else value - 65536
    
    def _applyCalibration(self):
        """Применить калибровку к сырым данным"""
        self._vCalibrated[0] = (self._vRaw[0] - self._offset[0]) * self._scale[0]
        self._vCalibrated[1] = (self._vRaw[1] - self._offset[1]) * self._scale[1]
        self._vCalibrated[2] = (self._vRaw[2] - self._offset[2]) * self._scale[2]
    
    def _smoothing(self):
        """Сглаживание выходных данных для осей XYZ"""
        if self._vScan > self._smoothSteps - 1:
            self._vScan = 0
        
        for i in range(3):
            if self._vTotals[i] != 0:
                self._vTotals[i] = self._vTotals[i] - self._vHistory[self._vScan][i]
            
            self._vHistory[self._vScan][i] = self._vCalibrated[i]
            self._vTotals[i] = self._vTotals[i] + self._vHistory[self._vScan][i]
            
            if self._smoothAdvanced:
                max_idx = 0
                for j in range(self._smoothSteps):
                    if self._vHistory[j][i] > self._vHistory[max_idx][i]:
                        max_idx = j
                
                min_idx = 0
                for k in range(self._smoothSteps):
                    if self._vHistory[k][i] < self._vHistory[min_idx][i]:
                        min_idx = k
                
                self._vSmooth[i] = (self._vTotals[i] - (self._vHistory[max_idx][i] + self._vHistory[min_idx][i])) / (self._smoothSteps - 2) if self._smoothSteps > 2 else self._vTotals[i] / self._smoothSteps
            else:
                self._vSmooth[i] = self._vTotals[i] / self._smoothSteps
        
        self._vScan += 1
    
    def getX(self):
        """Получить значение оси X"""
        return self._get(0)
    
    def getY(self):
        """Получить значение оси Y"""
        return self._get(1)
    
    def getZ(self):
        """Получить значение оси Z"""
        return self._get(2)
    
    def _get(self, index):
        """Получить сглаженные, откалиброванные или сырые данные с указанной оси"""
        if self._smoothUse:
            return int(self._vSmooth[index])
        return int(self._vCalibrated[index])
    
    def getAzimuth(self):
        """
        Вычислить азимут (в градусах)
        Значение корректируется с учетом магнитного склонения, если оно определено
        
        Returns:
            int: Азимут в градусах (0-359)
        """
        heading = math.atan2(self.getY(), self.getX()) * 180.0 / math.pi
        heading += self._magneticDeclinationDegrees
        
        # Нормализация в диапазон 0-360
        heading = heading % 360
        if heading < 0:
            heading += 360
        
        return int(heading)
    
    def getBearing(self, azimuth=None):
        """
        Разделить круг на 360 градусов на 16 равных частей и вернуть значение 0-15
        в зависимости от того, куда указывает азимут
        
        Args:
            azimuth: Азимут в градусах (если None, вычисляется автоматически)
        
        Returns:
            byte: Направление подшипника (0-15)
        """
        if azimuth is None:
            azimuth = self.getAzimuth()
        
        a = azimuth / 22.5 if azimuth > -0.5 else (azimuth + 360) / 22.5
        r = a - int(a)
        sexdec = math.ceil(a) if r >= 0.5 else math.floor(a)
        return int(sexdec) % 16
    
    def getDirection(self, azimuth=None):
        """
        Получить текстовое представление направления на основе азимута
        
        Args:
            azimuth: Азимут в градусах (если None, вычисляется автоматически)
        
        Returns:
            str: Строка направления (например, "N", "NNE", "NE")
        """
        if azimuth is None:
            azimuth = self.getAzimuth()
        
        d = self.getBearing(azimuth)
        return ''.join(BEARINGS[d]).strip()
    
    def get_magnet(self):
        """
        Получить вектор магнитного поля (совместимость с предыдущим API)
        
        Returns:
            list: [X, Y, Z] значения магнитного поля
        """
        self.read()
        return [self.getX(), self.getY(), self.getZ()]
