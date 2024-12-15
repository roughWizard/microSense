from microbit import *
import time

# Default settings
interval = 1000  # Data collection interval (in milliseconds)
send_data_flag = False # Data collection active flag
uart_buffer = ""  # Buffer to accumulate incoming UART data
start_time = 0  # Initialize the timer start time
sensors = [] # Array of sensor configurations

class Sensor:
  def __init__(self, sensor_type, channel, mode, unit, measure):
    self.sensor_type = sensor_type
    self.channel = channel
    self.mode = mode
    self.unit = unit
    self.measure = measure

# Function to send sensor data
def send_data():
  global sensors, start_time

  elapsed_time = running_time() - start_time  # Time since SEND_DATA command
  sensor_data = "DATA:[{},".format(elapsed_time) # String to be sent to website as JSON formatted array

  # Go through each sensor
  for sensor in sensors:
    sensor_value = sensor.measure()
    if sensor_mode == "analog": # Convert ADC value (0-1023) to a percentage if analog
      sensor_value = sensor_value/1023 * 100

    sensor_data += str(sensor_value) + "," # Call the read method of the sensor

  # Terminate the string
  sensor_data += "]"

  # String has format DATA:[time,measure1,measure2,...]  
  uart.write("{}\n".format(sensor_data))





# Function to process complete commands
def process_command(command):
  global sensor_read, start_time, interval, send_data_flag
  global sensor_type,sensor_channel,sensor_mode,

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
          "mode": "analog",
          "unit": "%"
        },
        "variableResistor": {
          "mode": "analog",
          "unit": "%"
        },
        "internal": { # Built-in functions (must be capital because of my naming convention internalAccelx)
          "Accelx": {
            "read": lambda: accelerometer.get_x() / 1000, # Need an anonymous wrapper function to return reading/1000
            "unit": "g"
          },
          "Temp": {
            "read": temperature,
            "unit": "°C"
          }
        }
      }
      validChannels = ["0","1"] # Channel is given as a string !

      # Validate received sensor configuration
      if sensor_type in validTypes and sensor_channel in validChannels:
        # Gets object pin0, pin1, etc.
        pin = globals()["pin" + sensor_channel] # globals() holds all global variables (including pin0, pin1, etc.)

        # Uses read_analog() or read_digital() on pin but without () -- that's done when actually reading data
        sensor_mode = validTypes[sensor_type]["mode"]
        sensor_read = pin.read_analog if sensor_mode == "analog" else pin.read_digital
        sensor_unit = validTypes[sensor_type]["unit"]

      elif sensor_type.startswith("internal") and sensor_type.replace("internal","") in validTypes["internal"]:
        sensor_mode = sensor_type.replace("internal","")
        sensor_read = validTypes["internal"][sensor_mode]["read"] # Take out the first part of the string "internal"
        sensor_channel = None # To be displayed below
        sensor_unit = validTypes["internal"][sensor_mode]["unit"]
      
      else:
        sensor_read = None # Make sure any previous configs do not stick on error
        customError = ""
        raise Exception("did not pass if tests " + customError) # Throw an error if sensor_type doesn't match

      # Reply sensor configured
      uart.write("SENSOR_CONFIG:type:{}, mode:{}, channel:{}, unit:{}\n".format(sensor_type, sensor_mode, sensor_channel,sensor_unit))
        
    except Exception as error:
      uart.write("Invalid sensor configuration: {} ({})\n".format(command,error))

  elif command == "SEND_DATA":
    if sensor_read: # Is sensor configured ?
        send_data_flag = True
        start_time = running_time()  # Start timer
        uart.write("Send data command received\n")
    else:
        uart.write("Cannot start: sensor not configured\n")
        
  elif command == "STOP_DATA":
    send_data_flag = False
    uart.write("Stop data command received\n")

  elif command == "SEND_CONFIG": # Send current Microbit configuration
    uart.write("")
      
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
    time.sleep_ms(interval)
