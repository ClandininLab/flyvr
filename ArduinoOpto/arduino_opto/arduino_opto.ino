#define LED_PIN 8

void setup() {
  pinMode(LED_PIN, OUTPUT);
  led_off();
  Serial.begin(9600); 
}

void led_on(){
  digitalWrite(LED_PIN, LOW);
}

void led_off(){
  digitalWrite(LED_PIN, HIGH);
}

void loop() {
  if (Serial.available() > 0) {
    byte incomingByte = Serial.read();
    if (incomingByte == 0xbe) {
      led_on();
    } else if (incomingByte == 0xef) {
      led_off();
    }
  }
}
