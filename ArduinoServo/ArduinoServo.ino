/* modified from Sweep
 by BARRAGAN <http://barraganstudio.com>
*/

#include <Servo.h>

Servo myservo;  // create servo object to control a servo
// twelve servo objects can be created on most boards

int pos = 0;    // variable to store the servo position

void setup() {
  myservo.attach(9);  // attaches the servo on pin 9 to the servo object
  Serial.begin(9600); 
}

void loop() {
  if (Serial.available() > 0) {
    byte incomingByte = Serial.read();
    myservo.write(incomingByte);
  }
}

