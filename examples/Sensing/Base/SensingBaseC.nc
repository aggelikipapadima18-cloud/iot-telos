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
 
#include "printf.h"
#include "SensingConstants.h"
module SensingBaseC {
  uses {
    interface Boot;
    interface Leds;

    interface SplitControl as RadioAMControl;
    interface AMPacket as RadioAMPacket;
    interface Receive as RadioSampleMsgReceive;
  }
}
implementation {
  event void Boot.booted() {
    call RadioAMControl.start();
  }
  
  event void RadioAMControl.startDone(error_t error) {
    if(error != SUCCESS)
      call RadioAMControl.start();
  }

  event void RadioAMControl.stopDone(error_t error) {
  }

  event message_t* RadioSampleMsgReceive.receive(message_t* msg, void* payload, uint8_t len) {
    nx_sensor_sample_t* sample = payload;

    call Leds.led2Toggle();

    if(len == sizeof(nx_sensor_sample_t)) {
      printf(
        "parent=%u src=%u " SENSOR_SAMPLE_PRINTF_FORMAT "\n",
        (unsigned int)TOS_NODE_ID,
        (unsigned int)call RadioAMPacket.source(msg),
        SENSOR_SAMPLE_PRINTF_ARGS((*sample))
      );
    }
    else {
      printf(
        "parent=%u src=%u invalid_len=%u\n",
        (unsigned int)TOS_NODE_ID,
        (unsigned int)call RadioAMPacket.source(msg),
        (unsigned int)len
      );
    }

    printfflush();
    return msg;
  }
}

