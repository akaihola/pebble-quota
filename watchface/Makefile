# SDK version installed when no Pebble SDK is active. CI sets the same variable.
PEBBLE_SDK_VERSION ?= 4.33.1
PEBBLE_SDK_DIR ?= $(HOME)/.local/share/pebble-sdk/SDKs/current
PEBBLE_CC ?= $(PEBBLE_SDK_DIR)/toolchain/arm-none-eabi/bin/arm-none-eabi-gcc
PEBBLE_ENV = env -i HOME="$(HOME)" PATH="$(PATH)" LANG="$(LANG)" CC="$(PEBBLE_CC)"

.PHONY: build clean emulator sdk

build: sdk
	$(PEBBLE_ENV) pebble build

clean: sdk
	$(PEBBLE_ENV) pebble clean

emulator: build
	pebble install --emulator emery

# Install the SDK only when the active one is missing. Ignoring the user's npm
# configuration avoids npm errors that pebble-tool does not report as failures.
sdk:
	@if test -e "$(PEBBLE_SDK_DIR)/sdk-core/pebble/waf" && test -x "$(PEBBLE_SDK_DIR)/toolchain/arm-none-eabi/bin/arm-none-eabi-gcc"; then exit 0; fi; \
	echo "No active Pebble SDK found; installing SDK $(PEBBLE_SDK_VERSION)."; \
	$(PEBBLE_ENV) npm_config_userconfig=/dev/null pebble sdk install "$(PEBBLE_SDK_VERSION)" \
	&& test -e "$(PEBBLE_SDK_DIR)/sdk-core/pebble/waf" \
	&& test -x "$(PEBBLE_SDK_DIR)/toolchain/arm-none-eabi/bin/arm-none-eabi-gcc" \
	|| { echo "Pebble SDK $(PEBBLE_SDK_VERSION) installation failed; nothing was built or cleaned." >&2; exit 1; }
