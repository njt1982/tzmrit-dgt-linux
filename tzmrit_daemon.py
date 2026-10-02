import sys
import time
import hid
import psutil

VID = 0x1a2c
PID = 0x4184

def find_target_interface():
    try:
        devices = hid.enumerate(VID, PID)
        for dev_info in devices:
            if dev_info.get('interface_number') == 1:
                return dev_info['path']
    except Exception as e:
        print(f"[-] HID Enumeration error: {e}", file=sys.stderr)
    return None

def split_temp_bcd(temperature):
    temp_int = int(max(0, min(999, temperature)))
    hundreds = temp_int // 100
    tens = (temp_int // 10) % 10
    ones = temp_int % 10
    return [hundreds, tens, ones]

def get_cpu_temp():
    try:
        sensors = psutil.sensors_temperatures()
        for key in ['coretemp', 'k10temp', 'acpitz']:
            if key in sensors and sensors[key]:
                # Grab the maximum core value dynamically
                return max(s.current for s in sensors[key])
    except Exception:
        pass
    return 35  # Safe visual fallback default

def main():
    print("[+] Initializing TZMRIT/Jungle Leopard DGT Telemetry Daemon...")
    
    while True:
        path = find_target_interface()
        if not path:
            print("[-] Screen device panel not found. Retrying connection in 5s...", file=sys.stderr)
            time.sleep(5.0)
            continue
            
        device = hid.device()
        try:
            device.open_path(path)
            print("[+] Native link established with screen hardware interface.")
            
            while True:
                temp = get_cpu_temp()
                temp_payload = split_temp_bcd(temp)
                
                payload = [0x07, 0xff, 0xff] + temp_payload
                payload += [0x00] * (65 - len(payload))
                
                device.send_feature_report(payload)
                time.sleep(1.0)
                
        except (hid.HIDException, IOError) as err:
            print(f"[-] Connection dropped ({err}). Attempting to recover link...", file=sys.stderr)
            time.sleep(2.0)
        except KeyboardInterrupt:
            print("\n[+] Gracefully shutting down telemetry thread loops.")
            try:
                device.close()
            except Exception:
                pass
            break

if __name__ == "__main__":
    main()

