#define ENABLE_N 8

#define STEP_X 2
#define STEP_Y1 3
#define STEP_Y2 4
#define DIR_X 5
#define DIR_Y1 6
#define DIR_Y2 7

#define LIM_PRESSED(v) (!((PINB>>v)&1))
#define LIM_N_PRESSED LIM_PRESSED(1)
#define LIM_S_PRESSED LIM_PRESSED(2)
#define LIM_E_PRESSED LIM_PRESSED(3)
#define LIM_W_PRESSED LIM_PRESSED(4)

#define LIM_N 9
#define LIM_S 10
#define LIM_E 11
#define LIM_W 12

#define WEST LOW
#define EAST HIGH
#define NORTH HIGH
#define SOUTH LOW

#define DEBUG 13

volatile byte on_mask  = 0b00000000;
volatile byte off_mask = 0b11111111;

void setup() {

pinMode(ENABLE_N, OUTPUT);
pinMode(DEBUG, OUTPUT);
  
pinMode(STEP_X, OUTPUT);
pinMode(STEP_Y1, OUTPUT);
pinMode(STEP_Y2, OUTPUT);
  
pinMode(DIR_X, OUTPUT);
pinMode(DIR_Y1, OUTPUT);
pinMode(DIR_Y2, OUTPUT);
  
pinMode(LIM_N, INPUT_PULLUP);
pinMode(LIM_S, INPUT_PULLUP);
pinMode(LIM_E, INPUT_PULLUP);
pinMode(LIM_W, INPUT_PULLUP);

digitalWrite(ENABLE_N, LOW);
digitalWrite(DEBUG, LOW);

digitalWrite(DIR_X, NORTH);
digitalWrite(DIR_Y1, EAST);
digitalWrite(DIR_Y2, EAST);

digitalWrite(STEP_X, LOW);
digitalWrite(STEP_Y1, LOW);
digitalWrite(STEP_Y2, LOW);

cli();//stop interrupts
//set timer1 interrupt at 1Hz
TCCR1A = 0;// set entire TCCR1A register to 0
TCCR1B = 0;// same for TCCR1B
TCNT1  = 0;//initialize counter value to 0
// set compare match register for 1hz increments
// OCR1A = 532;// = (16*10^6) / (30e3) - 1 (must be <65536)
OCR1A = 16000;// = (16*10^6) / (30e3) - 1 (must be <65536)
// turn on CTC mode
TCCR1B |= (1 << WGM12);
// Set CS10 and CS12 bits for 1x prescaler
// https://arduinodiy.wordpress.com/2012/02/28/timer-interrupts/
TCCR1B |= (1 << CS10);  
// enable timer compare interrupt
TIMSK1 |= (1 << OCIE1A);
sei();

Serial.begin(9600); 

}

void loop() {
  byte incomingByte;
  if (Serial.available() > 0) {
    digitalWrite(DEBUG, !digitalRead(DEBUG));
    incomingByte = Serial.read(); // read the incoming byte:
    on_mask =  0b00011100;
    off_mask = 0b11100011;
    /*
      if (on_mask == 0b00000000){
        on_mask =  0b00011100;
        off_mask = 0b11100011;
      }
      else {
        on_mask =  0b00000000;
        off_mask = 0b11111111;
      }
      */
  }
}

ISR(TIMER1_COMPA_vect){
  if (LIM_N_PRESSED){
    digitalWrite(DIR_X, SOUTH);
  }
  if (LIM_S_PRESSED){
    digitalWrite(DIR_X, NORTH);
  }
  if (LIM_E_PRESSED){
    digitalWrite(DIR_Y1, WEST);
    digitalWrite(DIR_Y2, WEST);
  }
  if (LIM_W_PRESSED){
    digitalWrite(DIR_Y1, EAST);
    digitalWrite(DIR_Y2, EAST);
  }

  // Pulse high X, Y1, Y2
  PORTD |= on_mask;
  
  // 16x NOP = 1us delay
  __asm__("nop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\t"); 

  // Pulse low X, Y1, Y2
  PORTD &= off_mask;
}
