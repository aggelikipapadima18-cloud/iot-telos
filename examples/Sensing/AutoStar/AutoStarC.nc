#include "printf.h"
#include "SensingConstants.h"
#include "SensorSample.h"

module AutoStarC {
  uses {
    interface Boot;
    interface Leds;
    interface SplitControl as RadioControl;
    interface AMPacket as RadioAMPacket;
    interface LatestSample<sensor_sample_t>;
    interface SampleNxConverter;
    interface Timer<TMilli> as SendTimer;
    interface Timer<TMilli> as BeaconTimer;
    interface AMSend as SampleSend;
    interface Receive as SampleReceive;
    interface AMSend as BeaconSend;
    interface Receive as BeaconReceive;
    interface Receive as RoleReceive;
  }
}
implementation {
  message_t sampleMsg;
  message_t beaconMsg;
  bool isParent = FALSE;
  bool haveParent = FALSE;
  bool sampleBusy = FALSE;
  bool beaconBusy = FALSE;
  am_addr_t parentId = AM_BROADCAST_ADDR;
  sensor_sample_t latestSample;

  event void Boot.booted() {
    call RadioControl.start();
  }

  event void RadioControl.startDone(error_t error) {
    if (error != SUCCESS) {
      call RadioControl.start();
      return;
    }
    call SendTimer.startPeriodic(SAMPLING_INTERVAL);
    call BeaconTimer.startPeriodic(3000);
  }

  event void RadioControl.stopDone(error_t error) {}

  event message_t* RoleReceive.receive(message_t* msg, void* payload, uint8_t len) {
    role_start_msg_t* roleMsg = payload;
    if (len == sizeof(role_start_msg_t) && roleMsg->start == 1) {
      isParent = TRUE;
      haveParent = TRUE;
      parentId = TOS_NODE_ID;
      call Leds.led1On();
      printf("role=parent id=%u\n", (unsigned int)TOS_NODE_ID);
      printfflush();
    }
    return msg;
  }

  event void BeaconTimer.fired() {
    parent_beacon_msg_t* beacon;
    if (!isParent || beaconBusy) return;
    beacon = call BeaconSend.getPayload(&beaconMsg, sizeof(parent_beacon_msg_t));
    if (beacon == NULL) return;
    beacon->parent_id = TOS_NODE_ID;
    if (call BeaconSend.send(AM_BROADCAST_ADDR, &beaconMsg,
                             sizeof(parent_beacon_msg_t)) == SUCCESS)
      beaconBusy = TRUE;
  }

  event void BeaconSend.sendDone(message_t* msg, error_t error) {
    beaconBusy = FALSE;
  }

  event message_t* BeaconReceive.receive(message_t* msg, void* payload, uint8_t len) {
    parent_beacon_msg_t* beacon = payload;
    if (!isParent && len == sizeof(parent_beacon_msg_t)
        && beacon->parent_id == call RadioAMPacket.source(msg)) {
      parentId = beacon->parent_id;
      haveParent = TRUE;
      call Leds.led1On();
    }
    return msg;
  }

  event void SendTimer.fired() {
    nx_sensor_sample_t* nxSample;
    if (isParent || !haveParent || sampleBusy) return;
    call Leds.led0Toggle();
    if (call LatestSample.get(&latestSample) != SUCCESS) return;
    nxSample = call SampleSend.getPayload(&sampleMsg, sizeof(nx_sensor_sample_t));
    if (nxSample == NULL) return;
    call SampleNxConverter.copyToNx(nxSample, &latestSample);
    if (call SampleSend.send(parentId, &sampleMsg,
                             sizeof(nx_sensor_sample_t)) == SUCCESS)
      sampleBusy = TRUE;
  }

  event void SampleSend.sendDone(message_t* msg, error_t error) {
    sampleBusy = FALSE;
  }

  event message_t* SampleReceive.receive(message_t* msg, void* payload, uint8_t len) {
    nx_sensor_sample_t* sample = payload;
    if (isParent && len == sizeof(nx_sensor_sample_t)) {
      call Leds.led2Toggle();
      printf("parent=%u src=%u " SENSOR_SAMPLE_PRINTF_FORMAT "\n",
        (unsigned int)TOS_NODE_ID,
        (unsigned int)call RadioAMPacket.source(msg),
        SENSOR_SAMPLE_PRINTF_ARGS((*sample)));
      printfflush();
    }
    return msg;
  }
}
