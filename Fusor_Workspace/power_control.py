import communication as com

class PowerSupply:
    def __init__(self, name):
        self.name = name
        self.maxCurrent = 0
        self.maxVoltage = 0
        self.i = 0
        self.v = 0
        self.vDesired = 0
        self.iDesired = 0
    
    def set_voltage(RPi, voltageSetting):
        RPi.send_ssh_command(voltageSetting)