import RPi.GPIO as GPIO
import time

class ServoController:
    def __init__(self, servo_pin):

        self.servo_pin = servo_pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.servo_pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.servo_pin, 50)  
        self.pwm.start(0)  
    
    def set_angle(self, angle):

        duty = 2.5 + (angle / 18.0)
        self.pwm.ChangeDutyCycle(duty)
        time.sleep(0.5)
        self.pwm.ChangeDutyCycle(0) 
    
    def cleanup(self):

        self.pwm.stop()
        GPIO.cleanup()
