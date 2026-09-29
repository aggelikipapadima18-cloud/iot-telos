#define NEW_PRINTF_SEMANTICS
#include "printf.h"
#include "SensingConstants.h"

configuration AutoStarAppC {}
implementation {
  components MainC, AutoStarC as App, LedsC;
  components PrintfC, SerialStartC;
  components ActiveMessageC as Radio;
  components new SamplePeriodicLogC(SAMPLING_INTERVAL, VOLUME_SENSOR_SAMPLES);
  components SampleNxConverterC;
  components new TimerMilliC() as SendTimer;
  components new TimerMilliC() as BeaconTimer;
  components new AMSenderC(AM_SAMPLE_MSG) as SampleSender;
  components new AMReceiverC(AM_SAMPLE_MSG) as SampleReceiver;
  components new AMSenderC(AM_PARENT_BEACON_MSG) as BeaconSender;
  components new AMReceiverC(AM_PARENT_BEACON_MSG) as BeaconReceiver;
  components new SerialAMReceiverC(AM_ROLE_START_MSG) as RoleReceiver;

  MainC.Boot <- App;
  App.Leds -> LedsC;
  App.RadioControl -> Radio;
  App.RadioAMPacket -> Radio;
  App.LatestSample -> SamplePeriodicLogC;
  App.SampleNxConverter -> SampleNxConverterC;
  App.SendTimer -> SendTimer;
  App.BeaconTimer -> BeaconTimer;
  App.SampleSend -> SampleSender;
  App.SampleReceive -> SampleReceiver;
  App.BeaconSend -> BeaconSender;
  App.BeaconReceive -> BeaconReceiver;
  App.RoleReceive -> RoleReceiver;
}
