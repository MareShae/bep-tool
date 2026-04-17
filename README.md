# BATTERY ENERGY PREFERENCE TOOL (BEP TOOL)
written in KDE Neon


[1. Battery Operation Range]
Charging battery (close) to full or discharging (close) to empty can rapidly deteriorate battery life. Placing limits for charging and discharging can protect battery health and can maximize battery usage.

Battery replacement can be costly if replacing with an OEM, but less expensive with off-brand options, which can be hit-or-miss for battery quality and life expectancy.

The KDE Neon tools allow for setting the battery charge threshold but it is not persistent and resets after reboot. Simple service scripts do this but this also allows for explicitly setting your threshold, charge thresholds and automated actions with notification reminders.

[2. Battery Performance]
EPP replaces cpufreq for better DVFS performance and efficiency. DVFS is based on workload, temperature and other factors to more precisely scale cpu frequency, which applies optimizes power and effectually protect battery life.

KDE Neon power profile is limited to 3 hints: power, balanced, performance.
CPU preferences expands balance hints to: balance performance and balance power


[· Function]
1. Automatically set the (dis)charging limits
   Sends notifications when charge approaches these limits
   (Hybrid-)Sleep/hibernate/power-off if charge breaches lower limit
2. Exposes energy performance options