#include <AccelStepper.h>

const int MOTOR_STEP_PINS[5] = {3, 6, 8, 10, 12};
const int MOTOR_DIR_PINS[5] = {2, 5, 7, 9, 11};

const int MECHANICAL_PUMP_PIN = A0;
const int TURBO_PUMP_PIN = A1;
const int VARIAC_LIMIT_SWITCH_PIN = A3;
const int ENABLE_PIN = 4;

const float DEG_PER_STEP = 1.8;
const float STEPS_PER_DEG = 1.0 / DEG_PER_STEP;
const int TOTAL_STEPS = 200;
const int TOTAL_DEGREES = 360;
const int VARIAC_MAX_DEGREES = 300;
const int VARIAC_GEAR_RATIO = 30;

AccelStepper motors[5] = {
  AccelStepper(AccelStepper::DRIVER, MOTOR_STEP_PINS[0], MOTOR_DIR_PINS[0]),
  AccelStepper(AccelStepper::DRIVER, MOTOR_STEP_PINS[1], MOTOR_DIR_PINS[1]),
  AccelStepper(AccelStepper::DRIVER, MOTOR_STEP_PINS[2], MOTOR_DIR_PINS[2]),
  AccelStepper(AccelStepper::DRIVER, MOTOR_STEP_PINS[3], MOTOR_DIR_PINS[3]),
  AccelStepper(AccelStepper::DRIVER, MOTOR_STEP_PINS[4], MOTOR_DIR_PINS[4])
};

int currentDeg[5] = {0, 0, 0, 0, 0};
String serialBuffer = "";
bool newCommand = false;
int targetMotor = 0;
int targetDeg = 0;

bool mechanicalPumpState = false;
bool turboPumpState = false;

void handleSerialInput();
void applyMove();
long degreesToSteps(int newDeg, int oldDeg, int motorIdx);

void setup() {
  Serial.begin(9600);
  
  while (!Serial) {
    ;
  }
  
  delay(1000);

  for (int i = 0; i < 5; i++) {
    pinMode(MOTOR_DIR_PINS[i], OUTPUT);
    if (i == 4) {
      motors[i].setMaxSpeed(100);
      motors[i].setAcceleration(50);
    } else {
      motors[i].setMaxSpeed(1000);
      motors[i].setAcceleration(500);
    }
    motors[i].setCurrentPosition(0);
  }
  
  pinMode(MECHANICAL_PUMP_PIN, OUTPUT);
  pinMode(TURBO_PUMP_PIN, OUTPUT);
  pinMode(VARIAC_LIMIT_SWITCH_PIN, INPUT_PULLUP);
  digitalWrite(MECHANICAL_PUMP_PIN, LOW);
  digitalWrite(TURBO_PUMP_PIN, LOW);
  mechanicalPumpState = false;
  turboPumpState = false;
  
  digitalWrite(MOTOR_DIR_PINS[4], LOW);
  while (digitalRead(VARIAC_LIMIT_SWITCH_PIN) == LOW) {
    digitalWrite(MOTOR_STEP_PINS[4], HIGH);
    delayMicroseconds(500);
    digitalWrite(MOTOR_STEP_PINS[4], LOW);
    delayMicroseconds(500);
  }
  
  bool limitSwitchState = digitalRead(VARIAC_LIMIT_SWITCH_PIN);
  if (limitSwitchState == LOW) {
    digitalWrite(MOTOR_DIR_PINS[4], LOW);
  } else {
    digitalWrite(MOTOR_DIR_PINS[4], HIGH);
  }
  
  Serial.println("ARDUINO_READY: Fusor Motor Controller v1.0");
  Serial.println("Motor pin assignments:");
  for (int i = 0; i < 5; i++) {
    Serial.print("MOTOR_");
    Serial.print(i + 1);
    Serial.print(": Step=");
    Serial.print(MOTOR_STEP_PINS[i]);
    Serial.print(", Dir=");
    Serial.print(MOTOR_DIR_PINS[i]);
    Serial.println(" (ACTIVE)");
  }
  Serial.print("MECHANICAL_PUMP: Pin A0 (");
  Serial.print(MECHANICAL_PUMP_PIN);
  Serial.println(") (ACTIVE)");
  Serial.print("TURBO_PUMP: Pin A1 (");
  Serial.print(TURBO_PUMP_PIN);
  Serial.println(") (ACTIVE)");
  Serial.print("VARIAC_LIMIT_SWITCH: Pin A2 (");
  Serial.print(VARIAC_LIMIT_SWITCH_PIN);
  Serial.println(") (ACTIVE)");
  Serial.println("Ready to receive commands:");
  Serial.println("  Motor 1-4: MOTOR_X:degree (0-359)");
  Serial.println("  Motor 5 (VARIAC): MOTOR_5:degree (0-300)");
  Serial.println("  Mechanical Pump: SET_MECHANICAL_PUMP:0-100");
  Serial.println("  Turbo Pump: SET_TURBO_PUMP:0-100");
}

void loop() {
  handleSerialInput();
  applyMove();
  digitalWrite(ENABLE_PIN, LOW);
  for (int i = 0; i < 5; i++) {
    motors[i].run();
  }
}

long degreesToSteps(int newDeg, int oldDeg, int motorIdx) {
  int deltaDeg = newDeg - oldDeg;
  long steps;
  
  if (motorIdx == 4) {
    steps = (long)(abs(deltaDeg) * 54);
  } else {
    steps = (long)(abs(deltaDeg) * STEPS_PER_DEG);
  }
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
        
        if (cmd.startsWith("SET_MECHANICAL_PUMP:")) {
          int colonIndex = cmd.indexOf(':');
          if (colonIndex > 0) {
            String powerStr = cmd.substring(colonIndex + 1);
            powerStr.trim();
            int power = powerStr.toInt();
            
            if (power >= 0 && power <= 100) {
              if (power == 0) {
                mechanicalPumpState = false;
                digitalWrite(MECHANICAL_PUMP_PIN, LOW);
                Serial.println("OK: MECHANICAL_PUMP OFF (0%)");
              } else if (power == 100) {
                mechanicalPumpState = true;
                digitalWrite(MECHANICAL_PUMP_PIN, HIGH);
                Serial.println("OK: MECHANICAL_PUMP ON (100%)");
              }
            } else {
              Serial.print("ERROR: Invalid mechanical pump power ");
              Serial.println(power);
            }
          }
          serialBuffer = "";
          continue;
        }
        
        if (cmd.startsWith("SET_TURBO_PUMP:")) {
          int colonIndex = cmd.indexOf(':');
          if (colonIndex > 0) {
            String powerStr = cmd.substring(colonIndex + 1);
            powerStr.trim();
            int power = powerStr.toInt();
            
            if (power >= 0 && power <= 100) {
              if (power == 0) {
                turboPumpState = false;
                digitalWrite(TURBO_PUMP_PIN, LOW);
                Serial.println("OK: TURBO_PUMP OFF (0%)");
              } else if (power == 100) {
                turboPumpState = true;
                digitalWrite(TURBO_PUMP_PIN, HIGH);
                Serial.println("OK: TURBO_PUMP ON (100%)");
              }
            } else {
              Serial.print("ERROR: Invalid turbo pump power ");
              Serial.println(power);
            }
          }
          serialBuffer = "";
          continue;
        }
        
        int colonIndex = serialBuffer.indexOf(':');
        
        if (colonIndex > 0) {
          String motorPart = serialBuffer.substring(0, colonIndex);
          motorPart.trim();
          motorPart.toUpperCase();
          
          if (motorPart.startsWith("MOTOR_")) {
            String motorIdStr = motorPart.substring(6);
            int motorId = motorIdStr.toInt();
            
            if (motorId >= 1 && motorId <= 5) {
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

  int motorIdx = targetMotor;

  if (motorIdx == 4) {
    if (targetDeg < 0) {
      targetDeg = 0;
    }
    if (targetDeg > VARIAC_MAX_DEGREES) {
      targetDeg = VARIAC_MAX_DEGREES;
    }

    if (targetDeg < 0 || targetDeg > VARIAC_MAX_DEGREES) {
      Serial.print("ERROR: VARIAC motor degree out of range (0-");
      Serial.print(VARIAC_MAX_DEGREES);
      Serial.print("): ");
      Serial.println(targetDeg);
      newCommand = false;
      return;
    }

    if (targetDeg == currentDeg[motorIdx]) {
      Serial.print("OK: MOTOR_");
      Serial.print(motorIdx + 1);
      Serial.print(" (VARIAC) already at ");
      Serial.print(currentDeg[motorIdx]);
      Serial.println(" degrees");
      newCommand = false;
      return;
    }

    bool limitSwitchState = digitalRead(VARIAC_LIMIT_SWITCH_PIN);
    long steps = degreesToSteps(targetDeg, currentDeg[motorIdx], motorIdx);
    long newPos;
    
    if (limitSwitchState == LOW) {
      digitalWrite(MOTOR_DIR_PINS[motorIdx], LOW);
      if (targetDeg > currentDeg[motorIdx]) {
        newPos = motors[motorIdx].currentPosition() - steps;
      } else {
        newPos = motors[motorIdx].currentPosition() + steps;
      }
    } else {
      digitalWrite(MOTOR_DIR_PINS[motorIdx], HIGH);
      if (targetDeg > currentDeg[motorIdx]) {
        newPos = motors[motorIdx].currentPosition() + steps;
      } else {
        newPos = motors[motorIdx].currentPosition() - steps;
      }
    }

    motors[motorIdx].moveTo(newPos);
    motors[motorIdx].runToPosition();
    currentDeg[motorIdx] = targetDeg;
    
    Serial.print("OK: MOTOR_");
    Serial.print(motorIdx + 1);
    Serial.print(" (VARIAC) moved to ");
    Serial.print(currentDeg[motorIdx]);
    Serial.print(" degrees (limit switch: ");
    Serial.print(limitSwitchState == LOW ? "LOW/CCW" : "HIGH/CW");
    Serial.println(")");
  } else {
    if (targetDeg == 360) {
      targetDeg = 0;
    }

    if (targetDeg < 0 || targetDeg > 359) {
      Serial.print("ERROR: Invalid degree ");
      Serial.println(targetDeg);
      newCommand = false;
      return;
    }

    if (targetDeg > currentDeg[motorIdx]) {
      long steps = degreesToSteps(targetDeg, currentDeg[motorIdx], motorIdx);
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
      long steps = degreesToSteps(targetDeg, currentDeg[motorIdx], motorIdx);
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
  }

  newCommand = false;
}
