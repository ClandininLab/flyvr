/* LineViewer --- scrolling window display for Arduino line scan image sensor 2010-08-01 */

import processing.serial.*;
import java.text.SimpleDateFormat;
import java.util.Date;

final int LINELEN = 128;

PImage img;
Serial duino;
boolean Synced = false;

PrintWriter output = null;

String datetime(){
  SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd-HH-mm-ss-SSS");
  Date now = new Date();
  String result = sdf.format(now);
  return result;
}

void setup ()
{
  println ("<START>");
  println (Serial.list());
  println ("<END>");

  // Open serial port to Arduino at 115200 baud
  duino = new Serial (this, "/dev/tty.usbmodem1411", 115200);
  
  // Define window size
  size (700, 700);
  
  // Image height is same as window
  img = createImage (LINELEN, height, RGB);
  
  // Initialise image to a shade of blue
  img.loadPixels ();
  
  for (int i = 0; i < img.pixels.length; i++) {
    img.pixels[i] = color (0, 90, 102); 
  }
  
  img.updatePixels ();
  
  // Choose image update rate
  frameRate (30);
}

void draw ()
{
  int i;
  int ch;
  int nbufs;
  int b;
  byte[] inbuf = new byte[LINELEN + 1];
  
  // Synchronise
  if (Synced) {
    nbufs = duino.available () / (LINELEN + 1);
  }
  else {
    do {
      while (duino.available () == 0){
        try {    
          Thread.sleep(10);
        } catch(Exception e){}
      }
        
      ch = duino.read ();
      
    } while (ch != 0);
    nbufs = 0;
    Synced = true;
  }

  // Load the image pixels in preparation for next frame(s)
  img.loadPixels ();
  
  for (b = 0; b < nbufs; b++) {
    // Scroll the old image data down the window
    for (i = img.pixels.length - LINELEN - 1; i >= 0; i--) {
      img.pixels[i + LINELEN] = img.pixels[i];
    }
    // Read 128 pixels from image sensor, via Arduino
    duino.readBytes (inbuf);
    
    // Check we're still in sync
    if (inbuf[128] != 0) {
      print ("UNSYNC ");
      Synced = false;
    }
    
    // Transfer incoming pixels to image
    String csvstr = "";
    
    for (i = 0; i < LINELEN; i++) {
      ch = inbuf[i];
      if (ch < 0)
        ch += 256;
      
        csvstr += str(ch);
      
      if (i != LINELEN - 1){
        csvstr += ", ";
      }
      
      img.pixels[i] = color (ch, ch, ch);
    }
    
    if (output != null) {
      output.println(csvstr);
    }
  }

  // We're done updating the image, so re-display it
  img.updatePixels ();
  image (img, 0, 0, width, height);
}

void keyPressed() {
  if (key == ENTER) {
    output = createWriter(datetime() + ".csv");
  } else if (keyCode == 32){
    if (output != null){
      output.flush();
      output.close();
      output = null;
    }
  }
}