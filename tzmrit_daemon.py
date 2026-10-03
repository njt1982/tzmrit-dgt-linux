"""Send CPU temperatures to the TZMRIT/Jungle Leopard USB panel."""

import logging
import math
import signal
import time

import hid
import psutil

VID = 0x1A2C
PID = 0x4184
INTERFACE = 1
REPORT_ID = 7
REPORT_LENGTH = 64  # Report ID plus 63 data bytes from the HID descriptor.
LOG = logging.getLogger(__name__)


class Shutdown:
    """A signal-safe stop flag with interruptible waits.

    Signal handlers must not acquire Event locks: a signal can arrive while
    the main thread already holds one of those locks.
    """

    def __init__(self):
        self.requested = False

    def set(self):
        self.requested = True

    def is_set(self):
        return self.requested

    def wait(self, seconds):
        deadline = time.monotonic() + seconds
        while not self.requested:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(remaining, 0.1))
        return self.requested


def find_target_interface():
    for info in hid.enumerate(VID, PID):
        if info.get("interface_number") == INTERFACE:
            return info["path"]
    return None


def split_temp_bcd(temperature):
    if not math.isfinite(temperature) or not 0 <= temperature <= 150:
        raise ValueError(f"invalid CPU temperature: {temperature!r}")
    value = int(temperature)
    return [value // 100, (value // 10) % 10, value % 10]


def build_temperature_report(temperature):
    """Encode whole degrees as three decimal digits in verified report 7."""
    payload = [REPORT_ID, 0xFF, 0xFF] + split_temp_bcd(temperature)
    return bytes(payload + [0] * (REPORT_LENGTH - len(payload)))


def get_cpu_temp():
    """Prefer Intel package or AMD Tdie readings; never fabricate a value."""
    sensors = psutil.sensors_temperatures()
    for group, preferred_labels in (
        ("coretemp", ("package id",)),
        ("k10temp", ("tdie", "tctl")),
    ):
        readings = [s for s in sensors.get(group, [])
                    if s.current is not None and math.isfinite(s.current)
                    and 0 <= s.current <= 150]
        for label in preferred_labels:
            preferred = [s.current for s in readings
                         if s.label.lower().startswith(label)]
            if preferred:
                return max(preferred)
        if readings:
            return max(s.current for s in readings)
    raise RuntimeError("no valid CPU temperature in coretemp or k10temp")


def run(stop):
    retry_delay = 2
    last_connection_error = None
    last_sensor_error = None
    while not stop.is_set():
        device = None
        stage = "finding interface 1"
        try:
            path = find_target_interface()
            if path is None:
                raise OSError("panel not found")
            stage = "opening interface 1"
            device = hid.device()
            device.open_path(path)
            LOG.info("Opened screen interface %r", path)
            first_report = True
            while not stop.is_set():
                try:
                    temp = get_cpu_temp()
                except Exception as err:
                    message = str(err)
                    if message != last_sensor_error:
                        LOG.error("CPU temperature unavailable: %s; skipping updates. "
                                  "The panel may retain its last reading.", message)
                    last_sensor_error = message
                    if stop.wait(5):
                        break
                    continue
                if last_sensor_error is not None:
                    LOG.info("CPU temperature readings recovered")
                    last_sensor_error = None
                stage = "sending feature report 7"
                payload = build_temperature_report(temp)
                written = device.send_feature_report(payload)
                if written != len(payload):
                    raise OSError(f"short feature report: {written}/{len(payload)} bytes")
                if first_report:
                    LOG.info("Sent %d-byte temperature report (%.1f C)", written, temp)
                    first_report = False
                retry_delay = 2
                last_connection_error = None
                stop.wait(1)
        except Exception as err:
            message = f"{stage}: {err}"
            if message != last_connection_error:
                LOG.error("%s; retrying with a delay capped at 30s", message)
            last_connection_error = message
        finally:
            if device is not None:
                try:
                    device.close()
                except Exception:
                    LOG.debug("Failed to close HID handle", exc_info=True)
        if stop.wait(retry_delay):
            break
        retry_delay = min(retry_delay * 2, 30)
    LOG.info("Telemetry stopped")


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    stop = Shutdown()
    def request_stop(signum, frame):
        stop.set()
    previous = {sig: signal.signal(sig, request_stop)
                for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        LOG.info("Starting TZMRIT/Jungle Leopard telemetry")
        run(stop)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    main()
