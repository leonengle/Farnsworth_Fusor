class TurboPump:
    def __init__(self, name):
        self.name = name
        self.powerSetting = 0

    def set_power(self, powerInput):
        self.powerSetting = max(0, min(100, powerInput)) #clamps powerInput between 0, 100
        print(f"Vaccuum pump set to {self.powerSetting}")