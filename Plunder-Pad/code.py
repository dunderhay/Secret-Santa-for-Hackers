print("Starting")

import board

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys import KC
from kmk.scanners import DiodeOrientation
from kmk.handlers.sequences import send_string, simple_key_sequence
from kmk.modules.layers import Layers
from kmk.modules.tapdance import TapDance


# KEYTBOARD SETUP
keyboard = KMKKeyboard()
keyboard.modules.append(Layers())
tapdance = TapDance()
tapdance.tap_time = 250
keyboard.modules.append(tapdance)

keyboard.col_pins = (board.GP10, board.GP11, board.GP12)
keyboard.row_pins = (board.GP13, board.GP14, board.GP15)
keyboard.diode_orientation = DiodeOrientation.COL2ROW

XXXXXXX = KC.NO

# MACROS ROW 1
## BURP LAYER
MOMENTARY = KC.MO(1)
MOVE_PREVIOUS_TAB = simple_key_sequence([KC.LCTRL(KC.MINUS)])
MOVE_NEXT_TAB = simple_key_sequence([KC.LCTRL(KC.EQUAL)])
## ENCODE & APPS LAYER
TERMINAL = simple_key_sequence([KC.LCMD(KC.SPACE()), KC.MACRO_SLEEP_MS(1000), send_string('iTerm'), KC.ENTER])
BURP_SUITE = simple_key_sequence([KC.LCMD(KC.SPACE()), KC.MACRO_SLEEP_MS(1000), send_string('Burp Suite'), KC.ENTER])

# MACROS ROW 2
## BURP LAYER
REPEATER_TAB = simple_key_sequence([KC.LCTRL(KC.LSHIFT(KC.R))])
INTRUDER_TAB = simple_key_sequence([KC.LCTRL(KC.LSHIFT(KC.I))])
PROXY_TAB = simple_key_sequence([KC.LCTRL(KC.LSHIFT(KC.P))])
## ENCODE & APPS LAYER
URL_ENCODE =  simple_key_sequence([KC.LCTRL(KC.U)])
URL_DECODE = simple_key_sequence([KC.LCTRL(KC.LSHIFT(KC.U))])
HTML_ENCODE = simple_key_sequence([KC.LCTRL(KC.H)])
HTML_DECODE = simple_key_sequence([KC.LCTRL(KC.LSHIFT(KC.H))])
BASE64_ENCODE = simple_key_sequence([KC.LCTRL(KC.B)])
BASE64_DECODE = simple_key_sequence([KC.LCTRL(KC.LSHIFT(KC.B))])

# MACROS ROW 3
## BURP LAYER
SEND_TO_REPEATER = simple_key_sequence([KC.LCTRL(KC.R)])
SEND_TO_INTRUDER = simple_key_sequence([KC.LCTRL(KC.I)])
PROXY_INSPECTION = KC.TD(
    # Tap once to forward intercepted proxy request
    simple_key_sequence([KC.LCTRL(KC.F)]),
    # Tap twice to toggle proxy interception
    simple_key_sequence([KC.LCTRL(KC.T)]),
)


# KEYMAPS
keyboard.keymap = [
    # BURP LAYER
    [
        PROXY_INSPECTION, SEND_TO_INTRUDER,  SEND_TO_REPEATER,
        REPEATER_TAB,     INTRUDER_TAB,      PROXY_TAB,
        MOVE_NEXT_TAB,    MOVE_PREVIOUS_TAB, MOMENTARY,
    ],
    # ENCODE & APPS LAYER
    [
        BASE64_ENCODE, HTML_DECODE, URL_ENCODE,
        BASE64_DECODE, HTML_ENCODE, URL_DECODE,
        TERMINAL,   BURP_SUITE,  XXXXXXX,
    ],
]

if __name__ == '__main__':
    keyboard.go()