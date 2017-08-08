// Arduino pin assignments
#define STEP_X 2
#define STEP_Y1 3
#define STEP_Y2 4
#define DIR_X 5
#define DIR_Y1 6
#define DIR_Y2 7
#define ENABLE_N 8
#define LIM_N 9
#define LIM_S 10
#define LIM_E 11
#define LIM_W 12
#define DEBUG 13

#define X_MASK 0b00000100
#define Y_MASK 0b00011000

#define LIM_PRESSED(v) (((PINB>>(v-8))&0x01)==0x00)
#define LIM_N_PRESSED LIM_PRESSED(LIM_N)
#define LIM_S_PRESSED LIM_PRESSED(LIM_S)
#define LIM_E_PRESSED LIM_PRESSED(LIM_E)
#define LIM_W_PRESSED LIM_PRESSED(LIM_W)

#define NORTH true
#define SOUTH false
#define EAST true
#define WEST false

#define N_MASK 0b00100000
#define S_MASK 0b11011111
#define E_MASK 0b11000000
#define W_MASK 0b00111111

#define STEP_OVFL 0x7FFF

#define IN_BUF_LEN 4
#define OUT_BUF_LEN 7

void serialSetup() {
  Serial.begin(9600);
}

void pinSetup() {
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
}

void setTimerFrequency(long hz){
  OCR1A = 16000000/hz - 1;
}

void timerSetup() {
  //set timer1 interrupt at 1Hz
  TCCR1A = 0;// set entire TCCR1A register to 0
  TCCR1B = 0;// same for TCCR1B
  TCNT1  = 0;//initialize counter value to 0
  // set the timer frequency
  setTimerFrequency(30000);
  // turn on CTC mode
  TCCR1B |= (1 << WGM12);
  // Set CS10 and CS12 bits for 1x prescaler
  // https://arduinodiy.wordpress.com/2012/02/28/timer-interrupts/
  TCCR1B |= (1 << CS10);  
  // enable timer compare interrupt
  TIMSK1 |= (1 << OCIE1A);
}

void debug(bool value){
  if (value) {
    digitalWrite(DEBUG, HIGH);
  } else {
    digitalWrite(DEBUG, LOW);
  }
}

void setup() {
  pinSetup();
  timerSetup(); 
  serialSetup();
}

bool shouldRun = false;

volatile unsigned int alphaX = 0;
volatile unsigned int alphaY = 0;

volatile bool dirX = false;
volatile bool dirY = false;

byte inBuf[IN_BUF_LEN];
byte outBuf[OUT_BUF_LEN];

volatile long xsteps = 0;
volatile long ysteps = 0;

void loop() {
  if (Serial.available() > 0) {
    Serial.readBytes(inBuf, IN_BUF_LEN);
    
    noInterrupts();
    
    // read in the dirX value
    dirX = ((inBuf[0] >> 7) & 0x01);
    if (dirX){
      PORTD |= N_MASK;
    } else {
      PORTD &= S_MASK;
    }
    
    // read in the alphaX value
    alphaX = inBuf[0] & 0x7F;
    alphaX <<= 8;
    alphaX |= inBuf[1];

    // read in the dirY value
    dirY = ((inBuf[2] >> 7) & 0x01);
    if (dirY){
      PORTD |= E_MASK;
    } else {
      PORTD &= W_MASK;
    }

    // read in the alphaY value
    alphaY = inBuf[2] & 0x7F;
    alphaY <<= 8;
    alphaY |= inBuf[3];

    // create the output buffer

    // save the pin state of the limit switches
    outBuf[0] = PINB;

    // save the number of steps along the X axis
    outBuf[1] = xsteps >> 16;
    outBuf[2] = xsteps >> 8;
    outBuf[3] = xsteps;

    // save the number of steps along the Y axis
    outBuf[4] = ysteps >> 16;
    outBuf[5] = ysteps >> 8;
    outBuf[6] = ysteps;
    
    interrupts();

    // send the output buffer
    Serial.write(outBuf, OUT_BUF_LEN);
  }
}

unsigned int xcount = 0;
unsigned int ycount = 0;

ISR(TIMER1_COMPA_vect){
  // Build up mask used for the motor control
  byte mask = 0x00;
  
  // Determine whether the X-axis should increment
  if (!((dirX && LIM_N_PRESSED) || (!dirX && LIM_S_PRESSED))){
    if (xcount >= STEP_OVFL){
      xcount -= STEP_OVFL;
      mask |= X_MASK;
      if (dirX) {
        xsteps += 1;
      } else {
        xsteps -= 1;
      }
    }
    xcount += alphaX;
  }

  // Determine whether the Y-axis should increment
  if (!((dirY && LIM_E_PRESSED) || (!dirY && LIM_W_PRESSED))){
    if (ycount >= STEP_OVFL){
      ycount -= STEP_OVFL;
      mask |= Y_MASK;
      if (dirY) {
        ysteps += 1;
      } else {
        ysteps -= 1;
      }
    }
    ycount += alphaY;
  }

  // Pulse high X, Y1, Y2
  PORTD |= mask;
  
  // 16x NOP = 1us delay
  __asm__("nop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\tnop\n\t"); 

  // Pulse low X, Y1, Y2
  PORTD &= ~mask;
}
