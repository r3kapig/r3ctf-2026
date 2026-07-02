CC ?= gcc
CFLAGS ?= -g -O0
OBJCOPY ?= objcopy
OBJCOPYFLAGS ?= --strip-debug --strip-symbol=foo --strip-symbol=ploys --strip-symbol=ploy_degrees

TARGET = ploys
ATTACHMENT ?= ../attachments/ploys

all: $(TARGET)

$(TARGET): ploys.c seccomp.c
	$(CC) $(CFLAGS) -o $@ ploys.c
	$(OBJCOPY) $(OBJCOPYFLAGS) $@

attachment: $(TARGET)
	cp $(TARGET) $(ATTACHMENT)
	chmod 0555 $(ATTACHMENT)

clean:
	$(RM) $(TARGET)

.PHONY: all attachment clean
