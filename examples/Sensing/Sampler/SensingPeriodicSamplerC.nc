/*
 * Copyright (c) 2007 Stanford University.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * - Redistributions of source code must retain the above copyright
 *   notice, this list of conditions and the following disclaimer.
 * - Redistributions in binary form must reproduce the above copyright
 *   notice, this list of conditions and the following disclaimer in the
 *   documentation and/or other materials provided with the
 *   distribution.
 * - Neither the name of the Stanford University nor the names of
 *   its contributors may be used to endorse or promote products derived
 *   from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 * FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL STANFORD
 * UNIVERSITY OR ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 * STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
 * OF THE POSSIBILITY OF SUCH DAMAGE.
 */

/**
 * @author Kevin Klues <klueska@cs.stanford.edu>
 * @date July 24, 2007
 */

#include "SensingConstants.h"
#include "SensorSample.h"
module SensingPeriodicSamplerC {
  uses {
    interface Boot;
    interface LatestSample<sensor_sample_t>;
    interface SampleNxConverter;
    interface Timer<TMilli> as SendTimer;
    interface Leds;
    interface SplitControl as AMControl;
    interface AMSend as SampleSend;
  }
}
implementation {
  message_t sample_msg;
  sensor_sample_t latest_sample;
  bool sendBusy = FALSE;

  task void sendSampleMsgTask();

  void sendLatestSample() {
    nx_sensor_sample_t* nx_sample;

    if(sendBusy == TRUE)
      return;

    if(call LatestSample.get(&latest_sample) != SUCCESS)
      return;

    nx_sample = call SampleSend.getPayload(&sample_msg, sizeof(nx_sensor_sample_t));
    if(nx_sample == NULL)
      return;

    call SampleNxConverter.copyToNx(nx_sample, &latest_sample);

    if(call SampleSend.send(BASE_STATION_ADDR, &sample_msg, sizeof(nx_sensor_sample_t)) == SUCCESS) {
      sendBusy = TRUE;
      call Leds.led2On();
    }
  }

  task void sendSampleMsgTask() {
    sendLatestSample();
  }
	
  event void Boot.booted() {
    call AMControl.start();
  }
  
  event void AMControl.startDone(error_t e) {
  	if(e != SUCCESS)
  		call AMControl.start();
    else
      call SendTimer.startPeriodic(SAMPLING_INTERVAL);
  }
  
  event void AMControl.stopDone(error_t e) {
  }

  event void SendTimer.fired() {
    call Leds.led0Toggle();
    post sendSampleMsgTask();
  }

  event void SampleSend.sendDone(message_t* msg, error_t error) {
    call Leds.led2Off();

    if(error != SUCCESS) {
      sendBusy = FALSE;
      post sendSampleMsgTask();
    }

    sendBusy = FALSE;
  }
}
