COMPONENT=SensingBaseAppC
#CFLAGS += -I.. -I../universal_sensors
CFLAGS += -DLOW_POWER_LISTENING
CFLAGS += -I.. -I../tmote_onboard_sensors
CFLAGS += -DCC1K_DEFAULT_FREQ=CC1K_914_077_MHZ

TINYOS_ROOT_DIR?=../../../..
PRINTFDIR = $(TINYOS_ROOT_DIR)/tos/lib/printf
CFLAGS +=  -I$(PRINTFDIR)

include $(TINYOS_ROOT_DIR)/Makefile.include
