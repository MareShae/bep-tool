"""
@author mareshae
@date   May 10, 2026

Some comments use annotations that work with Better Comments by Aaron Bond in VSCode.
"""

import os
import zmq
import time
import numpy
import paths
import notify2
import textual
import textwrap
import threading
import textual.app as app
import textual.widgets as widgets
import textual.containers as containers



# the absolute path of this script
abs_path = os.path.abspath(__file__)
dir_path = os.path.dirname(abs_path)



## ZeroMQ IPC Client

class ipcClient:
    
    # create the zmq socket
    zmq_context = zmq.Context()
    zmq_socket = zmq_context.socket(zmq.PAIR)
    
    # insert abstract namespace `@` to bypass linux limitations on file permissions
    zmq_socket.connect(f"ipc://@{dir_path}/my_socket")

    # allocate timeout to recv
    zmq_socket.setsockopt(zmq.RCVTIMEO, 10000) #  10 seconds

    @staticmethod
    def send(method: str, path: str, body: dict = {}) -> dict | None:
        """
        packages a request in discount HTTPS
        waits for a response for allocated time at initialization
        """

        package = {
            "method": method,
            "path": path,
            "body": body
        }
        print(f"sending package to backend: {package}")

        try:
            # send the package
            ipcClient.zmq_socket.send_json(package)
            print("waiting for a response")
            # return the response to client
            return ipcClient.zmq_socket.recv_json()
        except Exception as err:
            print(f"failed to send package: {err}")
            return None


class tui(app.App):
    # the css path for the application
    CSS_PATH = "./bep_tool.tcss"
    

    # this is used to alert the user when the capacity approaches cap
    CAUTION_MARGIN = 5

    def compose(self) -> app.ComposeResult:
        # request the value from backend
        response = ipcClient.send("GET", paths.BATTERY_T)
        if response is None: exit(1)
        batt = response["body"]

        # encapsulation

        yield widgets.Header()
        yield widgets.Footer()

        # threshold

        yield widgets.Label("Charge Thresholds", classes="title")

        with containers.Horizontal(classes="ch_entry"):
            yield widgets.Label("Max")

            yield widgets.Label(
                f"{batt['max']}",
                id = paths.CHARGE_CONTROL_END_THRESHOLD_T
                )

            yield widgets.Input(
                value = "",
                max_length = 3,
                type = "integer",
                id = f"{paths.CHARGE_CONTROL_END_THRESHOLD_T}_buffer"
                )

        with containers.Horizontal(classes="ch_entry"):
            yield widgets.Label("Min")

            yield widgets.Label(
                f"{batt['min']}",
                id = paths.CHARGE_CONTROL_START_THRESHOLD_T
                )

            yield widgets.Input(
                value = "",
                max_length = 3,
                type = "integer",
                id = f"{paths.CHARGE_CONTROL_START_THRESHOLD_T}_buffer"
                )

        yield widgets.Rule()

        # Notification

        widgets.Label("Notification", classes="title")

        with containers.Vertical(classes="notif_entry"):
            yield widgets.Checkbox(
                "Notification audio alert",
                value = True,
                id = "notif_sound"
            )

            yield widgets.Label("Notification always sent")

        yield widgets.Rule()

        # Low Power Action

        yield widgets.Label("Low power action", classes="title")

        with containers.Horizontal(classes="amc_entry"):
            yield widgets.Label("on min")

            # request the value from backend
            response = ipcClient.send("GET", paths.LOW_POWER_ACTIONS_AVAILABLE_T)
            if response is None: exit(1)
            options = response["body"]["value"]

            yield widgets.Select(
                [(x, x) for x in options],
                value = batt["lowpwr_action"],
                id = paths.LOW_POWER_ACTIONS_AVAILABLE_T
            )


    def on_mount(self) -> None:
        """
        use set_interval to poll every second
        """
        
        # ticks every second
        self.set_interval(10, self.on_tick)

        # flag for on_tick
        self.on_tick_flag: bool = False

    
    # wrapper for asyn network
    async def send_to_ipc_server(self, method: str, path: str, body: dict={}):
        return ipcClient.send(method, path, body)
    
    
    async def on_tick(self) -> None:
        """
        sync backend with frontend
        """

        # assert flag to block concurrent instances
        if self.on_tick_flag: return
        # toggle flag on to prevent concurrent instances
        self.on_tick_flag = True

        try:

            # sync tui values on display with backend

            # request the value from backend
            response = await self.send_to_ipc_server("GET", paths.BATTERY_T)
            if response is None: exit(1)
            batt = response["body"]

            wdgt = self.query_one(f"#{paths.CHARGE_CONTROL_END_THRESHOLD_T}", widgets.Label)
            if str(wdgt.content) != str(batt["max"]):
                wdgt.update(str(batt["max"]))

            wdgt = self.query_one(f"#{paths.CHARGE_CONTROL_START_THRESHOLD_T}", widgets.Label)
            if str(wdgt.content) != str(batt["min"]):
                wdgt.update(str(batt["min"]))

            wdgt = self.query_one(f"#{paths.LOW_POWER_ACTIONS_AVAILABLE_T}", widgets.Select)
            if wdgt.value != str(batt["lowpwr_action"]):
                wdgt.value = str(batt["lowpwr_action"])

            # notifications and alerts

            sound = self.query_one("#notif_sound", widgets.Checkbox).value

            # when the device is plugged in and receiving power
            if batt["status"] in ["charging"]:
                if batt["capacity"] >= batt["max"]:
                    Notification.send(
                        "Charging Above Set Capacity",
                        "unplug the device to protect battery health.",
                        sound
                    )

                elif batt["capacity"] >= batt["max"] - self.CAUTION_MARGIN:
                    Notification.send(
                        "Capacity Almost Fully Charged",
                        f"{batt['max'] - batt['capacity']} % remaining.",
                        sound
                    )

                else:
                    Notification.hide()

            # # when the device is not plugged and is providing power
            elif  batt["status"] in ["discharging"]:
                if batt["capacity"] <= batt["min"]:
                    Notification.send(
                        "Utilization Below Set Capacity",
                        f"device set to {batt['lowpwr_action']}. plugin the device to cancel.",
                        sound)

                elif batt["capacity"] <= batt["min"] + self.CAUTION_MARGIN:
                    Notification.send(
                        "Capacity Almost Fully Discharged",
                        f"{batt['capacity'] - batt['min']} % remaining.",
                        sound
                    )

                else:
                    Notification.hide()

            # when the device is plugged but not charging, due to threshold
            elif  batt["status"] in ["not charging"]:
                Notification.send(
                    "Capacity Optimized",
                    "the device can be unplugged.",
                    sound
                )

            # when the device is plugged but not charging, due to capacity
            elif  batt["status"] in ["full"]:
                Notification.send(
                    "Capacity is Full",
                    "unplug the device to prevent battery stress.",
                    sound
                )

            # unknown
            else:
                Notification.send(
                    "Battery Status is Unknown",
                    "Ꭓ̷[Ø𝝭_╟─╫╢¿?]▒ɬϾ_╬═[ΞЯЯ_Ø_NULL]Шя7:∅",
                    sound
                )

        except Exception as err:
            print(err)

        # toggle flag off to allow next instance
        self.on_tick_flag = False


    @textual.on(widgets.Input.Submitted)
    async def input_changed(self, event:widgets.Input.Submitted) -> None:
        """
        values are pushed in the backend
        """

        if event.input.id is None: return

        path = event.input.id.replace("_buffer", "")
        response = ipcClient.send("POST", path, {"value": event.value})
        if response is None: exit(1)

        wdgt = self.query_one(f"#{event.input.id}", widgets.Input)
        wdgt.value = ""



class Notification:
    notify = notify2.Notification(None)

    notify2.init(f"bep tool")

    notify.set_urgency(notify2.URGENCY_NORMAL)
    notify.set_timeout(0) # no timeout

    # save the last message to prevent crash
    __last_msg__: str = ""

    # audio alert

    BLOCKSIZE: int = 4410   # Number of frames per audio chunk
    SAMPLING: int = 44100   # Sampling frequency
    DURATION: float = 1   # Duration of the generated audio in seconds
    AMPLITUDE: float = 1
    SIGNAL = numpy.arange(int(SAMPLING * DURATION)).astype(numpy.float32)
    SIGNAL = 2 * numpy.pi * SIGNAL / SAMPLING
    FREQ_L: float = 440     # Frequency of the sound source in Hz
    FREQ_H: float = 4400    # Frequency of the sound source in Hz

    __active__ = True  # is class obj active
    __play__ = 0   # play flag; auto reset


    @staticmethod
    def playback():
        """
        use sounddevice exclusively here
        """
        
        import sounddevice

        # Set buffer at length of audio to prevent under/overrun
        sounddevice.default.blocksize = Notification.BLOCKSIZE
        # Generate the signal
        signal = numpy.sin(Notification.SIGNAL * Notification.FREQ_H)
        signal = numpy.column_stack((signal, signal))

        while True:
            # wait for play ping
            while not Notification.__play__:
                if not Notification.__active__:
                    return
                
                time.sleep(1)
            
            # reset play ping
            Notification.__play__ -= 1

            # Play
            try:
                sounddevice.play(signal, Notification.SAMPLING)
                sounddevice.wait()

            except Exception as err:
                print(f"unable to play audio: {err}")

    threading.Thread(target=playback).start()
    

    @staticmethod
    def send(title: str, msg: str, sound: bool, factor:int=1):
        # no repetitive messages
        if msg == Notification.__last_msg__:
            return
        
        try:
            # play notification sound
            if sound:
                Notification.alert(factor)

            # send the notification via DBus
            Notification.notify.update(
                textwrap.dedent(title),
                textwrap.dedent(msg)
            )

            # show the notification
            Notification.notify.show()

        except Exception as err:
            print(f"unable to send notification: {err}")

        # save the last message
        Notification.__last_msg__ = msg


    @staticmethod
    def hide():
        # close the notification instance
        Notification.notify.close()

        # manually override the id
        # .show does not usually work after .close
        Notification.notify.id = 0


    @staticmethod
    def alert(factor):
        """
        set play flag to true
        this removes the block in the thread to play the sound
        """
        Notification.__play__ = factor

    
    @staticmethod
    def close():
        """set active flag to false; quit thread"""
        Notification.notify.close()
        Notification.__active__ = False



if __name__ != "__main__":
    exit(1)


## ! PRIVILEGES
if os.geteuid() == 0:
    exit(2)


# start the textual ui
try:
    tui().run()
finally:
    Notification.close()
