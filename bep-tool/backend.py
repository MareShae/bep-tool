"""
@author mareshae
@date   May 10, 2026

Some comments use annotations that work with Better Comments by Aaron Bond in VSCode.

@description Backend service for the bep-tool
The backend sets the sysfs files using its su privileges.
The bep-tool is meant as a battery critical service, therefore,
regardless of the limitations of access to DBus notify and audio devices
the tool should run.
For instance, the charging threshold should be set
even when a user has not logged in.
Also, regardless of which user is logged in,
the service must be consistently on, instead of restarted for every instance.
communicates with the 
"""

import os
import zmq
import enum
import math
import time
import socket
import datetime
import threading
import subprocess



# the absolute path of this script
abs_path = os.path.abspath(__file__)
dir_path = os.path.dirname(abs_path)



## SysFS

class UserDo:
    @staticmethod
    def write(cmd: str):
        # write to stdin and wait for stdout or stderr
        proc = subprocess.Popen(
            ["/usr/bin/bash", "-c", cmd],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # read output from the PIPE
        stdout, stderr = proc.communicate()

        # strip whitespaces from the output
        return stdout.lower().strip() if stdout else stdout, stderr


    @staticmethod
    def write_to_file(glob_paths, value):
        for path in glob_paths:
            _, stderr = UserDo.write(f"echo '{value}' | sudo tee {path}")
            if stderr is not None:
                print(stderr)


    @staticmethod
    def read_from_file(glob_paths):
        contents = []

        for path in glob_paths:
            stdout, stderr = UserDo.write(f"cat {path}")

            if stderr is not None:
                print(stderr)

            contents.append(stdout)

        return contents



## Power Supply

class BAT:
    # Current status
    CAP: int = 0
    STAT: str = ""

    # Lower power
    class LOWPWR_ACTIONS_AVAILABLE(enum.Enum):
        HYBRID_SLEEP = "hybrid-sleep"
        HIBERNATE    = "hibernate"
        POWEROFF     = "poweroff"

    LOWPWR_ACTION: LOWPWR_ACTIONS_AVAILABLE = LOWPWR_ACTIONS_AVAILABLE.HYBRID_SLEEP
    LOWPWR_ACTION_LATENCY: int = 60 # seconds
    LOWPWR_ACTOR: threading.Thread | None = None

    # Threshold
    ABS_MAX: int = 80   # cannot be more than this
    ABS_MIN: int = 20   # cannot be less than this
    MAX: int = 80
    MIN: int = 20


    @staticmethod
    def analyze(cap: str, stat: str):
        BAT.CAP = int(cap)
        BAT.STAT = stat
        
        if stat in  ["charging"]:
            return BAT.on_charging()
        
        if stat in ["discharging"]:
            return BAT.on_discharging()
        
        if stat in ["not charging"]:
            return BAT.on_not_charging()
        
        if stat in ["full"]:
            return BAT.on_full()


    @staticmethod
    def on_charging():
        """
        cancel the exist low power action

        simply setting to None stops the timer
        """

        BAT.LOWPWR_ACTOR = None


    @staticmethod
    def on_discharging():
        """
        setup (maybe) a low power action
        """

        # if already set
        if BAT.LOWPWR_ACTOR: return
        # if capacity criteria is not fulfilled
        if BAT.CAP > BAT.MIN: return

        def actor():
            start = datetime.datetime.now().timestamp()
            
            while BAT.LOWPWR_ACTOR and datetime.datetime.now().timestamp() - start < BAT.LOWPWR_ACTION_LATENCY:
                # sleep for one second
                time.sleep(1)
            
            if BAT.LOWPWR_ACTOR:
                BAT.low_power_action()
                BAT.LOWPWR_ACTOR = None

        # start in new thread
        BAT.LOWPWR_ACTOR = threading.Thread(target=actor, daemon=True)
        BAT.LOWPWR_ACTOR.start()


    @staticmethod
    def on_not_charging():
        pass


    @staticmethod
    def on_full():
        pass


    @staticmethod
    def low_power_action():
        UserDo.write(f"systemctl {BAT.LOWPWR_ACTION.value}")



## ZeroMQ IPC Server

class ipcServer:

    # create the zmq socket
    zmq_context = zmq.Context()
    zmq_socket = zmq_context.socket(zmq.PAIR)

    # insert abstract namespace `@` to bypass linux limitations on file permissions
    zmq_socket.bind(f"ipc://@{dir_path}/my_socket")


    @staticmethod
    def recv() -> dict | None:
        """
        search for pushed context in the socket
        does not wait, to allow the main loop to run
        """

        try:
            return ipcServer.zmq_socket.recv_json(flags=zmq.DONTWAIT)
        except zmq.Again:
            return None
        

    @staticmethod
    def send(status: int, body: dict = {}):
        """
        packages a response in discount HTTPS
        does not wait for a response from clients
        """

        ipcServer.zmq_socket.send_json({
            "status": status,
            "body": body
        })


    @staticmethod
    def analyze(req: dict):
        """
        reads client requests and respond accordingly
        """
        
        status, value = 200, {}
        try:
            if req["method"] == "POST":

                if req["path"] == paths.CHARGE_CONTROL_END_THRESHOLD_T:
                    ipcServer.on_post_charge_control_end_threshold(req["body"])

                elif req["path"] == paths.CHARGE_CONTROL_START_THRESHOLD_T:
                    ipcServer.on_post_charge_control_start_threshold(req["body"])

            elif req["method"] == "GET":

                if req["path"] == "PING":
                    value = {"PONG": "success"}

                elif req["path"] == paths.BATTERY_T:
                    value = {
                        "abs_max": BAT.ABS_MAX,
                        "abs_min": BAT.ABS_MIN,
                        "max": BAT.MAX,
                        "min": BAT.MIN,
                        "capacity": BAT.CAP,
                        "status": BAT.STAT,
                        "lowpwr_action": BAT.LOWPWR_ACTION.value
                    }

                elif req["path"] == paths.LOW_POWER_ACTIONS_AVAILABLE_T:
                    value = {"value": tuple([x.value for x in BAT.LOWPWR_ACTIONS_AVAILABLE])}

                elif req["path"] == paths.LOW_POWER_ACTION_T:
                    value = {"value": BAT.LOWPWR_ACTION.value}

                elif req["path"] == paths.CHARGE_CONTROL_END_THRESHOLD_T:
                    value = ipcServer.on_get_charge_control_end_threshold(req["body"])

                elif req["path"] == paths.CHARGE_CONTROL_START_THRESHOLD_T:
                    value = ipcServer.on_get_charge_control_start_threshold(req["body"])

            else:
                raise ValueError(f"method: {req['method']}")
            
        except KeyError as e:
            status = 400

        except ValueError as e:
            status = 400

        ipcServer.send(status, value)
            
            
    @staticmethod
    def on_post_charge_control_end_threshold(body: dict):
        # clamp the value to absolute max and user min
        value = min(BAT.ABS_MAX, max(int(body["value"]), BAT.MIN))
        # user max must not be equal to user min
        if value == BAT.MIN: return

        UserDo.write_to_file(paths.CHARGE_CONTROL_END_THRESHOLD, value)
        BAT.MAX = value
            

    @staticmethod
    def on_post_charge_control_start_threshold(body: dict):
        # clamp the value to user max and absolute min
        value = min(BAT.MAX, max(int(body["value"]), BAT.ABS_MIN))
        # user min must not be equal to user min
        if value == BAT.MAX: return

        UserDo.write_to_file(paths.CHARGE_CONTROL_START_THRESHOLD, value)
        BAT.MIN = value
            
            
    @staticmethod
    def on_post_low_power_actions_available(body: dict):
        value = body["value"]
        BAT.LOWPWR_ACTION = BAT.LOWPWR_ACTIONS_AVAILABLE(value)
            

    @staticmethod
    def on_get_charge_control_end_threshold(body: dict):
        return {
            "value": BAT.MAX
        }


    @staticmethod
    def on_get_charge_control_start_threshold(body: dict):
        return {
            "value": BAT.MIN
        }



if __name__ != "__main__":
    exit(1)


import paths


## ! PRIVILEGES
if os.geteuid() != 0:
    exit(2)


## ! SCRIPT IS A SINGLE INSTANCE
si_lock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

#  abstract socket prefixed with `\0`
try:
    si_lock.bind('\0bep-tool-backend-singleton-lock')

except socket.error as err:
    print("bep-tool backend already runnig: {err}")
    exit()


try:

    # on start:
    # write threshold values to sysfs
    UserDo.write_to_file(paths.CHARGE_CONTROL_END_THRESHOLD, BAT.MAX)
    UserDo.write_to_file(paths.CHARGE_CONTROL_START_THRESHOLD, BAT.MIN)


    # on tick
    while True:
        # sleep for one second
        now: float = datetime.datetime.now().timestamp()
        time.sleep(math.ceil(now) - now)

        # access the current BAT capacity and status
        status, err = UserDo.write(f"cat {paths.STATUS[0]}")
        capacity, err = UserDo.write(f"cat {paths.CAPACITY[0]}")

        # analyze the capacity and status
        BAT.analyze(capacity, status)

        # read from zmq
        req = ipcServer.recv()
        if req is None: continue
        
        print(req)

        # client will be waiting for a response:
        # analyse the request and correspond accordingly
        ipcServer.analyze(req)

except KeyboardInterrupt:
    print("\n[Ctrl + C] detected. Graceful shutdown ...")
