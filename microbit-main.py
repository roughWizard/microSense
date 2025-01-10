# Note : make sure to click "Disconnect" after flashing code ( or
# close the tab that has the MicroPython editor, otherwise serial
# transmission will drop characters)

from microbit import *
import time

class Sensor:
  def __init__(self, channel, name, mode, unit, measure):
    self.name = name # Name of sensor
    self.channel = channel # Channel : 0,1,2
    self.mode = mode # Analog or digital
    self.unit = unit # To be displayed on y axis of graph
    self.measure = measure # Measuring function


# Function to send current sensor configuration on Microbit
def send_sensor_config(sensors):
  if not isinstance(sensors, list): # Is it an array (list) of sensors or just one sensor ?
    sensors = [sensors] # We're expecting a list later, so make it a list of 1

  sensor_config = "SENSOR_CONFIG:[" # String to be sent to website as JSON formatted array

  # Go through each sensor
  for i, sensor in enumerate(sensors):
    if sensor: # Is a sensor configured ?
      sensor_config += '["{}", "{}", {}, "{}"]'.format(sensor.name, sensor.mode, sensor.channel, sensor.unit)
    else:
      sensor_config += '[]'

    # Add a comma if it's not the last sensor in the list
    if i < len(sensors) - 1:
      sensor_config += ","    

  # Terminate the string
  sensor_config += "]"

  # String has format SENSOR_CONFIG:[["photoresistor","analog","0","%"],[...]]
  uart.write("{}\n".format(sensor_config))


def measure_distance(TRIG,ECHO):
    # Trigger pulse with this sequence
    TRIG.write_digital(0)
    time.sleep_us(2)
    TRIG.write_digital(1)
    time.sleep_us(10)
    TRIG.write_digital(0)
    
    # Measure the pulse duration on ECHO pin
    while ECHO.read_digital() == 0:
        pulse_start = time.ticks_us()
    
    while ECHO.read_digital() == 1:
        pulse_end = time.ticks_us()
    
    pulse_duration = time.ticks_diff(pulse_end, pulse_start)
    
    # Calculate distance (cm): time * speed of sound in cm/us) / 2 because of return trip
    return (pulse_duration * 0.0343) / 2


# Function to send sensor data
def send_data(elapsed_time):
  global sensors

  sensor_data = ""
  # Go through each sensor
  for sensor in sensors:
    sensor_data += "," # Separate whether configured or not so they show up in right order in array
    if sensor: # Is a sensor configured ?
      sensor_data += str(sensor.measure()) # Call the read method of the sensor and add it after a comma
 
  # Prepare the string
  sensor_data = "DATA:{}{}".format(elapsed_time, sensor_data) # String to be sent to website (guaranteed a comma after time)

  # String has format DATA:[time,measure1,measure2,...]
  uart.write("{}\n".format(sensor_data))


# Function to process complete commands
def process_command(command):
  global sensors, start_time, next_time, interval, send_data_flag, ok_to_send
  
  if command.startswith("SET_INTERVAL:"): # SET_INTERVAL:1000
    try:
      requestedInterval = int(command.split(":")[1])
      if requestedInterval > 0:
        interval = requestedInterval
        uart.write("Interval set to {} ms\n".format(interval))
      else:
        raise Exception("Number incorrect\n")
          
    except ValueError:
      uart.write("Invalid interval command: {}\n".format(command))

  elif command.startswith("SET_SENSOR:"): # SET_SENSOR:photoresistor,0
    try:
      config = command.split(":", 1)[1].split(",") # Parse into array based on "," for the rightmost part of ":"
      name = config[0] # Name of sensor
      channel = int(config[1]) # 0 or 1 or internal sensor name (or more pins : it's the Microbit pin number) -- comes in as a string !
        
      if channel not in validChannels:
        raise Exception("Invalid channel") # Throw an error if incorrect channel

      # Valid sensor configurations (set mode to analog "a" or digital "d")
      validTypes = {
        "ultrasonicRanger": {
          "mode": "digital",
          "read": lambda trig, echo: lambda: measure_distance(trig,echo), # Returns measure_distance with tri and echo filled in as parameters of outer function
          "unit": "cm"
        },
        "photoresistor": {
          "mode": "analog",
          "read": lambda pin: lambda: pin.read_analog()/1023 * 100, # Return as a percentage
          "unit": "%"
        },
        "variableResistor": {
          "mode": "analog",
          "read": lambda pin: lambda: pin.read_analog()/1023 * 100, # Return as a percentage
          "unit": "%"
        },
        "internal": { # Built-in functions (must be capital because of my naming convention internalAccelx)
          "Accelx": {
            "mode": "digital", # To avoid conversion to %
            "read": lambda: lambda: accelerometer.get_x() / 1000, # Need an anonymous wrapper function to return reading/1000
            "unit": "g"
          },
          "Temp": {
            "mode": "digital", # To avoid conversion to %
            "read": lambda: lambda: temperature(),
            "unit": "°C"
          }
        }
      }

      # Validate received sensor configuration
      if name == "none": # No sensor configured on given channel, so set to none in case one there
        sensors[channel] = None
        return

      if name in validTypes:
        mode = validTypes[name]["mode"]
        unit = validTypes[name]["unit"]

        # Execute anonymous function that will return the measurement function
        if name == "ultrasonicRanger": # Special, takes two pins (assume they're next to each other)
          measure = validTypes[name]["read"](validPins[channel], validUltrasonicEchoPins[channel])
        else:
          measure = validTypes[name]["read"](validPins[channel])

      elif name.startswith("internal") and name.replace("internal","") in validTypes["internal"]:
        internalName = name.replace("internal","") # Take out the first part of the string "internal"
        mode = validTypes["internal"][internalName]["mode"]
        unit = validTypes["internal"][internalName]["unit"]
        measure = validTypes["internal"][internalName]["read"]()

      else:
        raise Exception("Invalid sensor type") # Throw an error if sensor_type doesn't match

      # Reply sensor configured
      sensors[channel] = Sensor(channel, name, mode, unit, measure)
      send_sensor_config(sensors[channel])
        
    except Exception as error:
      uart.write("Invalid sensor configuration: {} ({})\n".format(command,error))

  elif command.startswith("REMOVE_SENSOR:"): # REMOVE_SENSOR:0
    channel = command.split(":", 1)[1] # Get number (as a string) of channel to remove
    if channel in validChannels and sensors[channel]: # Channel is valid (0,1,2) and there is a sensor configured
      sensors[channel] = None
    else:
      uart.write("Invalid channel or no sensor configured on channel: {}\n".format(command))

  elif command == "SEND_DATA": 
    if [x for x in sensors if x is not None]: # Is sensor configured ? (iterates through array sensors and includes only the elements that are not None)
      send_data_flag = True
      start_time = running_time() # Start time from the running clock
      next_time = start_time # Next time to sample from the running clock
      uart.write("Send data command received\n")
    else:
      uart.write("Cannot start: sensor not configured\n")
        
  elif command == "STOP_DATA":
    send_data_flag = False
    uart.write("Stop data command received\n")

  elif command == "SEND_CONFIG": # Send current Microbit configuration
    send_sensor_config(sensors)
  
  elif command == "SEND_INTERVAL":
    uart.write("INTERVAL:{}\n".format(interval))
 
  elif command == "OK":  # Handle OK response from the webpage
    ok_to_send = True  # Set ok_to_send to True when "OK" is received
 
  else:
    uart.write("Unknown command received: {}\n".format(command))


# Default settings
interval = 1000  # Data collection interval (in milliseconds)
send_data_flag = False # Data collection active flag
ok_to_send = False  # Initially, we cannot send data until we receive "OK"

uart_buffer = "" # Buffer to accumulate incoming UART data
uart.init(baudrate=115200)

start_time = 0  # Initialize the timer start time (based on current running clock)
next_time = 0 # Elapsed time since last data sent

sensors = [None, None, None] # Array of sensor configurations for P0, P1, P2 (for now only supporting big pins)
validChannels = [0,1,2] # Channel is given as a string !
validPins = [pin0,pin1,pin2] # Pin objects for reading data
validUltrasonicEchoPins = [pin8,pin12,pin16] # For the second pin connection


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
    current_time = running_time()

    if current_time >= next_time:
      if ok_to_send: # Must have received an OK message
        send_data(current_time - start_time)
        next_time += interval # Compensate for drift
        ok_to_send = False  # Set flag to false after sending data
      else:
        send_data_flag = False # Reset send_data flag if OK message has not been received to avoid piling up data in the buffer