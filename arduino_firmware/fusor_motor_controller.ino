#include <AccelStepper.h>

const int MOTOR_STEP_PINS[6] = {3, 5, 7, 9, 11, 13};
const int MOTOR_DIR_PINS[6] = {4, 6, 8, 10, 12, A0};

const float DEG_PER_STEP = 1.8;
const float STEPS_PER_DEG = 1.0 / DEG_PER_STEP;
const int TOTAL_STEPS = 200;
const int TOTAL_DEGREES = 360;

AccelStepper motors[6] = {
  AccelStepper(AccelStepper::DRIVER, MOTOR_STEP_PINS[0], MOTOR_DIR_PINS[0]),
  AccelStepper(AccelStepper::DRIVER, MOTOR_STEP_PINS[1], MOTOR_DIR_PINS[1]),
  AccelStepper(AccelStepper::DRIVER, MOTOR_STEP_PINS[2], MOTOR_DIR_PINS[2]),
  AccelStepper(AccelStepper::DRIVER, MOTOR_STEP_PINS[3], MOTOR_DIR_PINS[3]),
  AccelStepper(AccelStepper::DRIVER, MOTOR_STEP_PINS[4], MOTOR_DIR_PINS[4]),
  AccelStepper(AccelStepper::DRIVER, MOTOR_STEP_PINS[5], MOTOR_DIR_PINS[5])
};

int currentDeg[6] = {0, 0, 0, 0, 0, 0};
String serialBuffer = "";
bool newCommand = false;
int targetMotor = 0;
int targetDeg = 0;

long degreesToSteps(int newDeg, int oldDeg) {
  int deltaDeg = newDeg - oldDeg;
  long steps = (long)(abs(deltaDeg) * STEPS_PER_DEG);
  return steps;
}

void handleSerialInput() {
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        String cmd = serialBuffer;
        cmd.trim();
        cmd.toUpperCase();
        
        int colonIndex = serialBuffer.indexOf(':');
        
        if (colonIndex > 0) {
          String motorPart = serialBuffer.substring(0, colonIndex);
          motorPart.trim();
          motorPart.toUpperCase();
          
          if (motorPart.startsWith("MOTOR_")) {
            String motorIdStr = motorPart.substring(6);
            int motorId = motorIdStr.toInt();
            
            if (motorId >= 1 && motorId <= 6) {
              targetMotor = motorId - 1;
              String degreeStr = serialBuffer.substring(colonIndex + 1);
              degreeStr.trim();
              targetDeg = degreeStr.toInt();
              newCommand = true;
            } else {
              Serial.print("ERROR: Invalid motor ID ");
              Serial.println(motorId);
            }
          } else {
            targetMotor = 0;
            String degreeStr = serialBuffer.substring(colonIndex + 1);
            degreeStr.trim();
            targetDeg = degreeStr.toInt();
            newCommand = true;
          }
        } else {
          targetMotor = 0;
          targetDeg = serialBuffer.toInt();
          newCommand = true;
        }
        
        serialBuffer = "";
      }
    } else {
      serialBuffer += c;
    }
  }
}

void applyMove() {
  if (!newCommand) return;

  if (targetDeg == 360) {
    targetDeg = 0;
  }

  if (targetDeg < 0 || targetDeg > 359) {
    Serial.print("ERROR: Invalid degree ");
    Serial.println(targetDeg);
    newCommand = false;
    return;
  }

  int motorIdx = targetMotor;

  if (motorIdx == 0) {
    if (targetDeg > currentDeg[motorIdx]) {
      long steps = degreesToSteps(targetDeg, currentDeg[motorIdx]);
      digitalWrite(MOTOR_DIR_PINS[motorIdx], HIGH);
      long newPos = motors[motorIdx].currentPosition() + steps;
      motors[motorIdx].moveTo(newPos);
      motors[motorIdx].runToPosition();
      currentDeg[motorIdx] = targetDeg;
      Serial.print("OK: MOTOR_");
      Serial.print(motorIdx + 1);
      Serial.print(" moved clockwise (forward) to ");
      Serial.print(currentDeg[motorIdx]);
      Serial.println(" degrees");
    } else if (targetDeg < currentDeg[motorIdx]) {
      long steps = degreesToSteps(targetDeg, currentDeg[motorIdx]);
      digitalWrite(MOTOR_DIR_PINS[motorIdx], LOW);
      long newPos = motors[motorIdx].currentPosition() - steps;
      motors[motorIdx].moveTo(newPos);
      motors[motorIdx].runToPosition();
      currentDeg[motorIdx] = targetDeg;
      Serial.print("OK: MOTOR_");
      Serial.print(motorIdx + 1);
      Serial.print(" moved counter-clockwise (backward) to ");
      Serial.print(currentDeg[motorIdx]);
      Serial.println(" degrees");
    } else {
      Serial.print("OK: MOTOR_");
      Serial.print(motorIdx + 1);
      Serial.print(" already at ");
      Serial.print(currentDeg[motorIdx]);
      Serial.println(" degrees");
    }
} else {
    currentDeg[motorIdx] = targetDeg;
    Serial.print("OK: MOTOR_");
    Serial.print(motorIdx + 1);
    Serial.print(" position set to ");
    Serial.print(currentDeg[motorIdx]);
    Serial.println(" degrees (placeholder - not connected)");
  }

  newCommand = false;
}

void setup() {
  Serial.begin(9600);
  
  while (!Serial) {
    ;
  }
  
  delay(1000);

  pinMode(MOTOR_DIR_PINS[0], OUTPUT);
  motors[0].setMaxSpeed(1000);
  motors[0].setAcceleration(500);
  motors[0].setCurrentPosition(0);
  
  Serial.println("ARDUINO_READY: Fusor Motor Controller v1.0");
  Serial.println("Motor pin assignments:");
  Serial.print("MOTOR_1: Step=");
  Serial.print(MOTOR_STEP_PINS[0]);
  Serial.print(", Dir=");
  Serial.print(MOTOR_DIR_PINS[0]);
  Serial.println(" (ACTIVE)");
  for (int i = 1; i < 6; i++) {
    Serial.print("MOTOR_");
    Serial.print(i + 1);
    Serial.print(": Step=");
    Serial.print(MOTOR_STEP_PINS[i]);
    Serial.print(", Dir=");
    Serial.print(MOTOR_DIR_PINS[i]);
    Serial.println(" (PLACEHOLDER)");
  }
  Serial.println("Ready to receive motor commands (format: MOTOR_X:degree)");
}

void loop() {
  handleSerialInput();
  applyMove();
  motors[0].run();
}
