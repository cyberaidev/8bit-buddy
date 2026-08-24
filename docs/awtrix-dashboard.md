# AWTRIX dashboard customisation

8bit Buddy can use AWTRIX 3 custom apps as persistent pages in the normal display rotation, while
notifications remain reserved for important transitions such as a sit/stand change.

## What is shown

- Agent pages remain persistent while the agent record is alive.
- Agent states can use a different AWTRIX icon for working, attention, complete, and error.
- Completed agents show a 100% progress bar.
- Sit/stand now has its own `8bitbuddy_sitstand` custom app.
- The sit/stand page updates once per minute with `SIT 29m` / `STAND 14m` and a countdown progress bar.
- Phase changes still beep and interrupt the rotation with a short notification.

## Add icons

AWTRIX 3 accepts either a numeric LaMetric icon ID or the filename of an icon already stored in the
`/ICONS` folder. Custom static icons should be 8x8 JPG; animated GIFs can be 8x8 or 32x8.

Upload or download the icons using the AWTRIX 3 web interface, then edit
`~/.config/8bit-buddy/config.toml`:

```toml
[icons]
running = "working"
attention = "attention"
complete = "complete"
error = "error"
sitting = "sit"
standing = "stand"
```

The values above are filenames without `.gif` or `.jpg`. They can instead be numeric icon IDs.
Leaving a value empty disables the icon for that state.

Suggested custom filenames are:

- `working.gif` - animated robot or activity indicator
- `attention.gif` - warning / user-input indicator
- `complete.gif` - green check
- `error.gif` - error indicator
- `sit.gif` - chair / seated person
- `stand.gif` - standing / stretch animation

## App rotation

AWTRIX 3 automatically adds CustomApps to its normal app loop. The exact placement can also be set
with the AWTRIX 3 `pos` field when a CustomApp is first pushed. 8bit Buddy currently lets AWTRIX
append its pages automatically so existing clock, date, temperature, and other pages are preserved.

The resulting rotation is typically similar to:

```text
Time -> Date -> Temperature -> 8bitbuddy_sitstand -> agent pages -> Time
```

Notifications are intentionally separate from the loop. `STAND UP - 15 MIN`, `SIT DOWN - 30 MIN`,
and urgent agent states can temporarily interrupt the current page without removing the persistent
status pages.
