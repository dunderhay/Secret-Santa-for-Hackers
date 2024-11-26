const int servoPin = 2;
const int ledPin = 5;

void setup() {
  Serial.begin(115200);
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);
  myServo.attach(servoPin);
  myServo.write(0);
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "wave") {
      for (int i = 0; i < 3; i++) { // LED flashes three times
        digitalWrite(ledPin, HIGH);
        delay(250); // LED on for 250ms
        digitalWrite(ledPin, LOW);
        delay(250); // LED off for 250ms
      }

      for (int i = 0; i < 2; i++) {  // Servo waves twice
        myServo.write(0);
        digitalWrite(ledPin, HIGH);  // LED on during servo movement
        delay(500);
        myServo.write(180);
        digitalWrite(ledPin, LOW);  // LED off during servo return
        delay(500);
      }

      myServo.write(0);  // Reset servo to initial position
      Serial.println("Wave completed");
    } else {
      Serial.println("Unknown command");
    }
  }
}