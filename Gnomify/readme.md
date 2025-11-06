# 🧙‍♂️ Gnomify – The Hardware Notification Wizard 

<img src="images/gnomify-wizard.jpg" width="50%" height="50%" />

A Wi-Fi-connected desktop companion that uses light to show the state of your terminal job. Gnomify is a physical notifier inspired by ntfy.sh, but built in hardware.

Perched beside your keyboard, the wizard raises an orb that pulses as your commands run — shifting color to show when a scan or other terminal job is in progress, complete, or has failed.

Whether it's `ffuf`, `nmap`, `nuclei`, or any other command-line tool, Gnomify shows you what’s happening at a glance.

---

## First Boot & Setup

On first boot, the wizard conjures an AP for provisioning.

**Hotspot (AP)**

- **SSID:** `Gnomify-Setup`
- **Password:** `gnomify123`

Connect to the AP and open `http://192.168.4.1` to:

- Enter your Wi-Fi SSID and password
- Set the **API token** (default: `verysecrettoken`)

The API token is saved in flash (Preferences / NVS) and used by the device to authenticate incoming requests.

When online, the wizard's orb breathes **cyan** to indicate a healthy WiFi connection.

---

## 🔮 Orb State Reference

Each colour of the wizard's orb conveys a different state:

| State       |     LED colour | Meaning                            |
| ----------- | ------------- | ---------------------------------- |
| `busy`      | 🟣 **Purple** | Work in progress / scanning        |
| `success`   | 🟢 **Green**  | Command completed successfully     |
| `error`     | 🔴 **Red**    | Command failed or error occurred   |
| `attention` | 🔵 **Blue**   | Attention, hit, or manual signal   |
| `offline`   | 🟠 **Orange** | Lost Wi-Fi or disconnected         |
| `portal`    | ⚪ **White**  | Setup mode / captive portal active |
| `off`       | ⚫ **Off**    | LED turned off manually            |

---

## API Reference

### 1. Send Event — set the orb state

Change the wizard's orb colour by posting a state:

```bash
curl -s -X POST "http://gnomify.local/event?token=verysecrettoken" \
  -H "Content-Type: application/json" \
  -d '{"state":"success"}'
```

Supported states: `busy`, `success`, `error`, `attention`, `off`

### 2. Query State — read current status

Retrieve current Wi-Fi and orb state:

```bash
curl -s "http://gnomify.local/state?token=verysecrettoken"
```

Example response:

```json
{
  "wifi_connected": true,
  "state": 2,
  "in_portal": false,
  "token": "verysecrettoken"
}
```

> `state` is an integer corresponding to the internal enum; use the API or the README table to map it to a name.

### 3. Root help page

```bash
curl "http://gnomify.local/"
```

---

## Command-Line Wrapper

Use `gnomify.sh` (included) or create your own wrapper to notify the wizard around arbitrary commands.

Example wrapper (concept):

```bash
#!/usr/bin/env bash
ESP="http://gnomify.local"
TOKEN="verysecrettoken"

notify() {
  curl -s -X POST "$ESP/event?token=$TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"state\":\"$1\"}" >/dev/null 2>&1
}

notify busy
"$@"
if [ $? -eq 0 ]; then
  notify success
else
  notify error
fi
```

### Example usage

```bash
./gnomify.sh ffuf -u https://target/FUZZ -w words.txt
./gnomify.sh sudo nmap -sC -sV example.com
./gnomify.sh --state attention
./gnomify.sh --state off
./gnomify.sh --get-state
```

---

## 🧹 Reset / Reconfigure

Erase saved Wi-Fi credentials and NVS data (factory reset):

```bash
pio run -t erase
```

On next boot the wizard will reopen the `Gnomify-Setup` portal.

---

## Development

1. Clone the repo and open it in **PlatformIO**.
2. Adjust configuration in `src/main.cpp` if needed (pins, defaults).
3. List your device:

```bash
pio device list
```

4. Update ports in `platformio.ini` if necessary:

```ini
upload_port = /dev/cu.usbmodem1101
monitor_port = /dev/cu.usbmodem1101
```

5. Build and flash:

```bash
pio run -t upload -e gnomify
```

6. Monitor serial output:

```bash
pio device monitor
```

---
