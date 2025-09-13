def importChecker():
  try:
    import PySimpleGUI
    print("PySimpleGUI imported successfully!")
  except ImportError as e:
    print("Import Failed")
    return False
    
  try:
    import paramiko
    print("Paramiko imported successfully!")
  except ImportError as e:
    print("Import Failed")
    return False
