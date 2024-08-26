#include <Keyboard.h>

const byte BUTTON_PIN = 0;  // Pin to which the button is connected
const char* passwords[] = {"Password123", "123456", "phishwozhere"}; // Password list to chose from
const int PASSWORDS_LENGTH = sizeof(passwords) / sizeof(passwords[0]); // Calculate size of password list

void setup(){
  randomSeed(analogRead(0));
  pinMode(BUTTON_PIN, INPUT);
  digitalWrite(BUTTON_PIN, HIGH);
  delay(5000);
}

void loop(){
  if (digitalRead(BUTTON_PIN) == LOW){
    // todo: should probably add debouncing but meh
    Keyboard.print(passwords[random(0,PASSWORDS_LENGTH)]); // Send a random password from the passwords list
    Keyboard.write(176); // Press enter key - works on macos
    delay(1500);
  }
}