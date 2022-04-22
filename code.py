# State Classes rev 5
# rev 5 contains code state machine, RTC, SD card wrtiting
# and output to the m4express that controls the epaper screen

# pylint: disable=global-statement,stop-iteration-return,no-self-use,useless-super-delegation

import time
import board
import  digitalio
from adafruit_debouncer import Debouncer

import busio
import adafruit_pcf8523
import adafruit_register

import adafruit_sdcard
import storage


###############################################################################

# Set to false to disable testing/tracing code
TESTING = False

################################################################################
# Setup hardware

# Input Pins
SWITCH_1_PIN = board.D5
SWITCH_2_PIN = board.D6

# Output Pins
HOME_SCRN_OUT = board.D4
PROFILE1_SCRN_OUT = board.D14
TRACK1_SCRN_OUT = board.D15
FOCUS1_SCRN_OUT = board.D16
PROFILE2_SCRN_OUT = board.D17
VOICENOTE_SCRN_OUT = board.D18
RECORD_SCRN_OUT = board.D19


# Initialization of inputs
switch_1_io = digitalio.DigitalInOut(SWITCH_1_PIN)
switch_1_io.direction = digitalio.Direction.INPUT
switch_1_io.pull = digitalio.Pull.UP
switch_1 = Debouncer(switch_1_io)

switch_2_io = digitalio.DigitalInOut(SWITCH_2_PIN)
switch_2_io.direction = digitalio.Direction.INPUT
switch_2_io.pull = digitalio.Pull.UP
switch_2 = Debouncer(switch_2_io)

# Initialization of outputs

# Lights up LED for log on SD card:
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

home_scrn = digitalio.DigitalInOut(HOME_SCRN_OUT)
home_scrn.direction = digitalio.Direction.OUTPUT

profile1_scrn = digitalio.DigitalInOut(PROFILE1_SCRN_OUT)
profile1_scrn.direction = digitalio.Direction.OUTPUT

track1_scrn = digitalio.DigitalInOut(TRACK1_SCRN_OUT)
track1_scrn.direction = digitalio.Direction.OUTPUT

focus1_scrn = digitalio.DigitalInOut(FOCUS1_SCRN_OUT)
focus1_scrn.direction = digitalio.Direction.OUTPUT

profile2_scrn = digitalio.DigitalInOut(PROFILE2_SCRN_OUT)
profile2_scrn.direction = digitalio.Direction.OUTPUT

voicenote_scrn = digitalio.DigitalInOut(VOICENOTE_SCRN_OUT)
voicenote_scrn.direction = digitalio.Direction.OUTPUT

record_scrn = digitalio.DigitalInOut(RECORD_SCRN_OUT)
record_scrn.direction = digitalio.Direction.OUTPUT





#################################################################################################
# Setting up the Real Time Clock and set the initial time

# Creates object I2C that connects the I2C module to pins SCL and SDA
myI2C = busio.I2C(board.SCL, board.SDA)
# Creates an object that can access the RTC and communicate that information along using I2C.
rtc = adafruit_pcf8523.PCF8523(myI2C)

if True:   # change to True if you want to write the time!
# Note this code is in a loop and will continue to use this statement
    #                     year, mon, date, hour, min, sec, wday, yday, isdst
    #   t is a time object
    t = time.struct_time((2022,  04,   11,   15,  35,  0,    0,   -1,    -1))

    #print("Setting time to:", t)     # uncomment for debugging
    rtc.datetime = t
    #print()

# Verifying the set time
# while True:
#    t = rtc.datetime
#    #print(t)     # uncomment for debugging

#    print("The date is %s %d/%d/%d" % (days[t.tm_wday], t.tm_mday, t.tm_mon, t.tm_year))
#    print("The time is %d:%02d:%02d" % (t.tm_hour, t.tm_min, t.tm_sec))

#    time.sleep(1) # wait a second

##################################################################################################
#SD Card

# Creates object that connects SPI bus and a digital output for the microSD card's CS line.
# The pin name should match our wiring.
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
# This is the chip select line on the M4 board.
cs = digitalio.DigitalInOut(board.D10)

# This creates the microSD card object and the filesystem object:
# Inputs are the spi and cs objects.
sdcard = adafruit_sdcard.SDCard(spi, cs)
# The microSD card object and the filesystem object are now
# being passed through Vfsfat class.
vfs = storage.VfsFat(sdcard)

# We can now make the path /sd on the CircuitPython
# filesystem read and write from the card:
storage.mount(vfs, "/sd")

# Creates a file and writes name inside a text file along the path.
with open("/sd/stamp.csv", "a") as f:
    f.write("Date, Time In, Time Out , Total, Voice Note\r\n")
print("Logging column names into the filesystem\n")


################################################################################
# Global Variables
#NOTE THIS MAY NOT BE NEEDED, THESE VARIABLES ARE ONLY AVAILABLE TO THE LOOP, WHICH
#IS LOCATED OUTSIDE OF MACHINE STATES




################################################################################
# Support functions

# Code tracing feature
def log(s):
    """Print the argument if testing/tracing is enabled."""
    if TESTING:
        print(s)


################################################################################
# State Machine, Manages states

class StateMachine(object):

    def __init__(self):                             # Needed constructor
        self.state = None
        self.states = {}


    def add_state(self, state):                     # "add state" attribute, adds states to the machine
        self.states[state.name] = state

    def go_to_state(self, state_name):              # "go to state" attribute, facilittes transition to other states. Prints confirmation when "Testing = True"
        if self.state:
            log('Exiting %s\n' % (self.state.name))
            self.state.exit(self)
        self.state = self.states[state_name]
        log('Entering %s' % (self.state.name))
        self.state.enter(self)

    def pressed(self):                              # "button pressed" attribute. Accessed at the end of each loop, applies a pause and prints confirmaiton if setup.
        if self.state:
            log('Updating %s' % (self.state.name))
            self.state.pressed(self)
            #print("'StateMachine' Class occurrence")  # Use this print statement to understand how the states transition here to update the state in the serial monitor
            time.sleep(.125)                             # Critial pause needed to prevent the serial monitor from being "flooded" with data and crashing



################################################################################
# States

# Abstract parent state class: I'm not 100% sure that this state is the "parent class" for the states below.
# So far "StateMachine" appears to be the parent class, some clarification is needed to indentify how a class is called by "super().__init__()" (aka "Inheritance")

class State(object):


    def __init__(self):         # Constructor. Sets variables for the class, in this instance only, "self". Note machine variable below in the "enter" attribute
        # Variables for time stamps
        #Initialization of global variables which are inherited by child states in the following code

        self.month_in = 0
        self.day_in = 0
        self.year_in = 0
        self.hour_in = 0
        self.min_in = 0
        self.sec_in = 0

        self.month_out = 0
        self.day_out = 0
        self.year_out = 0
        self.hour_out = 0
        self.min_out = 0
        self.sec_out = 0



    @property
    def name(self):             # Attribute. Only the name is returned in states below. The State object shouldn't be called and returns nothing
        return ''

    def enter(self, machine):   # Class Attribute. Does what is commanded when the state is entered
        pass

    def exit(self, machine):    # Class Attribute. Does what is commanded when exiting the state
        pass

    def pressed(self, machine): # Class Attribute. Does what is commanded when a button is pressed
        print("'State' Class occurrence")   #This hasn't been called yet, I used this as a test to investigate the "inheritance" of child classes below.

########################################
# This state is active when powered on and other states return here
class Home(State):

    def __init__(self):
        super().__init__()          # Child class inheritance

    @property
    def name(self):
        return 'Home'

    def enter(self, machine):
        State.enter(self, machine)
        # Display a screen for the "Home" State, or enable a pin that displays the "Home" screen
        print('#### Home State ####')
        home_scrn.value = True    # output high signal to the epaper microcontroller
        print('Placeholder to display date and time\n')

    def exit(self, machine):
        State.exit(self, machine)
        home_scrn.value = False    # output low signal to the epaper microcontroller

    def pressed(self, machine):
        if switch_1.fell:                                         #
            machine.go_to_state('Profile 1')
        if switch_2.fell:
            machine.go_to_state('Profile 2')
    # Experiment clearing the screen before transitioning, perhaps load the next screen here? OR in "exit"

########################################
# The "Profile 1" state. Either choose to track a task or use a focus timer.
class Profile1(State):

    def __init__(self):
        super().__init__()
        self.State = State()


    @property
    def name(self):
        return 'Profile 1'

    def enter(self, machine):
        State.enter(self, machine)
        print('#### Profile 1 State ####')
        profile1_scrn.value = True    # output high signal to the epaper microcontroller
        print('Placeholder to display date and time\n')

    def exit(self, machine):
        State.exit(self, machine)
        profile1_scrn.value = False    # output low signal to the epaper microcontroller

    def pressed(self, machine):
        if switch_1.fell:
            machine.go_to_state('Tracking1')
        if switch_2.fell:
            machine.go_to_state('Focus Timer 1')
    # Experiment clearing the screen before transitioning, perhaps load the next screen here? OR in "exit"

########################################
# The "Tracking 1" state. Begin tracking task 1 in this state
class Tracking1(State):

    def __init__(self):
        super().__init__()
        self.State = State()


    @property
    def name(self):
        return 'Tracking1'

    def enter(self, machine):
        State.enter(self, machine)
        print('#### Tracking Task 1 State ####')
        track1_scrn.value = True    # output high signal to the epaper microcontroller
        print('Placeholder to display date and time')
        print('Placeholder to display counter for tracked time')

        print('Store a time-stamp for a tracking START time (global variable)\n')
        # This code is in process to store a "time in" stamp
        t = rtc.datetime

        # Components of the "time in" stamp
        self.State.month_in = t.tm_mon
        self.State.day_in = t.tm_mday
        self.State.year_in = t.tm_year

        # Components of the "time in" stamp
        self.State.hour_in = t.tm_hour
        self.State.min_in = t.tm_min
        self.State.sec_in = t.tm_sec

        print('Logging start time to .csv\n')    # Upon exit, log the global variables containing time stamps to the SD Card

        # appending timestamp to file, Use "a" to append file, "w" will overwrite data in the file, "r" will read lines from the file.
        with open("/sd/stamp.csv", "a") as f:
            led.value = True    # turn on LED to indicate writing entries
            print("%d/%d/%d, " % (self.State.month_in, self.State.day_in, self.State.year_in)) #Prints to serial monitor the data about to be written to the SD card
            f.write("%d/%d/%d, " % (self.State.month_in, self.State.day_in, self.State.year_in))    # Common U.S. date format

            print("%d:%02d:%02d, " % (self.State.hour_in, self.State.min_in, self.State.sec_in)) #Prints to the serial monitor the data about to be written to the SD card
            f.write("%d:%02d:%02d, " % (self.State.hour_in, self.State.min_in, self.State.sec_in))  # "Time in" written to file
            led.value = False  # turn off LED to indicate we're done

            # Read out all lines in the .csv file to verify the last entry
            #with open("/sd/stamp.csv", "r") as f:
            #print("Printing lines in file:")
            #line = f.readline()
            #while line != '':
            #print(line)
            #line = f.readline()

    def exit(self, machine):
        State.exit(self, machine)
        # Experiment clearing the Epaper Screen in this 'exit' attribute

        #Check that the variable values remain
        print('Track the variable values on exit')
        print('Date in: ' + str(self.State.month_in) + '/' + str(self.State.day_in) + '/' + str(self.State.year_in))
        print('Time in: ' + str(self.State.hour_in) + ':' + str(self.State.min_in) + ':' + str(self.State.sec_in) + '\n')
        track1_scrn.value = False    # output low signal to the epaper microcontroller

    def pressed(self, machine):
        if switch_1.fell:
            machine.go_to_state('Voice Note')
        if switch_2.fell:
            machine.go_to_state('Voice Note')

########################################
# The "Focus Timer 1" state. Begin the focus timer here
class FocusTimer1(State):

    def __init__(self):
        super().__init__()
        self.State = State()


    @property
    def name(self):
        return 'Focus Timer 1'


    def enter(self, machine):
        State.enter(self, machine)
        print('#### Focus Timer 1 State ####')
        focus1_scrn_scrn.value = True    # output high signal to the epaper microcontroller
        print('Display Focus Timer counting down')
        print('Display date and time\n')
        print('Placeholder to display "Ah Ah Ah" screen\n')
        # Display a screen for "Focus Timer 1" state, or enable a pin that displays the "Focus Timer 1" screen

    def exit(self, machine):
        State.exit(self, machine)
        focus1_scrn.value = False    # output low signal to the epaper microcontroller


    def pressed(self, machine):
        if switch_1.fell:                   # Either button press results in a transition to the "Home" state
            machine.go_to_state('Home')
        if switch_2.fell:                   # Question: Perhaps a transition to "Profile1" is more appropriate?
            machine.go_to_state('Home')
    # Experiment clearing the screen before transitioning, perhaps load the next screen here? OR in "exit"

########################################
# The "Profile 2" state. Implement at a later date. Any button press in this state causes a transition to the "Home" state.
class Profile2(State):

    def __init__(self):
        super().__init__()
        self.State = State()


    @property
    def name(self):
        return 'Profile 2'

    def enter(self, machine):
        State.enter(self, machine)
        print('#### Profile 2 State ####')
        profile2_scrn.value = True    # output high signal to the epaper microcontroller
        print('Placeholder to display Profile 2 Screen, date and time\n')
        print('Placeholder to display "Ah Ah Ah" screen\n')

    def exit(self, machine):
        State.exit(self, machine)
        profile2_scrn.value = False    # output low signal to the epaper microcontroller


    def pressed(self, machine):
        if switch_1.fell:
            machine.go_to_state('Home')     # Either button press returns to "Home" state, further profiles will be implemented in the future
        if switch_2.fell:
            machine.go_to_state('Home')
    # Experiment clearing the screen before transitioning, perhaps load the next screen here? OR in "exit"

########################################
# The "Voice Note" state. A placeholder state that has an option to record a voice note or return to the "home" state
class VoiceNote(State):

    def __init__(self):
        super().__init__()
        self.State = State()


    @property
    def name(self):
        return 'Voice Note'

    def enter(self, machine):
        State.enter(self, machine)

        #Screen Placeholders
        print('#### Voice Note State ####')
        voicenote_scrn.value = True    # output high signal to the epaper microcontroller
        print('Placeholder to display, "Yes or No" to record a note\n')

        #Tracking1 has ended, store a time out stamp upon entry then display screens
        print('Store a time-stamp for a tracking STOP time (global variable)\n')
        # This code is in process to store a "time in" stamp
        t = rtc.datetime

        # Components of the "time in" stamp
        self.State.month_out = t.tm_mon     #Not currently used for the initial demo
        self.State.day_out = t.tm_mday      #Not currently used for the initial demo
        self.State.year_out = t.tm_year     #Not currently used for the initial demo

        # Components of the "time out" stamp
        self.State.hour_out = t.tm_hour
        self.State.min_out = t.tm_min
        self.State.sec_out = t.tm_sec

        print('Logging stop time to .csv filesystem\n')    # Upon exit, log the global variables containing time stamps to the SD Card

        # appending timestamp to file, Use "a" to append file, "w" will overwrite data in the file, "r" will read lines from the file.
        with open("/sd/stamp.csv", "a") as f:
            led.value = True    # turn on LED to indicate writing entries
            #print("%d/%d/%d, " % (self.State.month_out, self.State.day_out, self.State.year_out)) #Prints to serial monitor the data about to be written to the SD card
            #f.write("%d/%d/%d, " % (self.State.month_out, self.State.day_out, self.State.year_out))    # Common U.S. date format

            print("%d:%02d:%02d, " % (self.State.hour_out, self.State.min_out, self.State.sec_out)) #Prints to the serial monitor the data about to be written to the SD card
            f.write("%d:%02d:%02d, " % (self.State.hour_out, self.State.min_out, self.State.sec_out))  # "Time in" written to file
            led.value = False  # turn off LED to indicate we're done

            # Read out all lines in the .csv file to verify the last entry
            #with open("/sd/stamp.csv", "r") as f:
            #print("Printing lines in file:")
            #line = f.readline()
            #while line != '':
            #print(line)
            #line = f.readline()



    def exit(self, machine):
        State.exit(self, machine)
        # Display the time stamps upon exit
        print('Track the variable values on exit')
        print("%d/%d/%d, " % (self.State.month_in, self.State.day_in, self.State.year_in)) #Prints to serial monitor the data about to be written to the SD card
        print("%d:%02d:%02d, " % (self.State.hour_in, self.State.min_in, self.State.sec_in)) #Prints to the serial monitor the data about to be written to the SD card
        print("%d/%d/%d, " % (self.State.month_out, self.State.day_out, self.State.year_out)) #Prints to serial monitor the data about to be written to the SD card
        print("%d:%02d:%02d, " % (self.State.hour_out, self.State.min_out, self.State.sec_out)) #Prints to the serial monitor the data about to be written to the SD card
        print('Note: Some variables have been forgotten between states\n')
        voicenote_scrn.value = False    # output low signal to the epaper microcontroller

    def pressed(self, machine):
        if switch_1.fell:                   # Yes button results in a transition to the "Record" state
            machine.go_to_state('Record')
        if switch_2.fell:                   # No button results in a transition to the "Home" state
            machine.go_to_state('Home')   # APPEND AN EMPTY ENTRY INTO THE SPREADSHEET HERE, then go gine
    # Experiment clearing the screen before transitioning, perhaps load the next screen here? OR in "exit"

########################################
# The "Record Note" state. A placeholder state that will record a note then transition to the "home" state
# Constains an easter egg photo
class Record(State):

    def __init__(self):
        super().__init__()
        self.State = State()


    @property
    def name(self):
        return 'Record'

    def enter(self, machine):
        State.enter(self, machine)
        print('#### Record Note State ####')
        record_scrn.value = True    # output high signal to the epaper microcontroller #Easter egg
        print('Placeholder to display, "Placeholder for second semester functionality!"\n')

        # Display the time stamps about to be recorded
        print('Track the variable values on entry')
        print("%d/%d/%d, " % (self.State.month_in, self.State.day_in, self.State.year_in)) #Prints to serial monitor the data about to be written to the SD card
        print("%d:%02d:%02d, " % (self.State.hour_in, self.State.min_in, self.State.sec_in)) #Prints to the serial monitor the data about to be written to the SD card
        print("%d/%d/%d, " % (self.State.month_out, self.State.day_out, self.State.year_out)) #Prints to serial monitor the data about to be written to the SD card
        print("%d:%02d:%02d, " % (self.State.hour_out, self.State.min_out, self.State.sec_out)) #Prints to the serial monitor the data about to be written to the SD card
        print('Note: The variables have been forgotten between states\n')

    def exit(self, machine):
        State.exit(self, machine)
        record_scrn.value = False    # output low signal to the epaper microcontroller

        print('Logging a voice note to .csv filesystem\n')    # Upon exit, log the global variables containing time stamps to the SD Card

        # appending timestamp to file, Use "a" to append file, "w" will overwrite data in the file, "r" will read lines from the file.
        with open("/sd/stamp.csv", "a") as f:
            led.value = True    # turn on LED to indicate writing entries
            f.write("Delta Formula, Speech to text voice note\r\n")
            #f.write(None, None, None, "sum(d2:d)\r\n",None)    #THERE IS PROBABLY AN ERROR HERE, In Excel you can't really sum items separated by ":"
            led.value = False  # turn off LED to indicate we're done

            # Read out all lines in the .csv file to verify the last entry
            #with open("/sd/stamp.csv", "r") as f:
            #print("Printing lines in file:")
            #line = f.readline()
            #while line != '':
            #print(line)
            #line = f.readline()


            #Functionality below is time difference and Sum, which may be handled in the spreadsheet
            #Need correction for data types of 12 & 24 hours after some date is logging
            #delta_hour = self.State.hour_out - self.State.hour_in # Calculate hour difference
            #delta_min = self.State.min_out - self.State.min_in  # Calculate min difference
            #delta_sec = self.State.sec_out - self.State.sec_in # Calculate sec difference
            #f.write("%d:%02d:%02d, " % (delta_hour, delta_min, delta_sec))  # Write the change in time to the file


    def pressed(self, machine):

        if switch_1.fell:
            #print('Put Easter Egg photo here?\n')
            machine.go_to_state('Home') # Return "Home"
        if switch_2.fell:
            machine.go_to_state('Home') # Return "Home"



################################################################################
# Create the state machine

LTB_state_machine = StateMachine()          # Defines the state machine
LTB_state_machine.add_state(Home())         # Adds the listed states to the machine (Except for the class, "State"
LTB_state_machine.add_state(Profile1())
LTB_state_machine.add_state(Tracking1())
LTB_state_machine.add_state(FocusTimer1())
LTB_state_machine.add_state(Profile2())
LTB_state_machine.add_state(VoiceNote())
LTB_state_machine.add_state(Record())

LTB_state_machine.go_to_state('Home')   #Starts the state machine in the "Home" state

while True:
    switch_1.update()               #Checks the switch 1 state each time the loop executes, necessary for button state changes
    switch_2.update()               #Checks the switch 1 state each time the loop executes, necessary for button state changes
    LTB_state_machine.pressed()     #Transitions to the StateMachine attrubute, "pressed". Doesn't do much there other than report the current state
