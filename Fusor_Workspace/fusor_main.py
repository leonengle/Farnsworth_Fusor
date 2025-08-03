import vacuum_control as VC
import communication as com


RPi_3b = com.SSHClient("RPi_1_IP", 22, "username", "password", "command_to_send {}")
turboPump = VC.TurboPump("name")
supply30kV = VC.PowerSupply("30kV Supply")

supply30kV.set_voltage(RPi_3b, 30000)  # Set voltage to 30kV

turboPump.setPower(85)