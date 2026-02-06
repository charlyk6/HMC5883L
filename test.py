import QMC5883L
import time

try:
    # Create a sensor object
    sensor = QMC5883L.QMC5883L()

    print("Sensor initialized. Reading data...")

    while True:
        # Read the raw magnetic field data (X, Y, Z)
        m = sensor.get_magnetometer()
        print(f"Magnetometer readings (X, Y, Z): {m[0]}, {m[1]}, {m[2]}")

        # Get the bearing (direction angle)
        bearing = sensor.get_bearing()
        print(f"Bearing: {bearing:.2f} degrees")

        # Get the temperature (if supported by the specific sensor implementation)
        # temp = sensor.read_temp()
        # print(f"Temperature: {temp:.2f} °C")

        time.sleep(0.5)

except KeyboardInterrupt:
    print("Program stopped")
except Exception as e:
    print(f"An error occurred: {e}")

