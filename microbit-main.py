from microbit import *
import time

# Default settings
interval = 1000  # Data collection interval (in milliseconds)
send_data_flag = False # Data collection active flag
uart_buffer = ""  # Buffer to accumulate incoming UART data
start_time = 0  # Initialize the timer start time

# Function to send sensor data
def send_data():
  global sensor_read

  if sensor_read:
    sensor_value = sensor_read()
    elapsed_time = running_time() - start_time  # Time since SEND_DATA command
    uart.write("data:{},{}\n".format(elapsed_time,sensor_value)) # data:2000,25

# Function to process complete commands
def process_command(command):
  global sensor_read,interval, send_data_flag

  if command.startswith("SET_INTERVAL:"): # SET_INTERVAL:1000
    try:
      interval = int(command.split(":")[1])
      uart.write("Interval set to {} ms\n".format(interval))
    except ValueError:
      uart.write("Invalid interval value: {}\n".format(command))

  elif command.startswith("SET_SENSOR:"): # SET_SENSOR:photoresistor,0
    try:
      sensor_config = command.split(":", 1)[1].split(",") # Parse into array based on "," the rightmost part of :
      sensor_type = sensor_config[0] # Name of sensor
      sensor_channel = sensor_config[1] # 0 or 1 or internal sensor name (or more pins : it's the Microbit pin number) -- comes in as a string !

      # Valid sensor configurations (set mode to analog "a" or digital "d")
      validTypes = {
        "photoresistor": {
          "mode": "analog"
        },
        "internal": {
          "accelx": accelerometer.get_x
        }
      }  
      validChannels = ["0","1"] # Channel is given as a string !
      
      if sensor_type in validTypes and sensor_channel in validChannels:
        # Gets object pin0, pin1, etc.
        pin = globals()["pin" + sensor_channel] # globals() holds all global variables (including pin0, pin1, etc.)

        # Uses read_analog() or read_digital() on pin but without () -- that's done when actually reading data
        sensor_mode = validTypes[sensor_type].mode
        #sensor_read = getattr(pin, "read_" + sensor_mode) -- ancienne ligne, pas très claire (au lieu de ci-dessous)
        sensor_read = pin.read_analog if sensor_mode == "analog" else pin.read_digital
          
      elif sensor_type == "internal" and sensor_channel in validTypes["internal"]:
        # sensor_channel actually holds the name of the sensor in this case
        sensor_mode = sensor_channel
        sensor_read = validTypes["internal"][sensor_channel]
        sensor_channel = None # To be displayed below (instead of repeating sensor name)
      
      else:
        raise # Throw an error if sensor_type doesn't match

      # Reply sensor configured
      uart.write("Sensor set to type:{}, mode:{}, channel:{}\n".format(sensor_type, sensor_mode, sensor_channel))
    except Exception:
      uart.write("Invalid sensor configuration: {}\n".format(command))

  elif command == "SEND_DATA":
    send_data_flag = True
    uart.write("Send data command received\n")

  elif command == "STOP_DATA":
    send_data_flag = False
    uart.write("Stop data command received\n")

  else:
    uart.write("Unknown command received: {}\n".format(command))

# Main loop
while True:
  if uart.any():
    # Read available data and add to the buffer
    uart_buffer += uart.read().decode('utf-8')
    
    # Process complete commands (delimited by \n)
    while '\n' in uart_buffer:
      command, uart_buffer = uart_buffer.split('\n', 1)  # Split off one command
      command = command.strip()  # Clean the command
      if command:
        process_command(command)  # Process the complete command

  # If SEND_DATA is active, send data at the specified interval
  if send_data_flag:
    send_data()
    start_time = running_time()  # Start timer
    time.sleep_ms(interval)
