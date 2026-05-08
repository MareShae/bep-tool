"""
@author mareshae
@date   April 1, 2026

Some comments use annotations that work with
Better Comments by Aaron Bond in VSCode.
"""



import os

## ! ENSURE USER
## ! restricted privileges even when run as root
if os.geteuid() == 0:
    # replaces the root process
    
    ruid:int = os.geteuid()     # root uid
    rgid:int = os.getegid()     # root gid
    if os.environ.get('SUDO_USER'):
        uuid = os.environ.get('SUDO_UID')
        ugid = os.environ.get('SUDO_GID')
        if uuid is None or ugid is None:
            raise Exception("no user id")
        # convert to integers
        uuid, ugid = int(uuid), int(ugid)
        # permanently drop to user
        os.setregid(ugid, ugid)
        os.setreuid(uuid, uuid)
    else:
        raise ValueError("no user")
    

import time
import numpy
import notify2
import textual
import datetime
import textwrap
import threading
import subprocess
import textual.app as tx_app
import textual.widgets as tx_widgets
import textual.containers as tx_containers


## ! GLOBAL VARIABLES
## PATHS
SYSFS_POWER_SUPPLY = "/sys/class/power_supply"
##
# Find power_supply that start with BAT(battery)
BAT_POWER_SUPPLY = [
    x
    for x in os.listdir(SYSFS_POWER_SUPPLY)
    if x.upper().startswith("BAT")
]

## ! CLASSES

## TUI
class main(tx_app.App):
    # the css path for the application
    CSS_PATH = "./assets/bep_tool.tcss"

    # class variables
    PWR_ACTION_LATENCY: str = "1 minute"
    CHARGE_ABS_MAX: int = 80    # absolute allowable max charge
    CHARGE_ABS_MIN: int = 20    # absolute allowable min charge
    CHARGE_CAUTION_MARGIN: int = 5  # notification margin for charge limits
    STATUS: str = "status"
    CAPACITY: str = "capacity"
    

    def compose(self) -> tx_app.ComposeResult: 
        # user defined max/min limits
        self.charge_max: str = str(main.CHARGE_ABS_MAX)   # max charge
        self.charge_min: str = str(main.CHARGE_ABS_MIN)   # min charge

        ## widgets start here:
        yield tx_widgets.Header()
        yield tx_widgets.Footer()

        # Charge Threshold
        yield tx_widgets.Label("Charge Threshold", classes="title")
        with tx_containers.Horizontal(classes="ch_entry"):
            yield tx_widgets.Label("Maximum Charge")
            yield tx_widgets.Input(
                value=self.charge_max,
                max_length=3,
                type="integer",
                id="max_charge")
        with tx_containers.Horizontal(classes="ch_entry"):
            yield tx_widgets.Label("Minimum Charge")
            yield tx_widgets.Input(
                value=self.charge_min,
                max_length=3,
                type="integer",
                id="min_charge")
        
        yield tx_widgets.Pretty([], id="ch_pretty")
        yield tx_widgets.Rule()

        # Notification
        yield tx_widgets.Label("Notification", classes="title")
        with tx_containers.Vertical(classes="notif_entry"):
            yield tx_widgets.Checkbox(
                "Sound on notification",
                value=True,
                id="notif_sound")
            yield tx_widgets.Label("Notification always sent at threshold")
        
        yield tx_widgets.Rule()

        # At Min Charge
        yield tx_widgets.Label("At Min Charge", classes="title")
        with tx_containers.Horizontal(classes="amc_entry"):
            yield tx_widgets.Label("on min charge")
            yield tx_widgets.Select(
                [(x,x) for x in ("sleep", "hibernate", "shutdown")],
                value="sleep",
                id="pwr_select")

        # yield textual.containers.VerticalScroll()
        # # Battery Charging Threshold
        # with textual.containers.Horizontal(id="bch"):
        #     yield textual.widgets.Label("Battery Charging Threshold", id="bch_label")
        #     yield textual.widgets.Input(value="80", max_length=0, type="integer", id="bch_input")
        # # CPPC
        # # AMD PState Operation Mode
        # with textual.containers.Horizontal(id="pstate"):
        #     yield textual.widgets.Label("Energy Performance Preference", id="epp_label")
        #     with textual.containers.Vertical():
        #         # Energy Performance Preference
        #         with textual.widgets.RadioSet(id="epp_set"):
        #             for eppx in eppa:
        #                 yield textual.widgets.RadioButton(
        #                     eppx,
        #                     value=eppx==list(epp)[0]
        #                 )
        #         # Boost
        #         yield textual.widgets.Button("Boost")
    

    def on_mount(self) -> None:
        """use set_interval to poll every second"""

        print("mounting TUI")

        # write limits to sysfs:
        # load and set configuration
        self.write2file_charge_control_threshold("max_charge", str(self.charge_max))
        self.write2file_charge_control_threshold("min_charge", str(self.charge_min))
        self.query_one("#ch_pretty", tx_widgets.Pretty).update([
            "loaded configuration for charge control threshold"
        ])

        # call poll function every 1 second
        self.set_interval(1, self.poll)

        # callback timer for low power:
        # the timer allows the user to take action before the callback
        # if action is taken, the callback is cancelled
        self.lowpwr_callbacktimer = None

    
    async def action_quit(self) -> None:
        self.exit()


    def poll(self) -> None:
        """
        checks against the limits for
        - capacity
        - status
        """

        # poll battery capacity and status
        for BAT in BAT_POWER_SUPPLY:
            BAT_PATH = f"{SYSFS_POWER_SUPPLY}/{BAT}"
            # check that the path contains the sysfs file
            if main.STATUS not in os.listdir(BAT_PATH):
                continue
            if main.CAPACITY not in os.listdir(BAT_PATH):
                continue

            # read and verify values from the file
            # status: ["Charging", "Discharging", "Full", "Not charging", "Unknown"]
            # capacity: 0, ..., 100
            status, capacity = None, None
            with open(f"{BAT_PATH}/{main.STATUS}") as file:
                status = file.read().lower().strip()
                if status is None: raise ValueError(f"status: {status}")
            with open(f"{BAT_PATH}/{main.CAPACITY}") as file:
                capacity = int(file.read().lower().strip())
                if capacity is None: raise ValueError(f"capacity: {capacity}")
            
            # when the device is plugged in and receiving power
            if status in ["charging"]:
                # cancel any existing low power callback timer:
                # timer is only for callback on low power
                # when plugged in, low power callback is irrelevant
                if self.lowpwr_callbacktimer:
                    self.lowpwr_callbacktimer.cancel()
                    self.lowpwr_callbacktimer = None

                # if it is at or below the upper threshold
                if capacity >= int(self.charge_max):
                    Notification.send(
                        """
                        threshold reached.
                        unplug the charger.
                        """,
                        self.query_one("#notif_sound", tx_widgets.Checkbox).value
                    )
                # if it is close to the end threshold
                elif capacity >= int(self.charge_max) - self.CHARGE_CAUTION_MARGIN:
                    Notification.send(
                        f"""
                        {int(self.charge_max) - capacity} % left to max charge.
                        """,
                        self.query_one("#notif_sound", tx_widgets.Checkbox).value
                    )
                else:
                    # hide any notification
                    Notification.hide()
            # when the device is not plugged and is providing power
            elif status in ["discharging"]:
                # if it is at or below the lower threshold, AND
                # the low power callback is not yet set, or has been cancelled
                if capacity <= int(self.charge_min):
                    pwr_select = self.query_one("#pwr_select", tx_widgets.Select).value
                    Notification.send(
                        f"""
                        min charge reached.
                        plugin the charger.
                        {pwr_select} in {self.PWR_ACTION_LATENCY}.
                        """,
                        self.query_one("#notif_sound", tx_widgets.Checkbox).value
                    )
                    # set callback timer for low power action
                    if not self.lowpwr_callbacktimer:
                        self.lowpwr_action()
                # if it is close to the lower threshold
                elif capacity <= int(self.charge_min) + self.CHARGE_CAUTION_MARGIN:
                    Notification.send(
                        f"""
                        {capacity - int(self.charge_min)} % left to min charge.
                        """,
                        self.query_one("#notif_sound", tx_widgets.Checkbox).value
                    )
                else:
                    # hide any notification
                    Notification.hide()
            # when the device is plugged but not charging, due to threshold
            elif status in ["not charging"]:
                Notification.send(
                    """
                    threshold reached.
                    unplug the charger.
                    """,
                    self.query_one("#notif_sound", tx_widgets.Checkbox).value
                )
            # when the device is plugged but not charging, due to capacity
            elif status in ["full"]:
                Notification.send(
                    """
                    max charge reached.
                    unplug the charger.
                    """,
                    self.query_one("#notif_sound", tx_widgets.Checkbox).value
                )
            # unknown state
            else:
                Notification.send(
                    """
                    unknown battery state.
                    """,
                    self.query_one("#notif_sound", tx_widgets.Checkbox).value
                )


    @textual.on(tx_widgets.Input.Submitted)
    def input_changed(self, event: tx_widgets.Input.Submitted) -> None:
        if event.input.id == "max_charge":
            ## validate the max threshold
            # get the min charge as set by the user
            min_charge = self.query_one("#min_charge", tx_widgets.Input).value
            # clamp between the abs max charge and the user min charge
            event.input.value = str(clamp((
                self.CHARGE_ABS_MAX,   # max value is the absolute upper limit
                int(min_charge)         # min value set by user
                ), int(event.value)     # submitted value
            ))
            # the user max charge cannot be equal to the user min value
            if event.input.value == min_charge:
                # display error to user
                self.query_one("#ch_pretty", tx_widgets.Pretty).update([
                    "user max charge cannot be equal to the user min value"
                ])
                # set the value back to previous value
                event.input.value = self.charge_max
                return 
            # write SYSFS max threshold
            self.write2file_charge_control_threshold(event.input.id, event.value)
            self.query_one("#ch_pretty", tx_widgets.Pretty).update([
                "set the SYSFS max threshold"
            ])
            # update the previous value to match
            self.charge_max = event.input.value
        
        elif event.input.id == "min_charge":
            ## validate the min threshold
            # get the max charge as set by the user
            max_charge = self.query_one("#max_charge", tx_widgets.Input).value
            # clamp between the user max charge and the abs min charge
            event.input.value = str(clamp((
                int(max_charge),    # max value set by user
                self.CHARGE_ABS_MIN,    # min value is the absolute lower limit
                ), int(event.value)     # submitted value
            ))
            # the user max charge cannot be equal to the user min value
            if event.input.value == max_charge:
                # display error to user
                self.query_one("#ch_pretty", tx_widgets.Pretty).update([
                    "user max charge cannot be equal to the user min value"
                ])
                # set the value back to previous value
                event.input.value = self.charge_min
                return 
            # write SYSFS min threshold
            self.write2file_charge_control_threshold(event.input.id, event.value)
            self.query_one("#ch_pretty", tx_widgets.Pretty).update([
                "set the SYSFS min threshold"
            ])
            # update the previous value to match
            self.charge_min = event.input.value

        else:
            raise ValueError(f"unknown input widget: {event.input.id}")
        
    
    def write2file_charge_control_threshold(self, id: str, value: str):
        SYSFS_FILE = ""
        if id == "max_charge":
            SYSFS_FILE = "charge_control_end_threshold"
        elif id == "min_charge":
            SYSFS_FILE = "charge_control_start_threshold"

        for BAT in BAT_POWER_SUPPLY:
            BAT_PATH = f"{SYSFS_POWER_SUPPLY}/{BAT}"
            # check that the path contains the sysfs file
            if not SYSFS_FILE in os.listdir(BAT_PATH):
                continue
            # write to the file with su process do
            BAT_FILE = f"{BAT_PATH}/{SYSFS_FILE}"
            SUProcessDo.write(f"echo '{value}' | sudo tee {BAT_FILE}")


    def lowpwr_action(self):
        """
        timeout with time units e.g 1 second, 1 minute, 1 hour
        callback after timeout
        args for the callback
        """        

        # set the callback timer
        def callback():
            # check for the selection in #pwr_select widget
            pwr_select = self.query_one("#pwr_select", tx_widgets.Select).value
            if pwr_select == "sleep":
                subprocess.run(["systemctl", "hybrid-sleep"])
            elif pwr_select == "hibernate":
                subprocess.run(["systemctl", "hibernate"])
            elif pwr_select == "shutdown":
                subprocess.run(["systemctl", "poweroff"])
            # reset the low power callback timer
            self.lowpwr_callbacktimer = None

        # set the callback timer
        self.lowpwr_callbacktimer = CallbackTimer(
            self.PWR_ACTION_LATENCY,
            callback
        )



## ! SINLGETON CLASSES
# Super User Process Do
class SuProcessDo_:
    def __init__(self) -> None:
        # get the password
        import getpass
        pwd = getpass.getpass(prompt=f'[sudo] password for {os.environ.get("USER")}: ')
        
        # open the subprocess
        self.__suproc__ = subprocess.Popen(
            ['sudo', '-S', 'sh'],
            stdin=subprocess.PIPE,
            # stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            text=True
        )

        # pipe the password 
        self.write(pwd)


    def write(self, cmd: str):
        # mainly for vscode error checking
        if self.__suproc__.stdin is None:
            return
        
        # write to pipe
        self.__suproc__.stdin.write(cmd+'\n')
        self.__suproc__.stdin.flush()
## SuProcessDo as a Singleton
SUProcessDo = SuProcessDo_()


## Playback
class Playback_(threading.Thread):
    BLOCKSIZE: int = 4410   # Number of frames per audio chunk
    SAMPLING: int = 44100   # Sampling frequency
    DURATION: float = 1   # Duration of the generated audio in seconds
    AMPLITUDE: float = 1
    SIGNAL = numpy.arange(int(SAMPLING * DURATION)).astype(numpy.float32)
    SIGNAL = 2 * numpy.pi * SIGNAL / SAMPLING
    FREQ_L: float = 440     # Frequency of the sound source in Hz
    FREQ_H: float = 4400    # Frequency of the sound source in Hz


    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.__active__ = True  # is class obj active
        self.__playping__ = False   # play flag; auto reset
        self.start()    # auto-start

    
    def run(self) -> None:
        """use sounddevice exclusively here"""
        import sounddevice

        # Set buffer at length of audio to prevent under/overrun
        sounddevice.default.blocksize = self.BLOCKSIZE
        # Generate the signal
        signal = numpy.sin(self.SIGNAL * self.FREQ_H)
        signal = numpy.column_stack((signal, signal))

        while self.__active__:
            # wait for play ping
            while not self.__playping__:
                time.sleep(1)
            # reset play ping
            self.__playping__ = False

            # Play
            sounddevice.play(signal, self.SAMPLING)
            sounddevice.wait()

        print("playback stopped")


    def play(self):
        """set play flag to true; play sound"""
        self.__playping__ = True


    def stop(self):
        """set active flag to false; quit thread"""
        self.__active__ = False
## Playback as a Singleton
print("creating Playback singleton")
Playback = Playback_()


## Notification
class Notification_(notify2.Notification):
    TITLE = "EPP BATTERY TOOL"

    def __init__(self) -> None:
        # notification object
        super().__init__(None)

        notify2.init(f"{__file__}")
        self.set_urgency(notify2.URGENCY_NORMAL)
        self.set_timeout(0) # No timeout

        self.__last_msg__ = None

    
    def send(self, msg: str, sound: bool) -> None:
        # do not send repetitive messages
        if msg == self.__last_msg__:
            return
        
        # play notification sound
        if sound:
            Playback.play()

        # send the d-bus notification
        self.update(
            Notification.TITLE,
            textwrap.dedent(msg)
        )

        # show the notification
        self.show()

        # save last message
        self.__last_msg__ = msg


    def hide(self) -> None:
        # close the notification instance
        self.close()

        # manually override the id
        # .show usually does not work after .close
        self.id = 0
## Notification as a Singleton
print("creating Notification singleton")
Notification = Notification_()
        

## ! MULTITON CLASSES

## Simple Callback Timer
class CallbackTimer(threading.Thread):
    # convert to common unit
    UNIT_RND = {
        's': 'second',
        'm': 'minute',
        'h': 'hour',
        'd': 'day',
        'w': 'week',
        'second': 'second',
        'minute': 'minute',
        'hour': 'hour',
        'day': 'day',
        'week': 'week',
        'seconds': 'second',
        'minutes': 'minute',
        'hours': 'hour',
        'days': 'day',
        'weeks': 'week',
    }
    # convert the timeout with units to seconds
    SEC_CVRT = {
        "second": 1,
        "minute": 60,  # 60 seconds in a minute
        "hour": 60,     # 60 minutes in an hour
        "day": 24,      # 24 hours in a day
        "week": 7       # 7 days in a week
    }
    
    def __init__(self, timeout:str, callback, args=()) -> None:
        self.__active__ = True

        # ensure space between alpha and numeric
        for i in range(len(timeout) - 1):
            if timeout[i].isdecimal() and timeout[i+1].isalpha():
                timeout = timeout[:i+1] + " " + timeout[i+1:]
                break
        if len(timeout.split()) != 2:
            raise ValueError(f"{timeout} failed to parse")
        
        timeout = timeout.split()[0] + " " + self.UNIT_RND[timeout.split()[1]]
        
        while True:
            # split the string
            value, unit = timeout.split()
            # get the keys in preserved order
            # ! this fails if dict stops preserving order
            sec_cvrt_units = list(self.SEC_CVRT.keys())
            # get the index of the current unit
            idx = sec_cvrt_units.index(unit)
            # stops for 'second' at 1st index
            if idx == 0: break
            # apply multiplier and appropriate unit
            timeout = str(int(value) * self.SEC_CVRT[unit])
            timeout += " " + sec_cvrt_units[idx - 1]

        latency: int = int(timeout.split()[0])
        
        def __callback_timer__():
            # get the current timestamp
            start = datetime.datetime.now().timestamp()
            # start the subsequent poll
            while self.__active__ and datetime.datetime.now().timestamp() - start < latency:
                # sleep for a second
                time.sleep(1)
            # callback if timer is active
            if self.__active__:
                callback(*args)
            else:
                print("callback timer cancelled")

        # setup and start the thread
        super().__init__(
            target=__callback_timer__,
            daemon=True
        )
        self.start()


    def cancel(self):
        self.__active__ = False


def clamp(limit: tuple, value):
    upper = max(limit)
    lower = min(limit)
    return min(upper, max(lower, value))


def EPP_Values():
    # online CPU
    online_cpu = ()
    with open("/sys/devices/system/cpu/online") as file:
        online_cpu = file.read().strip().split('-')
        online_cpu = tuple([int(x) for x in online_cpu])
    # Boost
    boost = set()
    for n in range(online_cpu[0], online_cpu[1] + 1):
        with open(f"/sys/devices/system/cpu/cpu{n}/cpufreq/boost") as file:
            boost.add(file.read().strip())
    # Energy Performance Preferences Available
    eppa = list()
    for n in range(online_cpu[0], online_cpu[1] + 1):
        with open(f"/sys/devices/system/cpu/cpu{n}/cpufreq/energy_performance_available_preferences") as file:
            for x in [x.strip() for x in file.read().strip().split(' ')]:
                if x not in eppa: eppa.append(x)
    # Energy Performance Preference
    epp = set()
    for n in range(online_cpu[0], online_cpu[1] + 1):
        with open(f"/sys/devices/system/cpu/cpu{n}/cpufreq/energy_performance_preference") as file:
            epp.add(file.read().strip())



## ...
if __name__ == "__main__":
    print("starting TUI")
    try:
        # run main tui
        main().run()
    finally:
        Notification.close()
        Playback.stop()
        print("\033[?1049l", end="", flush=True)
