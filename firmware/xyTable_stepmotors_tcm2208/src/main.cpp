#include <Arduino.h>
#include "math.h"
#include "BasicStepperDriver.h"
#include "MultiDriver.h"
#include "SyncDriver.h"
#include <Complex.h>
#include <watchdog.h>

#define MY_EN_PIN           10 // Enable
#define MY_STEP_PIN        9 // Step
#define MY_DIR_PIN          8 // Direction

#define MY_MOTOR_STEPS 200
#define MY_RPM 1200 
#define MY_MICROSTEPS 5 //16 microstep

#define MY_MMPR    40.0//mm per rotation
#define MY_MM2DEGREE(mm)   (float)16.0*360.0/MY_MMPR*mm //16 for microstep
#define MY_ROTATION(rot)  (float)16.0*rot
BasicStepperDriver MY_stepper(MY_MOTOR_STEPS, MY_DIR_PIN, MY_STEP_PIN,MY_EN_PIN);


#define MX_EN_PIN           13 // Enable
#define MX_STEP_PIN        12 // Step
#define MX_DIR_PIN          11 // Direction

#define MX_MOTOR_STEPS 200
#define MX_RPM 1200 
#define MX_MICROSTEPS 5 //16 microstep

#define MX_MMPR    40.0//mm per rotation
#define MX_MM2DEGREE(mm)   (float)16.0*360.0/MX_MMPR*mm //16 for microstep
#define MX_ROTATION(rot)  (float)16.0*rot
BasicStepperDriver MX_stepper(MX_MOTOR_STEPS, MX_DIR_PIN, MX_STEP_PIN,MX_EN_PIN);
SyncDriver MXMY_stepper(MX_stepper, MY_stepper);


Complex localPostion(0,0);
Complex globalPosition(0,0);
uint32_t  mili=0;

void generateCenterCells(Complex *displacment,Complex ncells,Complex pitch,Complex offsets)
{
    // float dir_x=1.0,dir_y=1.0;  
    // float y_displacment;  
    // for(uint8_t ny=0;ny<ncells.imag();ny++)
    // {
    //     y_displacment=ny*pitch.imag();
    //     for(uint8_t nx=0;nx<ncells.real();nx++)
    //     {
    //         displacment[nx,ny].set(pitch.real()*dir_x,y_displacment);
    //     }
    //     dir_x*=-1.0;
    // }
}
void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  Serial.setTimeout(500000);
//   delay(2000);
  Serial.print("==============ACAM===============\n");
  Serial.print("=========X-Y table Driver========\n");

  pinMode(MY_EN_PIN,OUTPUT);
  digitalWrite(MY_EN_PIN,0);
  MY_stepper.setEnableActiveState(LOW);
  MY_stepper.begin(MY_RPM,MY_MICROSTEPS);
  MY_stepper.enable();  
  MY_stepper.startRotate(0);

  pinMode(MX_EN_PIN,OUTPUT);
  digitalWrite(MX_EN_PIN,0);
  MX_stepper.setEnableActiveState(LOW);
  MX_stepper.begin(MY_RPM,MY_MICROSTEPS);
  MX_stepper.enable();  
  MX_stepper.startRotate(0);
  Serial.print("@wakeup\n");
  Serial.flush();
}
bool continuous_stepper = false;
float x_arg,y_arg;
int x_ncell,y_ncell,x_cntcell=0,y_cntcell=0;
float x_pitch,y_pitch,x_offset,y_offset,direction=1.0;
int capturedelay=500;
bool captureprofile=true;
int state_profile=0;
bool  profile_isrunning=false;

void loop() {
    unsigned wait_time_micros = MXMY_stepper.nextAction();          
    if(Serial.available()>0)
    {
        int deliminator[10];
        String serialstr=Serial.readStringUntil('\n');
        deliminator[0]=serialstr.indexOf(',');
        if(deliminator[0]==-1)
            deliminator[0]=serialstr.length();
        String cmd=serialstr.substring(0,deliminator[0]);
        if(cmd.endsWith("\r"))
            cmd=cmd.substring(0,cmd.indexOf('\r'));
        // Serial.print(serialstr);
        if(cmd=="reset")
        {
            Serial.flush();
            Serial.println("Start ACAM");
            continuous_stepper = false;
            captureprofile=true;
            profile_isrunning=false;
        }
        else if( cmd=="setzero")
        {
            globalPosition.set(0,0);
            Serial.print("@position,"+String(globalPosition.real())+","+String(globalPosition.imag())+"\n");            
        }
       else if(cmd=="mov2zero")
       {
            // Serial.println("mov2zero");
            // Serial.println("move to zero:"+String(localPostion.real())+","+String(localPostion.imag()));
            MXMY_stepper.startRotate(MX_MM2DEGREE(-globalPosition.real()),MY_MM2DEGREE(-globalPosition.imag()));
            localPostion.set(-globalPosition.real(),-globalPosition.imag());
            globalPosition=globalPosition+localPostion;
            Serial.print("@position,"+String(globalPosition.real())+","+String(globalPosition.imag())+"\n");            
       }
       else if(cmd=="movxy")
        {
            deliminator[1]=serialstr.indexOf(",",deliminator[0]+1);
            deliminator[2]=serialstr.indexOf(",",deliminator[1]+1);
            float Arg1=serialstr.substring(deliminator[0]+1,deliminator[1]).toFloat();
            float Arg2=serialstr.substring(deliminator[1]+1,deliminator[2]).toFloat();
            MX_stepper.startRotate(MX_MM2DEGREE(Arg1));
            MY_stepper.startRotate(MY_MM2DEGREE(Arg2));
            localPostion.set(Arg1,Arg2);
            globalPosition=globalPosition+localPostion;
            Serial.print("@position,"+String(globalPosition.real())+","+String(globalPosition.imag())+"\n");            

        }
        else if(cmd=="movcxy")
        {
            continuous_stepper=true;
            deliminator[1]=serialstr.indexOf(",",deliminator[0]+1);
            deliminator[2]=serialstr.indexOf(",",deliminator[1]+1);
            x_arg=serialstr.substring(deliminator[0]+1,deliminator[1]).toFloat();
            y_arg=serialstr.substring(deliminator[1]+1,deliminator[2]).toFloat();
            MXMY_stepper.startRotate(MX_MM2DEGREE(0),MY_MM2DEGREE(0));
        }
        else if(cmd=="rampxy")
        {
            deliminator[1]=serialstr.indexOf(",",deliminator[0]+1);
            deliminator[2]=serialstr.indexOf(",",deliminator[1]+1);
            float Arg1=serialstr.substring(deliminator[0]+1,deliminator[1]).toFloat();
            float Arg2=serialstr.substring(deliminator[1]+1,deliminator[2]).toFloat();
            MXMY_stepper.startRotate(MX_MM2DEGREE(Arg1),MY_MM2DEGREE(Arg2));
            localPostion.set(Arg1,Arg2);
            globalPosition=globalPosition+localPostion;
            Serial.print("@position,"+String(globalPosition.real())+","+String(globalPosition.imag())+"\n");            
  
        } 
        else if(cmd=="profile")
        {
            profile_isrunning=true;
            state_profile=0;
            deliminator[1]=serialstr.indexOf(",",deliminator[0]+1);
            deliminator[2]=serialstr.indexOf(",",deliminator[1]+1);            
            deliminator[3]=serialstr.indexOf(",",deliminator[2]+1);            
            deliminator[4]=serialstr.indexOf(",",deliminator[3]+1);            
            deliminator[5]=serialstr.indexOf(",",deliminator[4]+1);
            deliminator[6]=serialstr.indexOf(",",deliminator[5]+1);
            deliminator[7]=serialstr.indexOf(",",deliminator[6]+1);
            deliminator[8]=serialstr.indexOf(",",deliminator[7]+1);

            x_ncell= serialstr.substring(deliminator[0]+1,deliminator[1]).toInt();           
            x_pitch= serialstr.substring(deliminator[1]+1,deliminator[2]).toFloat();           
            x_offset= serialstr.substring(deliminator[2]+1,deliminator[3]).toFloat();           
            y_ncell= serialstr.substring(deliminator[3]+1,deliminator[4]).toInt();           
            y_pitch= serialstr.substring(deliminator[4]+1,deliminator[5]).toFloat();           
            y_offset= serialstr.substring(deliminator[5]+1,deliminator[6]).toFloat();   
            capturedelay= serialstr.substring(deliminator[6]+1,deliminator[7]).toInt();      
            captureprofile= (bool)serialstr.substring(deliminator[7]+1,deliminator[8]).toInt();      
            Serial.println("Start profile");

        }
        else if(cmd=="resumeprofile")
        {
            profile_isrunning=true;
        }
        else if(cmd=="stopc")
        {
            MXMY_stepper.stop();
            continuous_stepper=false;
            profile_isrunning=false;
            // Serial.println("stopc shit, I am here and fck you!!!!"+String(continuous_stepper));
        }               
        else
        {
            Serial.flush();
        }        
    }
    if(continuous_stepper)
    {
            if(wait_time_micros<=0)
            {
                MXMY_stepper.startRotate(MX_MM2DEGREE(x_arg),MY_MM2DEGREE(y_arg));  
                localPostion.set(x_arg,y_arg);
                globalPosition=globalPosition+localPostion;
                Serial.print("@position,"+String(globalPosition.real())+","+String(globalPosition.imag())+"\n"); 
                delay(1);           
            }     
    }
    if(profile_isrunning)
    {
        switch(state_profile)
        {
            case 0:// move to zero position
                MXMY_stepper.startRotate(MX_MM2DEGREE(-globalPosition.real()),MY_MM2DEGREE(-globalPosition.imag()));
                state_profile=1;
                // Serial.println("==move to zero position");

            break;
            case 1: 
                if(wait_time_micros<=0)//end of movment to zero
                {
                    localPostion.set(-globalPosition.real(),-globalPosition.imag());
                    globalPosition=globalPosition+localPostion;                    
                    state_profile=2;
                    // Serial.println(">>move to zero position done!");
                    Serial.print("@position,"+String(globalPosition.real())+","+String(globalPosition.imag())+"\n");    
                    delay(50);
                }            
            break;
            case 2://move to offset
                MXMY_stepper.startRotate(MX_MM2DEGREE(x_offset),MY_MM2DEGREE(y_offset));
                state_profile=3;
            break;
            case 3:
                if(wait_time_micros<=0)//end of movment to offset
                {
                    x_cntcell=1;
                    y_cntcell=1;  
                    direction=1.0;                        
                    localPostion.set(x_offset,y_offset);
                    globalPosition=globalPosition+localPostion;                       
                    Serial.print("@position,"+String(globalPosition.real())+","+String(globalPosition.imag())+"\n");   
                    // Serial.println(">>center Cell ("+String(x_cntcell)+","+String(y_cntcell)+")");  
                    mili=millis();
                    state_profile=4;
                }
            break;
            case 4: //wait for stable offset
                if((millis()-mili)>(uint32_t)capturedelay)
                {
                    state_profile=5;
                    if(captureprofile)
                    {
                        Serial.print("@trigcapture,"+String(x_cntcell)+","+String(y_cntcell)+"\n");
                         delay(50);
                        profile_isrunning=false;
                    }
                }
            break;
            case 5:// move in X direction
                if(direction>0)
                {
                    if(x_cntcell<x_ncell)
                    {
                        MXMY_stepper.startRotate(MX_MM2DEGREE(direction*x_pitch),MY_MM2DEGREE(0));
                        state_profile=6;
                        x_cntcell++;
                        // Serial.println("==move to center Cell:("+String(x_cntcell)+","+String(y_cntcell)+")");     
                    } 
                    else{
                        state_profile=8;
                    }   
                } 
                else
                {
                    if(x_cntcell>1)
                    {
                        MXMY_stepper.startRotate(MX_MM2DEGREE(direction*x_pitch),MY_MM2DEGREE(0));
                        state_profile=6;
                        x_cntcell--;
                        // Serial.println("==move to center Cell:("+String(x_cntcell)+","+String(y_cntcell)+")");     
                    } 
                    else{
                        state_profile=8;
                    }                       
                }
            break;
            case 6:
                if(wait_time_micros<=0)//end of movment to X direction 
                {
                    localPostion.set(direction*x_pitch,0);
                    globalPosition=globalPosition+localPostion;
                    Serial.print("@position,"+String(globalPosition.real())+","+String(globalPosition.imag())+"\n");                       
                    // Serial.println(">>center Cell ("+String(x_cntcell)+","+String(y_cntcell)+")");  
                    mili=millis();
                    state_profile=7;

                }              
            break;   
            case 7: //wait for stable x
                if((millis()-mili)>(uint32_t)capturedelay)
                {
                    state_profile=5;
                    if(captureprofile)
                    {
                        Serial.print("@trigcapture,"+String(x_cntcell)+","+String(y_cntcell)+"\n");
                        delay(50);
                        profile_isrunning=false;
                    }                    
                }            
            break;
            case 8:// move in Y direction
                if(y_cntcell<y_ncell)
                {            
                    MXMY_stepper.startRotate(MX_MM2DEGREE(0),MY_MM2DEGREE(y_pitch));
                    state_profile=9;
                    y_cntcell++;
                    // Serial.println("==move to center Cell:("+String(x_cntcell)+","+String(y_cntcell)+")");      
                } 
                else
                {
                     state_profile=11;
                }   
            break;
            case 9:
                if(wait_time_micros<=0)//end of movment in y 
                {
                    localPostion.set(0,y_pitch);
                    globalPosition=globalPosition+localPostion;
                    Serial.print("@position,"+String(globalPosition.real())+","+String(globalPosition.imag())+"\n");                       
                    // Serial.println(">>center Cell ("+String(x_cntcell)+","+String(y_cntcell)+")");  
                    direction*=-1; 
                    mili=millis();                   
                    state_profile=10;

                }              
            break; 
            case 10: //wait for stable y
                if((millis()-mili)>(uint32_t)capturedelay)
                {
                    state_profile=5;
                    if(captureprofile)
                    {
                        Serial.print("@trigcapture,"+String(x_cntcell)+","+String(y_cntcell)+"\n");
                        profile_isrunning=false;
                         delay(50);
                    }                    
                }
            break;
            case 11:
                profile_isrunning=false;
                Serial.print("@endprofile\n");
            break;        

        }
    }
    
}
