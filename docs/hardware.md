# Hardware and flashing

## Best fit: Ulanzi TC001

The recommended device is the
[Ulanzi TC001 Smart Pixel Clock](https://www.ulanzi.com/en-au/products/ulanzi-pixel-smart-clock-2882).
It is an 8 × 32 RGB LED matrix measuring 200.6 × 70.3 × 31.9 mm. That makes it narrow enough for
the top of a monitor or the space behind a keyboard while still leaving enough pixels for a short
name and scrolling status.

The display is a better fit than a 5- or 7-inch HDMI screen for this project because it needs only
USB-C power. Agent updates travel from the Mac over the local network. Its internal battery is useful
for short moves or interruptions, but Ulanzi recommends leaving it powered for normal daily use.

## Bill of materials

| Item | Required | Notes |
| --- | --- | --- |
| Ulanzi TC001 | Yes | Model 2882, 256-pixel RGB matrix |
| USB-C cable and 5 V / 1 A power | Yes | A cable is normally included; use continuous power |
| Mac with Python 3.11+ | Yes | Apple Silicon and Intel are supported |
| Reachable local Wi-Fi | Yes | The Mac must be able to reach the display's IP |
| Thin non-slip pad or monitor shelf | Optional | Useful if placed above the monitor |

## Flash AWTRIX 3 from macOS

AWTRIX 3 is open-source ESP32 firmware and provides the local HTTP custom-app API used by 8bit
Buddy. Flashing replaces Ulanzi's stock firmware.

1. Connect the TC001 to the Mac with a **data-capable** USB-C cable.
2. Open the [AWTRIX 3 online flasher](https://blueforcer.github.io/awtrix3/#/flasher) in Google
   Chrome or Microsoft Edge. The official flasher uses browser serial support and does not list
   Safari.
3. For the first flash of a Ulanzi clock, select **erase**.
4. After flashing, connect the Mac to the `awtrix_XXXXX` access point. The documented initial
   password is `12345678`.
5. Open `http://192.168.4.1`, enter the Wi-Fi details, and wait for the clock to join the network.
6. Note the IP address shown during connection. Reserve it in the router if possible so the 8bit
   Buddy configuration remains stable.
7. Confirm the API from the Mac:

   ```bash
   curl http://192.168.1.5/api/stats
   ```

8. Configure 8bit Buddy for this TC001:

   ```bash
   8bit-buddy configure --display-host 192.168.1.5
   ```

The official [AWTRIX quick start](https://github.com/Blueforcer/awtrix3/blob/main/docs/quickstart.md)
and [HTTP API reference](https://github.com/Blueforcer/awtrix3/blob/main/docs/api.md) remain the
source of truth if the firmware changes.

## Placement

- Above a monitor: use a shallow monitor shelf or a thin removable strip rated for the device's
  weight. Keep the light sensor unobstructed.
- Next to a keyboard: angle it slightly upward and reduce brightness in the AWTRIX settings.
- Avoid full-white mood-light modes at high brightness; a dense matrix draws more current and can
  generate additional heat.

## Alternatives

A self-built ESP32 plus 32 × 8 WS2812B matrix can also run AWTRIX 3, but it needs a case, diffuser,
power design, and firmware pin configuration. The TC001 is the recommended first version because it
is finished, compact, and has a widely used AWTRIX target profile.
