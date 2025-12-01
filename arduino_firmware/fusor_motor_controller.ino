#include <AccelStepper.h>

struct MotorConfig {
  const char* label;
  int stepPin;
  int dirPin;
  int stepsPerRevolution;
};

const MotorConfig MOTOR_CONFIGS[] = {
  {"MOTOR_1", 2, 3, 200},
  {"MOTOR_2", 4, 5, 200},
  {"MOTOR_3", 6, 7, 200},
  {"MOTOR_4", 8, 9, 200},
  {"MOTOR_5", 10, 11, 200},
  {"MOTOR_6", 12, 13, 200},
};

const int NUM_MOTORS = sizeof(MOTOR_CONFIGS) / sizeof(MOTOR_CONFIGS[0]);

const float MAX_SPEED = 1000.0;
const float ACCELERATION = 500.0;

const unsigned long SERIAL_TIMEOUT = 1000;
const int SERIAL_BUFFER_SIZE = 128;

AccelStepper* motors[NUM_MOTORS];

int currentAngles[NUM_MOTORS];
bool motorMoving[NUM_MOTORS] = {false};
int targetAngles[NUM_MOTORS] = {0};

String inputString = "";
boolean stringComplete = false;

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(SERIAL_TIMEOUT);
  
  inputString.reserve(SERIAL_BUFFER_SIZE);
  
  for (int i = 0; i < NUM_MOTORS; i++) {
    const MotorConfig& config = MOTOR_CONFIGS[i];
    
    pinMode(config.stepPin, OUTPUT);
    pinMode(config.dirPin, OUTPUT);
    digitalWrite(config.stepPin, LOW);
    digitalWrite(config.dirPin, LOW);
    
    motors[i] = new AccelStepper(AccelStepper::DRIVER, config.stepPin, config.dirPin);
    
    motors[i]->setMaxSpeed(MAX_SPEED);
    motors[i]->setAcceleration(ACCELERATION);
    motors[i]->setCurrentPosition(0);
    
    currentAngles[i] = 0;
    motorMoving[i] = false;
    targetAngles[i] = 0;
  }
  
  Serial.print("FUSOR_MOTOR_CONTROLLER_READY:");
  Serial.print(NUM_MOTORS);
  Serial.println("_MOTORS");
  Serial.flush();
  
  delay(100);
  
  Serial.println("ARDUINO_TEST:READY");
  Serial.flush();
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
      bool isRunning = motors[i]->run();
      
      if (motorMoving[i] && !isRunning && motors[i]->distanceToGo() == 0) {
        motorMoving[i] = false;
        currentAngles[i] = targetAngles[i];
        
        Serial.print(MOTOR_CONFIGS[i].label);
        Serial.print(":STOPPED:");
        Serial.print(currentAngles[i]);
        Serial.print(":POS:");
        Serial.println(motors[i]->currentPosition());
        Serial.flush();
      }
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
  
  if (command == "TEST_PING") {
    Serial.println("PONG");
    Serial.flush();
    return;
  }
  
  Serial.print("RECEIVED_COMMAND:");
  Serial.println(command);
  Serial.flush();
  
  if (command.length() == 0) {
    Serial.println("ERROR: Empty command after trim");
    return;
  }
  
  int colonIndex = command.indexOf(':');
  
  if (colonIndex < 0) {
    Serial.print("ERROR: Invalid command format. Expected: <LABEL>:<ANGLE>");
    Serial.print(" Received: ");
    Serial.println(command);
    return;
  }
  
  String label = command.substring(0, colonIndex);
  label.trim();
  String angleStr = command.substring(colonIndex + 1);
  angleStr.trim();
  
  if (angleStr.length() == 0) {
    Serial.println("ERROR: Missing angle value");
    return;
  }
  
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
  
  if (angleDifference == 0) {
    Serial.print(config.label);
    Serial.println(":ALREADY_AT_TARGET");
    return;
  }
  
  long currentSteps = motor->currentPosition();
  
  long stepsToMove = (long)((angleDifference / 360.0) * config.stepsPerRevolution);
  
  long targetSteps = currentSteps + stepsToMove;
  
  pinMode(config.stepPin, OUTPUT);
  pinMode(config.dirPin, OUTPUT);
  
  Serial.print(config.label);
  Serial.print(":MOVING:from_");
  Serial.print(currentAngle);
  Serial.print("_to_");
  Serial.print(targetAngle);
  Serial.print("_(");
  Serial.print(stepsToMove);
  Serial.print("_steps):POS:");
  Serial.print(currentSteps);
  Serial.print("->");
  Serial.print(targetSteps);
  Serial.print(":");
  Serial.println(stepsToMove > 0 ? "FORWARD" : "BACKWARD");
  Serial.flush();
  
  motor->moveTo(targetSteps);
  motorMoving[motorIndex] = true;
  targetAngles[motorIndex] = targetAngle;
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
    Serial.print(config.label);
    Serial.println(":ENABLED");
  }
}

void disableMotor(int motorIndex) {
  if (motorIndex >= 0 && motorIndex < NUM_MOTORS) {
    const MotorConfig& config = MOTOR_CONFIGS[motorIndex];
    Serial.print(config.label);
    Serial.println(":DISABLED");
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
