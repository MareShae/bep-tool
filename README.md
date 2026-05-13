# Battery Energy Preference Tool (bep tool) 🔋

A Python-based system utility designed to protect the health and extend the life of lithium-ion batteries by exposing charging thresholds to users, and using notify2 notifications and sound to alert users when the battery charge approaches and reaches the thresholds.

![app screenshot](/assets/screenshot.png)

## The Problem

Charging a lithium-ion battery (close) to full, or discharging (close) to empty, can rapidly deteriorate battery life. Placing limits for charging and discharging can protect battery health and can maximize battery usage.

Battery replacement can be costly if replacing with an OEM, but less expensive with off-brand options, which can be hit-or-miss for battery quality and life expectancy.


## What It Does

This project was written in KDE Neon. The in-built KDE Neon power management allows for setting the battery charge threshold, but it is not persistent and resets after reboot. Simple service scripts do this, however, **bep-tool** also allows for explicitly setting charge thresholds and automated actions with notification alerts.

**bep-tool** allows users to:
+ control start and end charging threshold
+ toogle notification and audio alerts
+ choose an automatic action at lower power threshold
   + hybird-sleep
   + hibernate
   + power-off

https://github.com/user-attachments/assets/dffc7228-e248-4489-a92a-903415387507


## Setup & Run
To install, in a terminal:
```
git clone https://github.com/MareShae/bep-tool
cd bep-tool

beptoolmgr --install
```

To uninstall:
```
beptoolmgr --install
```

The user app terminal UI. In a terminal, run:
```
beptoolmgr --run
```