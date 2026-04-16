# BATTERY ENERGY PREFERENCE TOOL (BEP TOOL)
written in KDE Neon


[1. Battery Operation Range]
Charging battery (close) to full or discharging (close) to empty can rapidly deteriorate battery life. Placing limits for charging and discharging can protect battery health and can maximize battery usage.

Battery replacement can be costly if replacing with an OEM, but less expensive with off-brand options, which can be hit-or-miss for battery quality and life expectancy.

The KDE Neon tools allow for setting the battery charge threshold but it is not persistent and resets after reboot. Other scripts do this but this allows includes explicitly setting your threshold, charge thresholds and automated actions with notification reminders.


[· Function]
1. Automatically set the (dis)charging limits
   Sends notifications when charge approaches these limits
   (Hybrid-)Sleep/hibernate/power-off if charge breaches lower limit