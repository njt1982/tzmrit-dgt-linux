# TZMRIT / Jungle Leopard KF620 DGT LCD Driver for Linux

A Python-based telemetry daemon for controlling the 7-segment digital LED temperature display on **TZMRIT / Jungle Leopard KF620 DGT** coolers in Linux environments (including Proxmox, Debian, and Ubuntu).

## ⚠️ Important Disclaimers

- **Hardware Compatibility**: This project was reverse-engineered specifically for the **TZMRIT / Jungle Leopard KF620 DGT** series cooler. 
- **Factory Profile**: The electronic panel controller identifies in `lsusb` as a generic keyboard layout spoofing device under the manufacturer profile:
```
ID 1a2c:4184 China Resource Semico Co., Ltd USB Gaming Keyboard
```
- **Use at Your Own Risk**: While this script is designed to safely execute standard system read-and-pipe telemetry loops, use it at your own discretion.
- **Community Contribution**: This is an independent, community-created solution. It is not officially supported, endorsed, or certified by TZMRIT or Jungle Leopard.

## 🚀 Features

- **Native Linux Telemetry**: Bypasses the vendor's Windows software application and heavy VM layers completely.
- **Auto-Targeting Connection**: Bypasses spoofed interface endpoints and explicitly binds to the target hardware screen link (Interface 1).
- **BCD Array Processing**: Translates live CPU telemetry data into the precise 3-byte BCD array format `[Hundreds, Tens, Ones]` required by the factory screen microchip.
- **Automatic Recovery**: Safely catches `HIDException` or I/O transport data drops if a USB host transiently drops, cycling reconnection attempts automatically without crashing the script thread.

## 📋 Requirements

- **Linux Operating System** (Tested on Proxmox, Ubuntu, Debian)
- **Root Privileges** (Required to write raw payloads directly to system `/dev/hidraw*` peripheral nodes)
- **Astral `uv`** (Modern fast Python package tool wrapper used to host isolated environments instantly)

## 🔧 Installation & Setup

### 1. Install `uv` on your System
If you don't have `uv` installed, execute the official standalone installation script:
```bash
curl -LsSf https://astral.sh | sh
```
*(Restart your terminal window after installation so the `uv` toolpath becomes globally accessible).*

### 2. Clone and Setup the Workspace
Clone this repository to your computer and navigate into the target folder path:
```bash
git clone https://github.com
cd tzmrit-dgt-linux
```

### 3. Execution Test
Run the script using `uv run`. The script relies on dependencies defined inside `pyproject.toml` (`hidapi` and `psutil`). `uv` will download and map these securely on the fly without making changes to your global operating system:
```bash
sudo uv run python3 tzmrit_daemon.py
```
*(Keep your terminal open—the screen will instantly wake up from its blank lock-state and begin matching your hardware core temperatures in real-time).*

---

## ⚙️ Running permanently as a Background Daemon

To configure this script to boot up automatically when your computer powers on without tying up an active terminal shell window, use the included Systemd service file wrapper:

1. Copy your repository workspace to a permanent system location:
   ```bash
 sudo cp -r . /usr/local/bin/tzmrit-dgt-linux
   ```

2. Link the template service manager script configuration file:
   ```bash
 sudo cp /usr/local/bin/tzmrit-dgt-linux/tzmrit-daemon.service /etc/systemd/system/
   ```

3. Refresh system configurations and turn the daemon engine on:
   ```bash
 sudo systemctl daemon-reload
 sudo systemctl enable --now tzmrit-daemon.service
   ```

4. Verify the active telemetry loop status:
   ```bash
 sudo systemctl status tzmrit-daemon.service
   ```

---

## 🛠️ Troubleshooting

### Screen remains on 00 or displays a static figure
1. Terminate your active tasks or service blocks:
   ```bash
 sudo systemctl stop tzmrit-daemon.service
   ```
2. Run an active hardware link check via Python to ensure your motherboard header claims it correctly:
   ```bash
 sudo uv run --with hidapi python3 -c "import hid; print([d for d in hid.enumerate(0x1a2c, 0x4184)])"
   ```
3. Ensure no secondary virtual machine software instances (like VirtualBox or QEMU/KVM configs) have an active pass-through rule claiming the `1a2c:4184` device identity.

### Sensor Not Found error loops
The script searches standard Linux platform temperature sensor string arrays (`coretemp`, `k10temp`, `acpitz`). If your system uses a custom distribution configuration, find your exact sensor name via Python:
```bash
uv run --with psutil python3 -c "import psutil; print(list(psutil.sensors_temperatures().keys()))"
```
Open `tzmrit_daemon.py` and add your system's specific sensor key string directly to the lookup list inside the `get_cpu_temp()` function:
```python
for key in ['coretemp', 'k10temp', 'acpitz', 'YOUR_SENSOR_NAME_HERE']:
```

---

## 📄 License & Credits

- Underlying protocol parameters deduced from reversing factory windows frameworks. 
- Thanks to the Linux open-source cooling community for tracking device structures across budget internal USB devices.
- Distributed under the MIT License. Feel free to modify and share!
