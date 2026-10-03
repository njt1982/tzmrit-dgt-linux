import math
import subprocess
import sys
import textwrap
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import tzmrit_daemon as daemon


class DaemonTests(unittest.TestCase):
    def test_sigterm_exits_cleanly_and_closes_device(self):
        code = textwrap.dedent('''
            import tzmrit_daemon as d
            class Device:
                def open_path(self, path): pass
                def close(self): print("CLOSED", flush=True)
                def send_feature_report(self, data): return len(data)
            d.find_target_interface = lambda: b"fake"
            d.hid.device = Device
            def temp():
                print("READY", flush=True)
                return 42
            d.get_cpu_temp = temp
            d.main()
        ''')
        process = subprocess.Popen([sys.executable, '-u', '-c', code],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), 'READY')
            process.terminate()
            output, errors = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, errors)
            self.assertIn('CLOSED', output)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_report_matches_descriptor_and_decimal_digits(self):
        for temp, digits in [(0, [0, 0, 0]), (42.9, [0, 4, 2]), (105, [1, 0, 5])]:
            report = daemon.build_temperature_report(temp)
            self.assertEqual(len(report), 64)
            self.assertEqual(report[:6], bytes([7, 255, 255] + digits))
            self.assertEqual(report[6:], bytes(58))

    def test_invalid_temperatures_are_rejected(self):
        for temp in [math.nan, math.inf, -1, 151]:
            with self.assertRaises(ValueError):
                daemon.build_temperature_report(temp)

    def test_prefers_package_and_tdie(self):
        sensor = lambda label, value: SimpleNamespace(label=label, current=value)
        for sensors, expected in [
            ({'coretemp': [sensor('Core 0', 70), sensor('Package id 0', 60)]}, 60),
            ({'k10temp': [sensor('Tctl', 80), sensor('Tdie', 55)]}, 55),
        ]:
            with patch.object(daemon.psutil, 'sensors_temperatures', return_value=sensors):
                self.assertEqual(daemon.get_cpu_temp(), expected)

    def test_missing_or_invalid_cpu_sensor_never_fabricates_temperature(self):
        for sensors in [{}, {'acpitz': [SimpleNamespace(label='', current=35)]},
                        {'coretemp': [SimpleNamespace(label='', current=math.nan)]}]:
            with patch.object(daemon.psutil, 'sensors_temperatures', return_value=sensors):
                with self.assertRaises(RuntimeError):
                    daemon.get_cpu_temp()

    def test_stop_closes_device_after_success(self):
        stop = threading.Event()
        device = Mock()
        def send(payload):
            stop.set()
            return len(payload)
        device.send_feature_report.side_effect = send
        with patch.object(daemon, 'find_target_interface', return_value=b'test'), \
             patch.object(daemon.hid, 'device', return_value=device), \
             patch.object(daemon, 'get_cpu_temp', return_value=42):
            daemon.run(stop)
        device.open_path.assert_called_once_with(b'test')
        device.close.assert_called_once()

    def test_sensor_failure_skips_hardware_update_and_closes_on_stop(self):
        stop = Mock()
        stop.is_set.return_value = False
        stop.wait.return_value = True
        device = Mock()
        with patch.object(daemon, 'find_target_interface', return_value=b'test'), \
             patch.object(daemon.hid, 'device', return_value=device), \
             patch.object(daemon, 'get_cpu_temp', side_effect=RuntimeError('missing')):
            daemon.run(stop)
        device.send_feature_report.assert_not_called()
        device.close.assert_called_once()

    def test_failed_open_closes_handle_and_waits(self):
        stop = Mock()
        stop.is_set.return_value = False
        stop.wait.return_value = True
        device = Mock()
        device.open_path.side_effect = OSError('open failed')
        with patch.object(daemon, 'find_target_interface', return_value=b'test'), \
             patch.object(daemon.hid, 'device', return_value=device):
            daemon.run(stop)
        device.close.assert_called_once()
        stop.wait.assert_called_once_with(2)


if __name__ == '__main__':
    unittest.main()
