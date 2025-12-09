const int TURBO_PUMP_PIN = A0;
const int MECHANICAL_PUMP_PIN = A1;

void setup() {
  Serial.begin(9600);

  pinMode(TURBO_PUMP_PIN, OUTPUT);
  pinMode(MECHANICAL_PUMP_PIN, OUTPUT);

  digitalWrite(TURBO_PUMP_PIN, LOW);
  digitalWrite(MECHANICAL_PUMP_PIN, LOW);

  Serial.println("Relay verification starting...");
}

void loop() {
  Serial.println("Turning TURBO PUMP ON");
  digitalWrite(TURBO_PUMP_PIN, HIGH);
  delay(2000);

  Serial.println("Turning TURBO PUMP OFF");
  digitalWrite(TURBO_PUMP_PIN, LOW);
  delay(1000);

  Serial.println("Turning MECHANICAL PUMP ON");
  digitalWrite(MECHANICAL_PUMP_PIN, HIGH);
  delay(2000);

  Serial.println("Turning MECHANICAL PUMP OFF");
  digitalWrite(MECHANICAL_PUMP_PIN, LOW);
  delay(1000);
}
