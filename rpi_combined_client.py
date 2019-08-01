import threading
from threading import Thread
import io
import socket
import struct
import time
import picamera
import serial
from time import sleep
import sys
import RPi.GPIO as GPIO
import ThunderBorg
from time import sleep


# Set server IP address & Port
host = "192.168.0.102"
port = 8000


# Thread to handle video transmission
def VideoStream():
    global command_client

    # Initialise everything
    # print("Connecting to command server")
    # command_client = socket.socket()  # Create a socket object
    # command_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # command_client.connect((host, port))  # Bind to the port
    # print("Should be connected to command server")
    # print("")

    # Start thread to handle control requests
    # Thread(target = steer).start()

    # Wait 0.5 seconds to allow video server to initialise
    sleep(0.5)

    # Set up video client
    print("Connecting to video server")
    video_socket = socket.socket()
    video_socket.connect((host, port + 1))

    # Make a file-like object out of the connection
    connection = video_socket.makefile('wb')
    print("Should be connected to video server")
    print("")
    try:
        camera = picamera.PiCamera()
        camera.resolution = (320, 240)
        # Set to true if camera is flipped vertically
        camera.vflip = True
        camera.hflip = True
        # Start a preview and let the camera warm up for 2 seconds
        # camera.start_preview()
        time.sleep(2)

        # Note the start time and construct a stream to hold image data
        # temporarily (we could write it directly to connection but in this
        # case we want to find out the size of each capture first to keep
        # our protocol simple)
        start = time.time()
        stream = io.BytesIO()
        for foo in camera.capture_continuous(stream, 'jpeg', use_video_port=True):
            # Write the length of the capture to the stream and flush to
            # ensure it actually gets sent
            connection.write(struct.pack('<L', stream.tell()))
            connection.flush()
            # Rewind the stream and send the image data over the wire
            stream.seek(0)
            connection.write(stream.read())
            # If we've been capturing for more than 30 seconds, quit
            # if time.time() - start > 30:
            #    break
            # Reset the stream for the next capture
            stream.seek(0)
            stream.truncate()
        # Write a length of zero to the stream to signal we're done
        connection.write(struct.pack('<L', 0))
    finally:
        recvCommand = "00000000"
        # ArduinoPort.write(recvCommand.encode())
        # print "Error! Connection lost!"
        connection.close()
        video_socket.close()



def CommandStream():
    port = 8005
    ip_address = "192.168.0.1"  # IP Address of PC
    control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    control_socket.bind(('0.0.0.0', port))
    print("waiting on port:", port)

    # Number the RPI IO pins using BCM
    GPIO.setmode(GPIO.BCM)
    # Set the first pin as an output
    GPIO.setup(18, GPIO.OUT)
    # GPIO.setup(1,GPIO.OUT)
    # Create a PWM instance
    sampler = GPIO.PWM(18, 50)
    sampler.start(0)

    # claw = GPIO.PWM(,50) #enter pin number
    # Need to set the board address of each Thunderborg separately to addresses e.g. 10 11


    # Board #1, address 10, two left motors, Motor1: Front, Motor2: Rear
    TB1 = ThunderBorg.ThunderBorg()
    TB1.i2cAddress = 10
    TB1.Init()

    # Board #2, address 11, two right motors, Motor1: Front, Motor2: Rear
    TB2 = ThunderBorg.ThunderBorg()
    TB2.i2cAddress = 11
    TB2.Init()

    TB3 = ThunderBorg.ThunderBorg()
    TB3.i2cAddress = 12
    TB3.Init()

    while True:
        print(TB1.GetBatteryReading())
        print(TB2.GetBatteryReading())
        print(TB3.GetBatteryReading())  # prints battery voltage

        # Receive control strings over the socket from the PC.
        data, addr = control_socket.recvfrom(1024)
        # Print the messages
        print("Message: ", data)

        # Use the data to control motors

        # Extract throttle and steer_angle from data
        throttle = int(data[0:3])
        steer_angle = int(data[3:6])
        sampler_position = int(data[6:9])
        claw_position = int(data[9:12])
        # scale throttle, steer angle, and sampler position to range [-1,1]
        # old_sampler_position = sampler_position
        scaled_sampler_position = (90 - sampler_position) / 90  # 1 is max clockise, -1 max anticlockwise
        scaled_throttle = (throttle - 90) / 90
        scaled_steer_angle = (steer_angle - 90) / 90

        claw_position_scaled = (90 - claw_position) / 90

        left_power = scaled_throttle + scaled_steer_angle
        right_power = scaled_throttle - scaled_steer_angle

        # Scale left_power and right_power so both stay in range [-1,1]

        if (left_power >= 1) or (right_power <= -1):
            left_power *= 1 / 2
            right_power *= 1 / 2

        TB1.SetMotors(left_power)
        TB2.SetMotors(right_power)

        #   if claw_position == 1:
        #      claw.ChangeDutyCycle(10)
        #  else:
        #      claw.ChangeDutyCycle(5)


        # Sampler Control Code
        # Servo is neutral at 1.5ms, >1.5 Counter-Clockwise, <1.5 Clockwise
        print(scaled_sampler_position)

        TB3.SetMotors(scaled_sampler_position)

        pulse_width = 1.5 - claw_position_scaled * 1 / 4

        duty_cycle = pulse_width * 5  # this is the simplification of D = PW/T * 100 with f=1/T = 50Hz

        sampler.ChangeDutyCycle(duty_cycle)

    control_socket.close()
    GPIO.cleanup() #Check if neccessary

Thread(target=VideoStream).start()
Thread(target=CommandStream).start()
