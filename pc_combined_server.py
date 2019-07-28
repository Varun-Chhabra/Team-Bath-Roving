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
import pygame
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
    # Once command server is connected, set up video server and wait for a connect
    print('Waiting for Video Stream')

    # Create socket
    video_server_soc = socket.socket()
    video_server_soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    video_server_soc.bind((host, 8003))
    video_server_soc.listen(0)

    # Accept a single connection and make a file-like object out of it
    video_client = video_server_soc.accept()[0].makefile('rb')
    print("Video client connected!")

    # Return clients
    return video_client




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
    video_client = setup_servers()


    # Initialise start time
    start_time = time.time()

    # Start receiving images

    while True:
        # Load image from stream
        image_time = time.time()
        image = (load_image(video_client))
        # draw_image = Image.fromarray(image)
        # draw_image = Image.fromarray(image)
        cv2.imshow('feed', cv2.resize(image,(640,480)))
        cv2.waitKey(1)


def CommandStream():
    axis_steer = 2
    axis_throttle = 0
    axis_sampler = 3  # find axis
    button_claw = 4
    claw_deployed = 0
    claw_transmit = "000"

    forwards_moved = 0
    reverse_moved = 0
    reverse_engaged = 0
    throttle = "090"

    # create dgram udp socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        t = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error:
        print('Failed to create socket')
        sys.exit()

    ip_address = "192.168.0.100"  # Address of RPi
    port = 8005  # port value must be the same on both scripts

    # ip_address_zero = ""
    # port_zero =

    size = [500, 700]
    screen = pygame.display.set_mode(size)

    pygame.init()
    pygame.joystick.init()
    j_count = pygame.joystick.get_count()
    print(j_count)
    gamepad = pygame.joystick.Joystick(0)
    gamepad.init()

    while True:
        pygame.event.pump()

        steer_angle = str(int(round(gamepad.get_axis(axis_steer) * 90 + 90, 0))).zfill(3)
        sampler_value = str(int(round(gamepad.get_axis(axis_sampler) * 90 + 90, 0))).zfill(3)
        claw_bool = str(int(round(gamepad.get_axis(button_claw) * 90 + 90, 0))).zfill(3)
        if int(claw_bool) < 40:
            claw_deployed = 0
            claw_transmit = "000"

        if int(claw_bool) > 140:
            claw_deployed = 1
            claw_transmit = "180"

        """
        if gamepad.get_axis(axis_throttle) < 0:
            forwards_moved = 1
        if gamepad.get_axis(axis_throttle) > 0:
            reverse_moved = 1
        if forwards_moved == 1:
            throttle = str(90 - int(round(gamepad.get_axis(axis_throttle)*45 + 45, 0))).zfill(3)
        if reverse_moved == 1 and gamepad.get_axis(axis_throttle) != -1:
            throttle = str(90 + int(round(gamepad.get_axis(axis_throttle)*45 + 45, 0))).zfill(3)
        """
        throttle = str(90 + int(round(gamepad.get_axis(axis_throttle) * 90, 0))).zfill(3)
        transmission_string = throttle + steer_angle + sampler_value + claw_transmit  # + sampler_value

        # transmission_string_zero = sampler_value

        print(transmission_string)
        #  print(transmission_string_zero)
        s.sendto(transmission_string.encode(), (ip_address, port))
        #   t.sendto(transmission_string_zero.encode(),ip_address_zero,port_zero)
        sleep(0.1)

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
image = 0



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
Thread(target=CommandStream).start()
