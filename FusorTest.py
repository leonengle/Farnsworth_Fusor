import PySimpleGUI as sg
import paramiko

# SSH connection settings
PI_HOST = '192.168.1.100'     # Replace with your Raspberry Pi's IP
PI_PORT = 22
PI_USERNAME = 'pi'            # Replace with your Pi's username
PI_PASSWORD = 'raspberry'     # Replace with your Pi's password
PI_COMMAND = 'echo {} > ~/received_bits.txt'  # Change as needed

def send_ssh_command(bitstring):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(PI_HOST, port=PI_PORT, username=PI_USERNAME, password=PI_PASSWORD)

        # Send the command
        command = PI_COMMAND.format(bitstring)
        stdin, stdout, stderr = client.exec_command(command)

        # Collect any errors (optional)
        error = stderr.read().decode()
        if error:
            sg.popup_error("Error sending data:", error)
        else:
            sg.popup("Sent successfully:", bitstring)
        client.close()
    except Exception as e:
        sg.popup_error("SSH Connection Failed", str(e))

# GUI layout
layout = [
    [sg.Text("Select Value (0-1023):")],
    [sg.Slider(range=(0, 1023), orientation='h', size=(50, 15), key='SLIDER')],
    [sg.Button('Send'), sg.Button('Exit')]
]

# Create the window
window = sg.Window("10-bit SSH Sender", layout)

# Event loop
while True:
    event, values = window.read()
    if event in (sg.WINDOW_CLOSED, 'Exit'):
        break
    elif event == 'Send':
        val = int(values['SLIDER'])
        bitstring = format(val, '010b')  # Convert to 10-bit binary
        send_ssh_command(bitstring)

window.close()
