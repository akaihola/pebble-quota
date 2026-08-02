PEBBLE_CC ?= $(HOME)/.local/share/pebble-sdk/SDKs/current/toolchain/arm-none-eabi/bin/arm-none-eabi-gcc

.PHONY: build clean emulator

build:
	CC=$(PEBBLE_CC) pebble build

clean:
	CC=$(PEBBLE_CC) pebble clean

emulator: build
	pebble install --emulator emery
