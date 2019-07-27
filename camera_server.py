# Programmed by Uvindu J Wijesinghe (2017)
import socket
import pygame
from threading import Thread
from numpy import array
import cv2
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import io
import struct
from time import sleep
import time
import scipy.misc
import sys

# Gamepad Key Mapping:
# Start - Toggle between manual and autonomous mode
# Right trigger - Forwards throttle
# Left trigger - Reverse throttle
# Left thumbstick - Steering input (needs to be centered properly for autonomous mode to activate)
# A - Toggle capturing images to disk
# B - Quits the script
# X - Decrement speed of car when in autonomous mode
# Y - Increment speed of car when in autonomous mode
#
# Note: If car is in autonomous mode, it will revert to manual mode if gamepad
#       is also giving driving commands. It will revert back to autonomous
#       mode once the gamepad input stops.


# User configurable options
# Display related:
disable_display_thread = 0      # Set to 1 to disable display thread - includes sign recognition and steering wheel
disable_camera_display = 0      # Set to 1 to disable camera output on screen
disable_steering_display = 0    # Set to 1 to disable animated steering wheel display
display_scale = 2               # Scale factor for displayed image. Set to 1 for original size.

# Object recognition options:
disable_sign_recognition = 0    # Set to 1 to disable all sign recognition (overides settings below)
disable_stop_sign = 0           # Set to 1 to disable stop sign recognition
disable_traffic_light = 1       # Set to 1 to disable traffic light recognition
disable_fuel_sign = 1           # Set to 1 to disable fuel sign recognition
disable_no_entry_sign = 1       # Set to 1 to disable No Entry sign recognition
disable_car_stopping = 0        # Don't stop the car even if a stop sign or traffic light is detected
stop_activate_width = 50        # Width of the stop sign detected above which the car should stop - bigger = closer
traffic_activate_height = 90    # Height of the traffic light detected above which the car should stop - bigger = closer
print_stop_sign_width = 1       # Set to 1 to print the width of detected stop sign in terminal
print_traffic_light_height = 0  # Set to 1 to print the height of detected traffic light red light in terminal

# Start conditions:
autonomous_enabled = 1          # Set to 1 to start in autonomous mode
pause_capture = 1               # Set to 1 to start with image capturing paused
set_speed = 0                   # Initial speed for autonomous mode

# Image capturing options:
disable_capture = 0             # Images aren't captured even if button on gamepad is pressed to unpause capture
image_num = 0                   # Starting number for captured image file name

# Other options:
speed_change_step = 10          # How much to change the vehicle speed by when X or Y are pressed - for autonomous mode
transmission_interval = 0.00    # How long to wait between commands transmitted (in seconds) - if buffer fills too fast


# Load a frame from the client Raspberry Pi to process
def load_image(video_client):

    len_stream_image = 0
    stream_image = 0

    # Repeat until a valid image has been received from the client (ie no errors)
    while len_stream_image != 230400:
        # Read the length of the image as a 32-bit unsigned int. If the
        # length is zero, quit the loop
        image_len = struct.unpack('<L', video_client.read(struct.calcsize('<L')))[0]
        if not image_len:
            print("Break as image length is null")
            return 0
        # Construct a stream to hold the image data and read the image
        # data from the connection
        image_stream = io.BytesIO()
        image_stream.write(video_client.read(image_len))
        # Rewind the stream, open it as an image with PIL
        image_stream.seek(0)
        stream_image = Image.open(image_stream)
        # Convert image to numpy array
        stream_image = array(stream_image)

        # Check to see if full image has been loaded - this prevents errors due to images lost over network
        len_stream_image = stream_image.size
        if len_stream_image != 230400:
            # The full 320x240 image has not been received
            print("Image acquisition error. Retrying...")

    # Convert to RGB from BRG
    stream_image = stream_image[:, :, ::-1]

    return stream_image


# Set up the command and video server to allow car client to connect
def setup_servers():

    # Set up command server and wait for a connect
    print('Waiting for Command Client')
    command_server_soc = socket.socket()  # Create a socket object
    command_server_soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    command_server_soc.bind((host, port))  # Bind to the port

    command_server_soc.listen(0)  # Wait for client connection
    # Wait for client to connect
    command_client, addr = command_server_soc.accept()

    print("Command client connected!")

    # Once command server is connected, set up video server and wait for a connect
    print('Waiting for Video Stream')

    # Create socket
    video_server_soc = socket.socket()
    video_server_soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    video_server_soc.bind((host, port + 1))
    video_server_soc.listen(0)

    # Accept a single connection and make a file-like object out of it
    video_client = video_server_soc.accept()[0].makefile('rb')
    print("Video client connected!")

    # Return clients
    return command_client, video_client




# Thread to receive video feed - Thread 1
def video_stream():
    global message
    global drive_values
    global send_commands
    global control_message
    global set_speed
    global autonomous_enabled
    global pause_capture
    global image_num
    global disable_capture
    global speed_change_step
    global transmission_interval
    global pause_capture
    global manual_control
    global image
    global stop_condition

    terminate_program = 0  # Flag to indicate script should be stopped
    total_frame = 0        # Count of total number of frames processed - used for frame rates
    last_send_time = 0     # Time since previous command was sent - used to control transmission rate
    show_started = 0       # Flag to indicate whether the show_images thread has started

    # Setup servers
    command_client, video_client = setup_servers()


    # Initialise start time
    start_time = time.time()

    # Start receiving images

    while True:
        # Load image from stream
        image_time = time.time()
        image = (load_image(video_client))
        # draw_image = Image.fromarray(image)
        # draw_image = Image.fromarray(image)
        cv2.imshow('feed', image)
        cv2.waitKey(1)



# Initiation
print("Data Collection Server Script Initiated")

# Find interface names using ifconfig (left hand column)
# On my computer:
# Ethernet adapter was named "enp4s0"
# Wireless adapter was named "wlp3s0"

# Get PC IP Address
# ni.ifaddresses('wlp3s0')
# wifi = ni.ifaddresses('wlp3s0')[2][0]['addr']
# ethernet = ni.ifaddresses('enp4s0')[2][0]['addr']

# Open port range on all network interfaces
host = "0.0.0.0"
port = 8000

# Set up XBox controller
# pygame.init()
# pygame.joystick.init()
# gamepad = pygame.joystick.Joystick(0)
# gamepad.init()

# Initialise variables
message = "00000000"
control_message = "00000000"
drive_values = [0, 0, 0, 0]
send_commands = 1
smoothed_angle = 1
wheel = cv2.imread('steering_wheel_image.jpg', 0)
# wheel_rows, wheel_cols = wheel.shape
manual_control = 0
image = 0
stop_condition = 0


# Indicate script initiation and print server details
print("")
print("Server details:")
# print("WiFi - ", wifi)
# print("Ethernet - ", ethernet)
print("Command Port - ", port)
print("Video Port - ", port + 1)
print("")

# Start thread (Thread 1)
Thread(target=video_stream).start()
