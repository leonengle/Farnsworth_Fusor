#include <AccelStepper.h>

#define STEP_PIN 2
#define DIR_PIN 4

const float DEG_PER_STEP = 1.8;
const float STEPS_PER_DEG = 1.0 / DEG_PER_STEP;

AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);

int currentDeg = 0;
String serialBuffer = "";
bool newCommand = false;
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
        targetDeg = serialBuffer.toInt();
        newCommand = true;
        serialBuffer = "";
      }
    } else {
      serialBuffer += c;
    }
  }
}

void applyMove() {
  if (!newCommand) return;

  if (targetDeg < 0 || targetDeg > 359) {
    newCommand = false;
    return;
  }

  if (targetDeg != currentDeg) {
    long steps = degreesToSteps(targetDeg, currentDeg);

    if (targetDeg > currentDeg) {
      digitalWrite(DIR_PIN, HIGH);
    } else {
      digitalWrite(DIR_PIN, LOW);
    }

    long newPos = stepper.currentPosition() + steps;

    stepper.moveTo(newPos);
    stepper.runToPosition();

    currentDeg = targetDeg;
  }

  newCommand = false;
}

void setup() {
  Serial.begin(9600);

  pinMode(DIR_PIN, OUTPUT);

  stepper.setMaxSpeed(1000);
  stepper.setAcceleration(500);
  stepper.setCurrentPosition(0);
}

void loop() {
  handleSerialInput();
  applyMove();
}
