# Battery Energy Preference Tool (BEP Tool) 🔋

A Python-based system utility designed to protect the health and extend the life of lithium-ion batteries by exposing charging thresholds to users, and using DBus notifications and sound to alert users when the battery charge approaches and reaches the thresholds. It was written in KDE Neon.

![image of the app](/assets/screenshot.png)


## The Problem

Charging a lithium-ion battery (close) to full, or discharging (close) to empty, can rapidly deteriorate battery life. Placing limits for charging and discharging can protect battery health and can maximize battery usage.

Battery replacement can be costly if replacing with an OEM, but less expensive with off-brand options, which can be hit-or-miss for battery quality and life expectancy.

## What It Does

The in-built KDE Neon power management allows for setting the battery charge threshold but it is not persistent and resets after reboot. Simple service scripts do this, however, **bep-tool** also allows for explicitly setting charge thresholds and automated actions with notification reminders.

**bep-tool** allows users to:
+ set start and end charging threshold
+ toogle DBus notification and sound
+ choose what to do when the charge drops to threshold
   + hybird-sleep
   + hibernate
   + power-off

## Installation & Setup
To install, in a terminal:
```
git clone https://github.com/MareShae/bep-tool
cd bep-tool
python -m venv venv
venv/bin/pip install -r requirements.txt
```

To uninstall, delete the /bep-tool folder.


## Run
The application runs in a terminal.
To run, in a terminal:
```
./venv/bin/python3 ./bep-tool
```
It requires a password once at start.

It can also be placed in a .desktop file and applied to auto-start.
```
[Desktop Entry]
Type=Application
Name=bep-tool
Comment=Runs bep-tool in a terminal
Exec=/path/to/ven/python3 /path/to/bep-tool.py
Icon=utilities-terminal
Terminal=true
Categories=System;Utility;
```