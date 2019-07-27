# rpi_rover_control_client.py
# Created: 2017.12.03
# Uvindu Wijesinghe and Varun Chhabra
#
# Note: Some code adapted from Project Intelligent Car
#
# Description:
# Receives input from a server computer. The input will be
# provided by a gamepad for rover manoeuvring
#
# Usage:
# When server script is ready for a client, run this script. The
# commands received will be printed on the terminal



# -*- coding: utf-8 -*-
import socket
import sys
import RPi.GPIO as GPIO
import ThunderBorg
import time
from time import sleep

port = 8005
ip_address = "192.168.0.1" #IP Address of PC
control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
control_socket.bind(('0.0.0.0', port))
print("waiting on port:", port)


#Number the RPI IO pins using BCM
GPIO.setmode(GPIO.BCM)
#Set the first pin as an output
GPIO.setup(18,GPIO.OUT)
#GPIO.setup(1,GPIO.OUT)
#Create a PWM instance
sampler = GPIO.PWM(18,50)
sampler.start(0)



#claw = GPIO.PWM(,50) #enter pin number
#Need to set the board address of each Thunderborg separately to addresses e.g. 10 11


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
    print(TB3.GetBatteryReading()) #prints battery voltage
    
    # Receive control strings over the socket from the PC.
    data, addr = control_socket.recvfrom(1024)
    # Print the messages
    print("Message: ", data)
    
    
    # Use the data to control motors

    #Extract throttle and steer_angle from data
    throttle = int(data[0:3])
    steer_angle = int(data[3:6])
    sampler_position = int(data[6:9])
    claw_position = int(data[9:12])
    #scale throttle, steer angle, and sampler position to range [-1,1]
    #old_sampler_position = sampler_position
    scaled_sampler_position = (90 - sampler_position)/90 #1 is max clockise, -1 max anticlockwise
    scaled_throttle =  ( throttle -90)/90
    scaled_steer_angle = (steer_angle - 90)/90
    
    claw_position_scaled = (90 - claw_position)/90
    
    

    left_power = scaled_throttle + scaled_steer_angle
    right_power = scaled_throttle - scaled_steer_angle

#Scale left_power and right_power so both stay in range [-1,1]

    if (left_power >= 1) or (right_power <= -1):
        left_power  *= 1/2
        right_power *= 1/2

    TB1.SetMotors(left_power)
    TB2.SetMotors(right_power)
    
 #   if claw_position == 1:
  #      claw.ChangeDutyCycle(10)
  #  else:
  #      claw.ChangeDutyCycle(5)


    #Sampler Control Code
    #Servo is neutral at 1.5ms, >1.5 Counter-Clockwise, <1.5 Clockwise
    print(scaled_sampler_position)
    
    TB3.SetMotors(scaled_sampler_position)
    
    
    
    pulse_width = 1.5 - claw_position_scaled*1/4
        
    
    
    duty_cycle = pulse_width * 5 # this is the simplification of D = PW/T * 100 with f=1/T = 50Hz
    
    sampler.ChangeDutyCycle(duty_cycle)


control_socket.close()
GPIO.cleanup() #Check if neccessary
