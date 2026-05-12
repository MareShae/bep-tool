import glob

CHARGE_CONTROL_END_THRESHOLD: str = glob.glob("/sys/class/power_supply/BAT*/charge_control_end_threshold")
CHARGE_CONTROL_START_THRESHOLD: str = glob.glob("/sys/class/power_supply/BAT*/charge_control_start_threshold")

STATUS: str = glob.glob("/sys/class/power_supply/BAT*/status")
CAPACITY: str = glob.glob("/sys/class/power_supply/BAT*/capacity")


CHARGE_CONTROL_END_THRESHOLD_T = "CHARGE_CONTROL_END_THRESHOLD"
CHARGE_CONTROL_START_THRESHOLD_T = "CHARGE_CONTROL_START_THRESHOLD"

LOW_POWER_ACTIONS_AVAILABLE_T = "LOW_POWER_ACTION_AVAILABLE"
LOW_POWER_ACTION_T = "LOW_POWER_ACTION"

BATTERY_T = "BATTERY"