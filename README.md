# peripad-mac-fix

A tiny userspace driver that makes a PeriPad touchpad (USB `258a:000c`) behave
on macOS: one finger moves the cursor, two fingers scroll.

It reads raw HID input reports straight from the device via IOKit and posts
synthetic mouse/scroll events through Quartz — no kernel extension required.

## Requirements

- macOS
- Python 3 with [`pyobjc`](https://pypi.org/project/pyobjc/) (`pip install pyobjc`)

## Usage

```bash
sudo python3 mouse.py
```

`sudo` is needed to open the HID device. Press `ctrl-c` to stop.

## Tuning

Edit the constants near the top of `mouse.py`:

| Constant             | Effect                                              |
| -------------------- | --------------------------------------------------- |
| `SENSITIVITY`        | Cursor speed (one finger)                           |
| `SCROLL_SENSITIVITY` | Scroll speed (two fingers)                          |
| `SCROLL_NATURAL`     | `True` = content follows fingers; `False` to invert |
| `LIFT_TIMEOUT`       | Seconds of silence before a touch is treated as new |

## Debugging

Run with `DEBUG=1` to print every raw HID frame, useful if the device's report
format differs from what's documented in `mouse.py`:

```bash
DEBUG=1 python3 mouse.py
```

## How it works

The device sends report id `7` as 8 bytes:
`[id, x_lo, x_hi, y_lo, y_hi, 00, 00, flag]`. It reports one contact per frame,
time-multiplexed, with the last byte identifying the stream:

- `0x08` — a single finger is down → move the cursor
- `0x00` / `0x10` — two fingers down, one per stream → scroll
