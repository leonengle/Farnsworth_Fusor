import communication as com
import random #remove later

class PowerSupply:
    def __init__(self, name, maxVoltage, maxCurrent):
        self.name = name
        self.maxVoltage = maxVoltage
        self.maxCurrent = maxCurrent
        self.i = 0
        self.v = 0
        self.vDesired = 0
        self.iDesired = 0
    
    def set_voltage(self, voltageSetting):
        self.vDesired = voltageSetting
        #RPi.send_ssh_command(voltageSetting)
        print(f"Setting voltage to {voltageSetting}V")

    def set_current(self, RPi, currentSetting):
        self.iDesired = currentSetting
        #RPi.send_ssh_command(currentSetting)
        print(f"Setting current to {currentSetting}A")

    def get_voltage(self, RPi):
        self.v = random.random() #RPi.send_ssh_command(voltageSetting)
        print(f"Voltmeter reading is {self.i}V")

    def get_current(self, RPi):
        self.i = random.random() #RPi.send_ssh_command(voltageSetting)
        print(f"Current meter reading is {self.i}A")

    #configure interrupt for if max current is exceeded, decrease voltage setting