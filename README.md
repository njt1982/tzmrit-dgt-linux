# TZMRIT / Jungle Leopard KF620 DGT display for Linux

A small Python daemon that sends CPU temperatures to the USB temperature panel on a TZMRIT / Jungle Leopard KF620 DGT cooler. This is an independent project, not endorsed by the manufacturer.

## Verified behavior

The working panel identifies as `1a2c:4184` (SEMICO USB Gaming Keyboard). The daemon selects interface 1. Its HID descriptor defines feature report 7 with 63 data bytes: **64 bytes total including the report ID**.

The tested temperature message begins with `[7, 255, 255, hundreds, tens, ones]` and is padded with zeros. The three temperature bytes are individual decimal digits, truncated to whole degrees. This message has been verified on the project's Ubuntu host; other hardware revisions and operating systems have not been established as compatible. The full vendor protocol, including an unavailable/blank display command, is not known.

Intel `coretemp` package readings and AMD `k10temp` Tdie readings are preferred. Other valid readings in those CPU groups are used as a fallback. ACPI thermal-zone readings are not assumed to measure the CPU. Missing, non-finite, or out-of-range temperatures are logged and updates are skipped; the daemon never substitutes an invented temperature. **During sensor failure, the panel may retain a stale reading.** Valid temperatures must be between 0 and 150°C.

The daemon retries connection failures with delays from 2 to 30 seconds, suppresses repeated identical errors, closes handles on failure, and handles SIGINT/SIGTERM shutdown. It does not reset USB devices or manually unbind kernel drivers. The installed `hidapi` backend may manage kernel driver ownership when opening a device.

## Setup

Requires Python 3.10+, `uv`, and USB device access. The supplied service runs as root. Install `uv` using its official installation instructions, then:

```bash
git clone https://github.com/njt1982/tzmrit-dgt-linux.git
cd tzmrit-dgt-linux
uv sync --locked
sudo .venv/bin/python -u tzmrit_daemon.py
```

Stop the foreground process with Ctrl+C before starting the service.

For the supplied service, place the project at `/usr/local/bin/tzmrit-dgt-linux` and create its virtual environment there with `uv sync --locked`. The service runs that environment's Python directly; it does not install or resolve dependencies at boot.

```bash
sudo ln -s /usr/local/bin/tzmrit-dgt-linux/tzmrit-daemon.service /etc/systemd/system/tzmrit-daemon.service
sudo systemctl daemon-reload
sudo systemctl enable --now tzmrit-daemon.service
systemctl status tzmrit-daemon.service
journalctl -u tzmrit-daemon.service -n 30
```

If a unit already exists, inspect it before replacing it. Changes to a linked unit require `daemon-reload`; Python changes require a service restart. Because the service runs as root, anyone who can edit its unit, Python source, or virtual environment can change code executed as root. A hardened installation should make those files root-owned and grant only the necessary device access.

## Troubleshooting

Stop the service before running a second instance. Enumerate the panel:

```bash
sudo .venv/bin/python -c 'import hid; print(hid.enumerate(0x1a2c, 0x4184))'
```

Enumeration alone does not prove the interfaces can be opened. Check the USB configuration, interface driver bindings, and kernel logs. On the tested host, unsuccessful unbind/recovery experiments left the device unconfigured with `can't set config #1, error -32`; rebooting restored it. Do not unbind unrelated keyboard interfaces based solely on their manufacturer name.

Inspect available temperatures:

```bash
.venv/bin/python -c 'import psutil; print(psutil.sensors_temperatures())'
```

Additional CPU sensor families need explicit selection and validation in `get_cpu_temp()`.

## Development

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tests use simulated devices and do not send USB messages. Confirm physical display behavior separately after protocol changes.
