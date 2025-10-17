from base_classes import VacuumControlInterface

class TurboPump(VacuumControlInterface):
    def __init__(self, name):
        super().__init__(name)

    def set_power(self, powerInput):
        self.powerSetting = max(0, min(100, powerInput)) #clamps powerInput between 0, 100
        print(f"Vaccuum pump set to {self.powerSetting}")
