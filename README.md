# Quickstart: **Setup Instructions**

## First Time Access

### 1. Clone and enter the folder
If you have the previous versions of the repository cloned, delete the folder and clone the new version
```
git clone https://github.com/leonengle/Farnsworth_Fusor/
cd Farnsworth_Fusor
```
### 2. Create the virtual environment
```
python -m venv venv
```
### 3. Activate the virtual environment

On macOS/Linux:
```
source venv/bin/activate
```
On windows (command prompt):
```
venv/Scripts/activate
```
On windows (Powershell):
```
venv/Scripts/Activate.psl
```
**NOTE: Everytime you open a new terminal session after the virtual environment is integrated, only run step 3 in the guide!**

### 4. Download all dependencies

After getting in the virtual environment, it is important for everyone involved to be on the same version so there are less environment-related surprises 
```
pip install -r requirements.txt
```
**NOTE: PySimpleGUI is hosted on a private PyPI server. If you're using the old version, it is recommended to get the private version of the library since it is more up-to-date and maintained. The user is required to run these commands to uninstall any existing versions for this project:**
```
python -m pip uninstall PySimpleGUI
python -m pip cache purge
```
**Now you can download all dependencies:** 
```
pip install -r requirements.txt
```

### 5. Verify the environment (Optional)

Run the test script to make sure your environment is working
```
python testEnv.py
```

## Common Errors while implementing your virtual environment
### 1. Permission Error
If you are getting this error while running Step 3:

<img width="674" height="119" alt="image" src="https://github.com/user-attachments/assets/1cd02b3c-e6d6-4a73-b65d-c0ed6d0ee4c6" />

then:
  - Open Powershell as administrator
  - Run this command:
      ```
      Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
      ```
  - Type in "Y" in the prompt

Close out of powershell and redo the command. You should be good!

If you are using powershell to activate your visual environment, make sure to close out and open back the powershell command prompt (not admin)



