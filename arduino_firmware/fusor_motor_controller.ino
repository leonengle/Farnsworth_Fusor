#include <AccelStepper.h>
#include <ArduinoJson.h>

struct MotorConfig {
  const char* label;
  int stepPin;
  int dirPin;
  int enablePin;
  int stepsPerRevolution;
  int microsteps;
};

const MotorConfig MOTOR_CONFIGS[] = {
  {"MOTOR_1", 2, 3, 4, 200, 16},
  {"MOTOR_2", 5, 6, 7, 200, 16},
  {"MOTOR_3", 8, 9, 10, 200, 16},
  {"MOTOR_4", 11, 12, 13, 200, 16},
  {"MOTOR_5", A0, A1, A2, 200, 16},
  {"MOTOR_6", A3, A4, A5, 200, 16},
};

const int NUM_MOTORS = sizeof(MOTOR_CONFIGS) / sizeof(MOTOR_CONFIGS[0]);

const float MAX_SPEED = 1000.0;
const float ACCELERATION = 500.0;

const unsigned long SERIAL_TIMEOUT = 1000;
const int SERIAL_BUFFER_SIZE = 128;

AccelStepper* motors[NUM_MOTORS];

int currentAngles[NUM_MOTORS];

String inputString = "";
boolean stringComplete = false;

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(SERIAL_TIMEOUT);
  
  inputString.reserve(SERIAL_BUFFER_SIZE);
  
  for (int i = 0; i < NUM_MOTORS; i++) {
    const MotorConfig& config = MOTOR_CONFIGS[i];
    
    motors[i] = new AccelStepper(AccelStepper::DRIVER, config.stepPin, config.dirPin);
    
    motors[i]->setMaxSpeed(MAX_SPEED);
    motors[i]->setAcceleration(ACCELERATION);
    motors[i]->setCurrentPosition(0);
    
    if (config.enablePin >= 0) {
      pinMode(config.enablePin, OUTPUT);
      digitalWrite(config.enablePin, LOW);
    }
    
    currentAngles[i] = 0;
  }
  
  Serial.print("FUSOR_MOTOR_CONTROLLER_READY:");
  Serial.print(NUM_MOTORS);
  Serial.println("_MOTORS");
  Serial.flush();
  
  delay(100);
}

void loop() {
  if (stringComplete) {
    String cmd = inputString;
    inputString = "";
    stringComplete = false;
    processCommand(cmd);
  }
  
  for (int i = 0; i < NUM_MOTORS; i++) {
    if (motors[i]) {
      motors[i]->run();
    }
  }
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    
    if (inChar == '\n') {
      stringComplete = true;
      break;
    } else if (inChar != '\r') {
      if (inputString.length() < SERIAL_BUFFER_SIZE - 1) {
        inputString += inChar;
      }
    }
  }
}

void processCommand(String command) {
  command.trim();
  
  if (command.length() == 0) {
    return;
  }
  
  if (command.startsWith("MOTOR:")) {
    String jsonStr = command.substring(6);
    jsonStr.trim();
    
    if (jsonStr.length() == 0) {
      Serial.print("ERROR: Empty JSON string after MOTOR: | Full command: ");
      Serial.println(command);
      return;
    }
    
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, jsonStr);
    
    if (error) {
      Serial.print("ERROR: Invalid JSON format: ");
      Serial.print(error.c_str());
      Serial.print(" | JSON received: ");
      Serial.println(jsonStr);
      return;
    }
    
    if (!doc.containsKey("component_name") || !doc.containsKey("motor_degree")) {
      Serial.println("ERROR: Missing component_name or motor_degree in JSON");
      return;
    }
    
    String label = doc["component_name"].as<String>();
    float motorDegreeFloat = doc["motor_degree"].as<float>();
    int targetAngle = (int)round(motorDegreeFloat);
    
    if (targetAngle < 0 || targetAngle > 360) {
      Serial.print("ERROR: Angle out of range (0-360). Received: ");
      Serial.println(targetAngle);
      return;
    }
    
    if (targetAngle == 360) {
      targetAngle = 0;
    }
    
    int motorIndex = findMotorByLabel(label);
    
    if (motorIndex < 0) {
      Serial.print("ERROR: Unknown motor label: ");
      Serial.println(label);
      printAvailableMotors();
      return;
    }
    
    moveMotorToAngle(motorIndex, targetAngle);
    
    Serial.print(label);
    Serial.print(":SUCCESS:");
    Serial.print(targetAngle);
    Serial.println("_degrees");
    Serial.flush();
    return;
  }
  
  int colonIndex = command.indexOf(':');
  
  if (colonIndex < 0) {
    Serial.print("ERROR: Invalid command format. Expected: <LABEL>:<ANGLE> or MOTOR:{...}");
    Serial.print(" Received: ");
    Serial.println(command);
    return;
  }
  
  String label = command.substring(0, colonIndex);
  label.trim();
  String angleStr = command.substring(colonIndex + 1);
  angleStr.trim();
  
  int targetAngle = angleStr.toInt();
  
  if (targetAngle < 0 || targetAngle > 360) {
    Serial.print("ERROR: Angle out of range (0-360). Received: ");
    Serial.println(targetAngle);
    return;
  }
  
  if (targetAngle == 360) {
    targetAngle = 0;
  }
  
  int motorIndex = findMotorByLabel(label);
  
  if (motorIndex < 0) {
    Serial.print("ERROR: Unknown motor label: ");
    Serial.println(label);
    printAvailableMotors();
    return;
  }
  
  moveMotorToAngle(motorIndex, targetAngle);
  
  Serial.print(label);
  Serial.print(":SUCCESS:");
  Serial.print(targetAngle);
  Serial.println("_degrees");
  Serial.flush();
}

void moveMotorToAngle(int motorIndex, int targetAngle) {
  if (motorIndex < 0 || motorIndex >= NUM_MOTORS) {
    Serial.println("ERROR: Invalid motor index");
    return;
  }
  
  const MotorConfig& config = MOTOR_CONFIGS[motorIndex];
  AccelStepper* motor = motors[motorIndex];
  
  if (!motor) {
    Serial.println("ERROR: Motor not initialized");
    return;
  }
  
  int currentAngle = currentAngles[motorIndex];
  int angleDifference = targetAngle - currentAngle;
  
  if (angleDifference > 180) {
    angleDifference -= 360;
  } else if (angleDifference < -180) {
    angleDifference += 360;
  }
  
  int totalStepsPerRevolution = config.stepsPerRevolution * config.microsteps;
  long currentSteps = motor->currentPosition();
  long stepsToMove = (long)((angleDifference / 360.0) * totalStepsPerRevolution);
  long targetSteps = currentSteps + stepsToMove;
  
  if (config.enablePin >= 0) {
    digitalWrite(config.enablePin, LOW);
  }
  
  motor->moveTo(targetSteps);
  
  unsigned long startTime = millis();
  const unsigned long TIMEOUT_MS = 30000;
  
  while (motor->distanceToGo() != 0) {
    motor->run();
    
    if (millis() - startTime > TIMEOUT_MS) {
      Serial.print("WARNING: Motor ");
      Serial.print(config.label);
      Serial.println(" movement timeout");
      break;
    }
    
    delay(1);
  }
  
  currentAngles[motorIndex] = targetAngle;
}

int findMotorByLabel(const String& label) {
  for (int i = 0; i < NUM_MOTORS; i++) {
    if (label.equals(MOTOR_CONFIGS[i].label)) {
      return i;
    }
  }
  return -1;
}

void printAvailableMotors() {
  Serial.print("Available motors: ");
  for (int i = 0; i < NUM_MOTORS; i++) {
    Serial.print(MOTOR_CONFIGS[i].label);
    if (i < NUM_MOTORS - 1) {
      Serial.print(", ");
    }
  }
  Serial.println();
}

void enableMotor(int motorIndex) {
  if (motorIndex >= 0 && motorIndex < NUM_MOTORS) {
    const MotorConfig& config = MOTOR_CONFIGS[motorIndex];
    if (config.enablePin >= 0) {
      digitalWrite(config.enablePin, LOW);
      Serial.print(config.label);
      Serial.println(":ENABLED");
    }
  }
}

void disableMotor(int motorIndex) {
  if (motorIndex >= 0 && motorIndex < NUM_MOTORS) {
    const MotorConfig& config = MOTOR_CONFIGS[motorIndex];
    if (config.enablePin >= 0) {
      digitalWrite(config.enablePin, HIGH);
      Serial.print(config.label);
      Serial.println(":DISABLED");
    }
  }
}

void setMotorSpeed(int motorIndex, float speed) {
  if (motorIndex >= 0 && motorIndex < NUM_MOTORS && motors[motorIndex]) {
    motors[motorIndex]->setMaxSpeed(speed);
    Serial.print(MOTOR_CONFIGS[motorIndex].label);
    Serial.print(":SPEED_SET:");
    Serial.println(speed);
  }
}
