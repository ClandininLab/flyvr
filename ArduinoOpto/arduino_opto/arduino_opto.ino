#define LED_PIN 8
#define LED_PIN_LASER 9 

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(LED_PIN_LASER, OUTPUT);
  led_off();
  Serial.begin(9600); 
}

void led_on(){
  digitalWrite(LED_PIN, LOW);
  digitalWrite(LED_PIN_LASER, HIGH);
}

void led_off(){
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(LED_PIN_LASER, LOW);
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
