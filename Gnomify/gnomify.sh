#!/usr/bin/env bash
# ==========================================================
#  🧙‍♂️ Gnomify — The Hardware Notification Wizard 🔮
#  A Wizard wielding an orb that breathes colour to show task state.
#  https://github.com/<yourname>/gnomify
# ==========================================================

# ---------------- CONFIG ----------------
ESP_HOST="http://gnomify.local"      # or http://<device-ip>
TOKEN="verysecrettoken"              # must match firmware

# ---------------- FUNCTIONS ----------------
notify() {
    local state="$1"
    curl -s -X POST "$ESP_HOST/event?token=$TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"state\":\"$state\"}" >/dev/null 2>&1
}

show_help() {
cat <<'EOF'
🧙‍♂️ Gnomify — The Hardware Notification Wizard 🔮
-------------------------------------------------

Usage:
  gnomify.sh <command> [args...]
      Run a command and show task progress:
        🟣 busy   while running
        🟢 success  if it exits 0
        🔴 error    if non-zero

  gnomify.sh --state <busy|success|error|attention|off>
      Manually set LED state.

  gnomify.sh --get-state
      Query current device state via /state endpoint.

  gnomify.sh --help
      Show this help message.

Examples:
  gnomify.sh ffuf -u https://target/FUZZ -w wordlist.txt
  gnomify.sh sudo nmap -sC -sV example.com
  gnomify.sh --state attention     # set LED to blue
  gnomify.sh --state off           # turn LED completely off
  gnomify.sh --get-state           # retrieve JSON state info

Behavior:
  🟣 busy       job running
  🟢 success    job completed OK (exit 0)
  🔴 error      job failed (non-zero exit)
  🔵 attention  "look now" alert to grab your attention
  ⚫ off        LED manually off until next event
  🩵 cyan       system idle / online
  🟡 yellow     connecting Wi-Fi
  🟠 orange     offline (shows even if off)

Config:
  Edit the variables at the top of this script:
      ESP_HOST="http://gnomify.local"
      TOKEN="verysecrettoken"

Return value:
  Passes through the exit code of the wrapped command.
EOF
}

# ---------------- MAIN ----------------
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

if [[ "$1" == "--get-state" ]]; then
    curl -s "$ESP_HOST/state?token=$TOKEN"
    echo
    exit 0
fi

if [[ "$1" == "--state" ]]; then
    shift
    state="$1"
    if [[ -z "$state" ]]; then
        echo "Usage: gnomify.sh --state <busy|success|error|attention|off>"
        exit 1
    fi
    notify "$state"
    echo "Sent state: $state"
    exit 0
fi

if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

notify "busy"
"$@"
STATUS=$?

if [ $STATUS -eq 0 ]; then
    notify "success"
else
    notify "error"
fi

exit $STATUS