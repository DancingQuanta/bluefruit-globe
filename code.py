# Circuit Playground Bluefruit Interactive Globe
# Use with the Adafruit BlueFruit LE Connect app
# Works with CircuitPython 5.0.0-beta.0 and later
# running on an nRF52840 CPB board.

import time
import board
import digitalio
import neopixel
import pwmio

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket

# Prep the status LED on the CPB
red_led = digitalio.DigitalInOut(board.D13)
red_led.direction = digitalio.Direction.OUTPUT

# Setup bluetooth
ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

# Setup neopixels
neopixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.1)
RED = (200, 0, 0)
GREEN = (0, 200, 0)
BLUE = (0, 0, 200)
PURPLE = (120, 0, 160)
YELLOW = (100, 100, 0)
AQUA = (0, 100, 100)
BLACK = (0, 0, 0)
color = PURPLE  # current NeoPixel color
neopixels.fill(color)

# Setup PWM output
pwm = pwmio.PWMOut(board.D1, duty_cycle=0)
pwm_max = 65535
pwm_max_half = pwm_max // 2
pwm_step = 1024
pwm_step_n_max = 64
pwm_step_n = 0

# Setup state machine variables
mode = ''
state = ''
i = 0
LAST_TIME = -1
TIME_INTERVAL = 0.5

print("BLE PWM control")
print("Use Adafruit Bluefruit app to connect")


while True:

    # set a pixel black when bluetooth is disconnected
    neopixels[0] = BLACK
    neopixels.show()
    ble.start_advertising(advertisement)

    while not ble.connected:
        # Wait for a connection.
        pass

    # set a pixel blue when connected
    neopixels[0] = BLUE
    neopixels.show()

    # main program runs with bluetooth connection

    while ble.connected:

        # Bluetooth message center

        if uart_service.in_waiting:
            # Packet is arriving.
            red_led.value = False  # turn off red LED
            packet = Packet.from_stream(uart_service)

            if isinstance(packet, ColorPacket):
                # Change the color.
                color = packet.color
                neopixels.fill(color)

            # control PWM and state machine with buttons

            if isinstance(packet, ButtonPacket) and packet.pressed:
                red_led.value = True  # blink to show packet has been received

                if packet.button == ButtonPacket.UP:
                    # Step up PWM

                    if pwm_step_n < pwm_step_n_max:
                        neopixels.fill(color)
                        pwm_step_n += 1
                        pwm.duty_cycle = pwm_step_n * pwm_step - 1
                        print("PWM level {}".format(pwm.duty_cycle))

                elif packet.button == ButtonPacket.DOWN:
                    # Step down PWM

                    if pwm_step_n > 0:
                        neopixels.fill(color)
                        pwm_step_n -= 1

                        if pwm_step_n != 0:
                            pwm.duty_cycle = pwm_step_n * pwm_step - 1
                        else:
                            pwm.duty_cycle = 0

                        print("PWM level {}".format(pwm.duty_cycle))

                elif packet.button == ButtonPacket.RIGHT:
                    # Turn PWM off
                    color = YELLOW
                    neopixels.fill(color)
                    pwm_step_n = pwm_step_n_max // 2
                    pwm.duty_cycle = pwm_max_half
                    print("PWM level {}".format(pwm.duty_cycle))

                elif packet.button == ButtonPacket.LEFT:
                    # Turn PWM fully on
                    color = YELLOW
                    neopixels.fill(color)
                    pwm_step_n = 0
                    pwm.duty_cycle = 0
                    print("PWM level {}".format(pwm.duty_cycle))

                elif packet.button == ButtonPacket.BUTTON_1:
                    # Start ramp state machine
                    mode = 'ramp'
                    state = 'initial'

                elif packet.button == ButtonPacket.BUTTON_2:
                    color = GREEN
                    neopixels.fill(color)

                elif packet.button == ButtonPacket.BUTTON_3:
                    color = BLUE
                    neopixels.fill(color)

                elif packet.button == ButtonPacket.BUTTON_4:
                    color = PURPLE
                    neopixels.fill(color)

            # do this when some buttons are released
            elif isinstance(packet, ButtonPacket) and not packet.pressed:
                if packet.button == ButtonPacket.UP:
                    neopixels.fill(RED)

                if packet.button == ButtonPacket.DOWN:
                    neopixels.fill(RED)

        # State machine

        if 'ramp' in mode:

            # What is the time?
            now = time.monotonic()

            if now >= LAST_TIME + TIME_INTERVAL:

                # Do something after an set interval

                if 'initial' in state:
                #     # Initial state - kick start PWM
                # 
                #     # Full red colour bar for 100% PWM
                #     neopixels.fill(RED)
                # 
                #     # Start PWM at full power
                #     pwm.duty_cycle = pwm_max
                # 
                #     # Move to next state
                #     state = 'kick'
                # 
                #     # Set LAST_TIME so that the next interval
                #     # is short
                #     now = now + (TIME_INTERVAL * 0.9)
                # 
                # elif 'kick' in state:
                #     # End kick and move to next state

                    # Full AQUA colour bar for 0% PWM
                    # PWM set in next state
                    neopixels.fill(AQUA)

                    # Set 0% PWM
                    pwm.duty_cycle = pwm_max_half

                    # Transition to next state
                    state = 'ramp_up'
                    steps = 50
                    min_frac = 0.5
                    i = 0

                elif 'ramp_up' in state:

                    # PWM up and down

                    if i < steps:
                        # Up ramp
                        pwm.duty_cycle = int(pwm_max * (1 + (1 - min_frac) * (i/steps - 1)))
                        print("PWM level {}".format(pwm.duty_cycle))
                        neopixel_index = i // 5
                        neopixels[neopixel_index] = RED
                        i += 1
                    else:
                        state = 'ramp_down'
                        i = 0

                elif 'ramp_down' in state:

                    # PWM up and down

                    if i < steps:
                         # Down ramp
                        pwm.duty_cycle = int(pwm_max * (1 - (1 - min_frac) * i / steps))
                        print("PWM level {}".format(pwm.duty_cycle))
                        neopixel_index = 9 - i // 5
                        neopixels[neopixel_index] = AQUA
                        i += 1
                    else:
                        state = 'end'

                elif 'end' in state:
                    # Turn off PWM
                    pwm.duty_cycle = 0
                    neopixels.fill(color)
                    state = ''
                    mode = ''

                # Record time since last
                LAST_TIME = now
