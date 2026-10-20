PEBBLE_CC ?= $(HOME)/.local/share/pebble-sdk/SDKs/current/toolchain/arm-none-eabi/bin/arm-none-eabi-gcc

.PHONY: build clean emulator

build:
	env -i HOME="$(HOME)" PATH="$(PATH)" LANG="$(LANG)" CC="$(PEBBLE_CC)" pebble build

clean:
	env -i HOME="$(HOME)" PATH="$(PATH)" LANG="$(LANG)" CC="$(PEBBLE_CC)" pebble clean

emulator: build
	pebble install --emulator emery
