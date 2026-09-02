==============================================================================
                          LOQ JET ENGINE
          Aero Dynamic Fan Stress & Telemetry Utility
       Specifically Configured for Lenovo LOQ 15IRX9 (Type 83DV)
       CPU: Intel Core i7-13645HX (14 Cores / 20 Threads)
       GPU: NVIDIA GeForce RTX 4050 Laptop GPU (6 GB GDDR6)
       RAM: 32 GB DDR5 | OS: Windows 11 64-bit
==============================================================================

[IMPORTANT SAFETY GUARANTEE]
This utility DOES NOT modify or flash your laptop's Embedded Controller (EC),
fan PWM registers, BIOS, voltages, or clock frequencies.
It generates controlled, legitimate CPU and GPU compute workloads, allowing
Lenovo's factory thermal controller to automatically and safely ramp the dual
fans to maximum cooling velocity.

------------------------------------------------------------------------------
[QUICK START GUIDE]
------------------------------------------------------------------------------
1. (One-time) Double-click `setup.bat` to install dependencies.
2. Double-click `run.bat` to launch the LOQ Jet Engine application.
3. Lenovo LOQ Best Practice:
   - Connect your original Lenovo 170W/230W charger.
   - Press Fn + Q until the power button LED turns RED (Performance Mode).
4. Select your desired intensity (25%, 50%, 75%, 100%) and mode (CPU + GPU).
5. Click "🚀 START JET ENGINE".
6. The app will smoothly ramp up (0% -> 25% -> 50% -> 75% -> 100%).
7. To stop normally: Click "🛑 STOP ENGINE".
8. For immediate instant shutdown: Click "⚠ EMERGENCY STOP" or press [ESC].

------------------------------------------------------------------------------
[TELEMETRY & SENSORS]
------------------------------------------------------------------------------
- CPU Utilization: Queried directly from Windows OS kernel.
- GPU Utilization & Temp: Queried directly via NVIDIA Driver NVML API (nvml.dll).
- CPU Temp & Fan RPM: Queried via Windows ACPI/WMI sensors. If the Windows OS
  or OEM driver restricts low-level sensor access, the display will strictly
  show "N/A — sensor unavailable". No fake sensor values are ever reported.

------------------------------------------------------------------------------
[THERMAL PROTECTION SYSTEM]
------------------------------------------------------------------------------
The built-in Thermal Safety Guard actively monitors temperatures and trips an
automatic emergency shutdown if limits are exceeded:
- CPU Warning Limit: 85°C | CPU Auto-Stop Limit: 92°C
- GPU Warning Limit: 80°C | GPU Auto-Stop Limit: 87°C
These thresholds can be adjusted within safe boundaries in the Settings menu.

------------------------------------------------------------------------------
[FILES IN THIS FOLDER]
------------------------------------------------------------------------------
- LOQ_Jet_Engine.py : Main Python application source
- requirements.txt  : Python dependencies (customtkinter, psutil, pillow)
- setup.bat         : Automated package installer
- run.bat           : One-click launcher
- README.txt        : This guide
- assets/           : Application assets and visual configuration

==============================================================================
