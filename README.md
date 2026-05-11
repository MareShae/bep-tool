# Battery Energy Preference Tool (BEP Tool) 🔋

A Python-based system utility designed to protect the health and extend the life of lithium-ion batteries by exposing charging thresholds to users, and using notify2 notifications and sound to alert users when the battery charge approaches and reaches the thresholds.

![image of the app](/assets/screenshot.png)


## The Problem

Charging a lithium-ion battery (close) to full, or discharging (close) to empty, can rapidly deteriorate battery life. Placing limits for charging and discharging can protect battery health and can maximize battery usage.

Battery replacement can be costly if replacing with an OEM, but less expensive with off-brand options, which can be hit-or-miss for battery quality and life expectancy.


## What It Does

This project was written in KDE Neon. The in-built KDE Neon power management allows for setting the battery charge threshold but it is not persistent and resets after reboot. Simple service scripts do this, however, **bep-tool** also allows for explicitly setting charge thresholds and automated actions with notification reminders.

**bep-tool** allows users to:
+ set start and end charging threshold
+ toogle notification and sound alert
+ choose what to do when the charge drops to threshold
   + hybird-sleep
   + hibernate
   + power-off


## Setup & Run
To it up setup, in a terminal:
```
git clone https://github.com/MareShae/bep-tool
cd bep-tool

beptoolmgr --setup
```

This is a terminal user interface (TUI). To run:
```
beptoolmgr --run
```

It requires a password once at start to grant write permissions to sysfs. It is ONLY used to write charge threshold(s). The script automatically ensures that it runs in user space.