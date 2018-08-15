/* LineCam --- Taos TSL1401 image sensor chip line-scan camera 2010-07-24 */

#include <avr/io.h>

#define AOpin 0  // Analog pin 0

// Arduino pin numbers
#define CLKpin 2  // Port D, bit 2
#define SIpin 3   // Port D, bit 3

#define NPIXELS 128

byte Pixel[NPIXELS];
long int Exposure;
unsigned int Before, After;
int gate;
int solenoidPin = 12;
//int incomingByte = 0;

void setup (void)
{
  int junk;
  
  pinMode (SIpin, OUTPUT);
  pinMode (CLKpin, OUTPUT);
  //pinMode(LED_BUILTIN, OUTPUT);
  pinMode(solenoidPin, OUTPUT);
  //pinMode (AOpin, INPUT);
  
  digitalWrite (SIpin, LOW);
  digitalWrite (CLKpin, HIGH);
  
  Exposure = 10000L;
  
  // Dummy read of analog pin to initialise converter
  junk = analogRead (AOpin);
  
  // Set ADC output to left-adjusted
  ADMUX |= (1<<ADLAR);
  
  // Set analog converter to divide-by-16 clock
  setAnalogPrescaler (4);
  
  Serial.begin (115200); //115200
}


void loop (){
  
  gate = Serial.read();
  //Serial.print("I received: ");
  //Serial.println(incomingByte, DEC);
  
  if (gate == 1)
  digitalWrite(solenoidPin, HIGH);
  
  else if (gate == 0)
  digitalWrite(solenoidPin, LOW);

  int i;
  // Make an exposure
  SensorExposeUs (Exposure);

  for (i = 0; i < NPIXELS; i++) {
    if (Pixel[i] == 0)
      Serial.write ((byte)1);
    else
      Serial.write ((byte)Pixel[i]);
  }
  Serial.write((byte)0);
  
  // Limit frame date by adding delay if required
  if (Exposure < 16000L) {
    delayMicroseconds ((int)16384L - Exposure);
  }
}

/* SensorExposeUs --- make an exposure of known duration */

void SensorExposeUs (long int us)
{
  int i;

  DummyReadSensor ();
  if (us > 770L)
    lDelayUs (us - 770L);
  //Before = millis ();
  RawReadSensor ();
  //After = millis ();
}

/* lDelayUs --- delay for long int microseconds */

void lDelayUs (long int us)
{
  if (us < 10000L)
    delayMicroseconds ((int)us);
  else
    delay ((int)(us / 1000L));
}

/* RawReadSensor --- read 128 pixels from sensor, directly */

void RawReadSensor (void)
{
  int i;
  uint8_t low, high;
  
  digitalWrite (CLKpin, LOW);
  delayMicroseconds (1);
  digitalWrite (SIpin, HIGH);
  digitalWrite (CLKpin, HIGH);
  digitalWrite (SIpin, LOW);
  
  for (i = 0; i < NPIXELS; i++) {
    ADCSRA |= (1 << ADSC);   // Start conversion

    // ADSC is cleared when the conversion finishes
    while (bit_is_set (ADCSRA, ADSC))
      ;

    // digitalWrite (CLKpin, LOW);
    PORTD &= ~(1<<2);
    
    // we have to read ADCL first; doing so locks both ADCL
    // and ADCH until ADCH is read.  reading ADCL second would
    // cause the results of each conversion to be discarded,
    // as ADCL and ADCH would be locked when it completed.
    low = ADCL;
    high = ADCH;

    Pixel[i] = high;
    //Pixel[i] = ((high << 8) | low) / 4;
    //Pixel[i] = analogRead (AOpin) / 4;

    __asm__ __volatile__ ("nop;nop;nop;nop");
    PORTD |= (1<<2);
    // digitalWrite (CLKpin, HIGH);
  }
  
  delayMicroseconds (1);
}


/* DummyReadSensor --- clock the sensor 128 times, but no ADC */

void DummyReadSensor (void)
{
  int i;
  
  digitalWrite (CLKpin, LOW);
  delayMicroseconds (1);
  digitalWrite (SIpin, HIGH);
  digitalWrite (CLKpin, HIGH);
  digitalWrite (SIpin, LOW);
  
  // Quickly pulse the clock pin 128 times
  for (i = 0; i < NPIXELS; i++) {
    //digitalWrite (CLKpin, LOW);
    PORTD &= ~(1<<2);
    __asm__ __volatile__ ("nop;nop;nop;nop");
    //digitalWrite (CLKpin, HIGH);
    PORTD |= (1<<2);
    __asm__ __volatile__ ("nop;nop;nop;nop");
  }
  
  delayMicroseconds (1);
}

void setAnalogPrescaler (int div)
{
  uint8_t bits = 0;
  
  switch (div) {
  case 2:
    bits = (1<<ADPS0);
    break;
  case 4:
    bits = (1<<ADPS1);
    break;
  case 8:
    bits = (1<<ADPS1) | (1<<ADPS0);
    break;
  case 16:
    bits = (1<<ADPS2);
    break;
  case 32:
    bits = (1<<ADPS2) | (1<<ADPS0);
    break;
  case 64:
    bits = (1<<ADPS2) | (1<<ADPS1);
    break;
  case 128:
  default:
    bits = (1<<ADPS2) | (1<<ADPS1) | (1<<ADPS0);
    break;
  }
  
  ADCSRA &= ~((1<<ADPS2) | (1<<ADPS1) | (1<<ADPS0));
  ADCSRA |= bits;
}

