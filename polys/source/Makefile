CC ?= gcc
CFLAGS ?= -g -O0
OBJCOPY ?= objcopy
OBJCOPYFLAGS ?= --strip-debug --strip-symbol=foo --strip-symbol=polys --strip-symbol=poly_degrees

TARGET = polys
ATTACHMENT ?= ../attachments/polys

all: $(TARGET)

$(TARGET): polys.c seccomp.c
	$(CC) $(CFLAGS) -o $@ polys.c
	$(OBJCOPY) $(OBJCOPYFLAGS) $@

attachment: $(TARGET)
	cp $(TARGET) $(ATTACHMENT)
	chmod 0555 $(ATTACHMENT)

clean:
	$(RM) $(TARGET)

.PHONY: all attachment clean
