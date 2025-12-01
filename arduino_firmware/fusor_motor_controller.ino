#include <AccelStepper.h>

struct MotorConfig {
  const char* label;
  int stepPin;
  int dirPin;
  int stepsPerRev;
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

AccelStepper steppers[NUM_MOTORS] = {
  AccelStepper(AccelStepper::DRIVER, 2, 3),
  AccelStepper(AccelStepper::DRIVER, 4, 5),
  AccelStepper(AccelStepper::DRIVER, 6, 7),
  AccelStepper(AccelStepper::DRIVER, 8, 9),
  AccelStepper(AccelStepper::DRIVER, 10, 11),
  AccelStepper(AccelStepper::DRIVER, 12, 13)
};

int currentAngle[NUM_MOTORS] = {0};
String inputLine = "";

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < NUM_MOTORS; i++) {
    steppers[i].setMaxSpeed(800);
    steppers[i].setAcceleration(400);
    steppers[i].setCurrentPosition(0);
  }
  Serial.println("STEPPER_CONTROLLER_READY");
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      processCommand(inputLine);
      inputLine = "";
    } else if (c != '\r') {
      inputLine += c;
    }
  }

  for (int i = 0; i < NUM_MOTORS; i++) {
    steppers[i].run();
  }
}

int findMotorIndex(const String& label) {
  for (int i = 0; i < NUM_MOTORS; i++) {
    if (label.equals(MOTOR_CONFIGS[i].label)) return i;
  }
  return -1;
}

void moveMotorToAngle(int idx, int angle) {
  int diff = angle - currentAngle[idx];
  if (diff > 180) diff -= 360;
  if (diff < -180) diff += 360;

  long steps = (long)((diff / 360.0) * MOTOR_CONFIGS[idx].stepsPerRev);
  long target = steppers[idx].currentPosition() + steps;

  steppers[idx].moveTo(target);
  currentAngle[idx] = angle;

  Serial.print(MOTOR_CONFIGS[idx].label);
  Serial.print(":OK:");
  Serial.println(angle);
}

void processCommand(String cmd) {
  cmd.trim();
  
  int colon = cmd.indexOf(':');
  if (colon < 0) {
    Serial.println("ERROR_BAD_FORMAT");
    return;
  }

  String label = cmd.substring(0, colon);
  int angle = cmd.substring(colon + 1).toInt();

  if (angle < 0 || angle > 359) {
    Serial.println("ERROR_BAD_ANGLE");
    return;
  }

  int idx = findMotorIndex(label);
  if (idx < 0) {
    Serial.println("ERROR_UNKNOWN_MOTOR");
    return;
  }

  moveMotorToAngle(idx, angle);
}
