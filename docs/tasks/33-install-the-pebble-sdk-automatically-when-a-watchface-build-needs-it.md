# Install the Pebble SDK when a build needs it

The watchface build should work after the SDK has been removed from Tinni, freeing its disk until another build needs the SDK. Add a simple automatic installation of the required Pebble SDK when absent, then remove the installed SDK from agent@tinni after the automatic reinstall has been verified. Preserve emulator state, settings and unrelated data.

On 2026-11-13, Pebble tool 5.0.40 installed SDK 4.17 twice into isolated homes. The first returned success despite an npm configuration error. The second used npm_config_userconfig=/dev/null and successfully built a copied watchface under nix-shell. Verify a missing-SDK build actually reinstalls and builds, handles failures visibly, and preserves existing builds. Check which exact SDK files and links are removed and report actual disk space recovered. Network access and license terms may be required.
