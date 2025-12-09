const int stepPin = 3;
const int dirPin  = 2;
const int enablePin = 4;
const int limitPin = A3;

void setup() {
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  pinMode(limitPin, INPUT_PULLUP);

  digitalWrite(dirPin, HIGH);
}

void loop() {
  digitalWrite(enablePin, LOW);
  if (digitalRead(limitPin) == LOW) {
    return;
  }

  digitalWrite(stepPin, HIGH);
  delayMicroseconds(1000);
  digitalWrite(stepPin, LOW);
  delayMicroseconds(1000);
}
