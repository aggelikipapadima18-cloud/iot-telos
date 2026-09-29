GEN=SerialRequestSamplesMsg.java SerialSampleMsg.java Constants.java

#SENSOR_DIR = universal_sensors
SENSOR_DIR = tmote_onboard_sensors
SENSOR_DEPS = ../$(SENSOR_DIR)/SensorSample.h

TFLAGS = -I../$(SENSOR_DIR) -I$(TINYOS_OS_DIR)/types -I$(TINYOS_OS_DIR)/platforms/null -I$(TINYOS_OS_DIR)/lib/serial

TINYOS_OS_DIR ?= ../../../../tos

all: SensingApp.jar

SensingApp.jar: SensingApp.class
	jar cf $@ *.class

SerialRequestSamplesMsg.java: ../SensingMsgs.h $(SENSOR_DEPS)
	nescc-mig $(TFLAGS) \
		-java-classname=SerialRequestSamplesMsg java ../SensingMsgs.h serial_request_samples_msg -o $@

SerialSampleMsg.java: ../SensingMsgs.h $(SENSOR_DEPS)
	nescc-mig $(TFLAGS) \
		-java-classname=SerialSampleMsg java ../SensingMsgs.h serial_sample_msg -o $@

Constants.java: ../SensingConstants.h
	nescc-ncg $(TFLAGS) -DSENSING_JAVA_MAKEFILE \
		-java-classname=Constants java ../SensingConstants.h BASE_STATION_ADDR SAMPLING_INTERVAL \
		MSG_QUEUE_SIZE LPL_INTERVAL  -o $@

SensingApp.class: $(wildcard *.java) $(GEN)
	javac *.java

clean:
	rm -f *.class $(GEN) SensingApp.jar Constants.java SerialSampleMsg.java SerialRequestSamplesMsg.java
