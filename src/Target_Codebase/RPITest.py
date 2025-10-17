import RPi.GPIO as GPIO
import time

PIN = 16
PIN2 = 23
PIN3 = 26
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN,GPIO.OUT)
GPIO.setup(PIN2, GPIO.OUT)
GPIO.setup(PIN3, GPIO.OUT)
try:
	while True:
	#	GPIO.output(PIN, GPIO.HIGH)
	#	GPIO.output(PIN2, GPIO.HIGH)
		GPIO.output(PIN3, GPIO.HIGH)
		time.sleep(1)
	#	GPIO.output(PIN, GPIO.LOW)
	#	GPIO.output(PIN2, GPIO.LOW)
		GPIO.output(PIN3, GPIO.LOW)
		time.sleep(1)
except KeyboardInterrupt:
	GPIO.cleanup()
