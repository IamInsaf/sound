# 🚀 LOQ JET ENGINE & HARDWARE TELEMETRY SUITE

> **Engineered specifically for Lenovo LOQ 15IRX9 (Machine Type 83DV)**
> - **CPU**: Intel Core i7-13645HX (14 Cores / 20 Threads)
> - **GPU**: NVIDIA GeForce RTX 4050 Laptop GPU (6 GB GDDR6)
> - **RAM**: 32 GB DDR5 | **OS**: Windows 11 64-bit

---

## ⚡ Quick Start: How to Run in 3 Steps

### Option A: Using the One-Click Batch Files (Easiest)

1. **Step 1 — Prepare your Lenovo LOQ**:
   - Plug in your Lenovo power adapter (170W / 230W).
   - Press <kbd>Fn</kbd> + <kbd>Q</kbd> until the power button LED glows **RED** (Performance Mode).

2. **Step 2 — Install Dependencies (One-time setup)**:
   - Open the [`LOQ_Jet_Engine`](file:///c:/Users/user/Desktop/sound/LOQ_Jet_Engine) folder.
   - Double-click **[`setup.bat`](file:///c:/Users/user/Desktop/sound/LOQ_Jet_Engine/setup.bat)**.
   - Wait 5 seconds until it displays `[SUCCESS] Setup complete!`.

3. **Step 3 — Launch the Application**:
   - Double-click **[`run.bat`](file:///c:/Users/user/Desktop/sound/LOQ_Jet_Engine/run.bat)**.
   - The **LOQ JET ENGINE** dark gaming dashboard will open.
   - Choose your intensity (e.g. `100%`) and mode (`CPU + GPU`).
   - Click **`🚀 START JET ENGINE`** to begin the ramp test.

---

### Option B: Running from PowerShell or Command Prompt

Open PowerShell or CMD in this directory (`c:\Users\user\Desktop\sound\LOQ_Jet_Engine`) and run:

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch LOQ Jet Engine
python LOQ_Jet_Engine.py
```

---

## 🛑 How to Stop the Engine

1. **Normal Stop**: Click **`🛑 STOP ENGINE`** at any time.
2. **Instant Emergency Stop**:
   - Click the glowing red **`⚠ EMERGENCY STOP (ESC)`** button, OR
   - Press the <kbd>ESC</kbd> key on your keyboard.
   - All 20 CPU threads and the GPU CUDA worker process will be killed instantly (`SIGKILL`), immediately dropping power draw.

---

## 🛡️ Important Safety Guarantee

> [!IMPORTANT]
> - **ZERO EC / FIRMWARE MODIFICATIONS**: This software **DOES NOT** touch or write to Lenovo Embedded Controller (EC) registers, fan PWM tables, BIOS, voltages, or clock frequencies.
> - **Natural Cooling Dynamics**: It creates legitimate, controlled arithmetic/CUDA compute workloads, allowing your Lenovo LOQ's factory thermal controller to automatically and safely spin up the dual fans.
> - **Built-in Thermal Protection Guard**:
>   - Automatic shutdown triggers if CPU reaches **92°C** or GPU reaches **87°C**.
>   - Warning alerts trigger if CPU reaches **85°C** or GPU reaches **80°C**.
>   - Safety thresholds can be customized safely in the **⚙ SETTINGS** menu.

---

## 📊 Live Dashboard Telemetry & Sensors

| Telemetry | Source | Description |
| :--- | :--- | :--- |
| **CPU Temperature** | Windows ACPI | Real-time reading & live history graph (shows `N/A — sensor unavailable` if Windows blocks ACPI access). |
| **GPU Temperature** | NVIDIA NVML (`nvml.dll`) | Direct hardware reading from RTX 4050 GPU sensor. |
| **CPU Utilization** | Windows Kernel (`psutil`) | Total load across all 20 logical threads + Clock GHz. |
| **GPU Utilization** | NVIDIA NVML (`nvml.dll`) | True compute utilization + live Power Draw (Watts). |
| **Fan Speed** | Windows / ACPI | Fan RPM if exposed, else `N/A — sensor unavailable` without fake numbers. |

---

## 📂 Application Directory Map

```
sound/
├── LOQ_Jet_Engine/                   <-- Main Single-Folder Application
│   ├── LOQ_Jet_Engine.py             <-- Full Python GUI & Workload Engine
│   ├── requirements.txt              <-- Python dependencies
│   ├── setup.bat                     <-- One-click installer
│   ├── run.bat                       <-- One-click launcher
│   ├── README.md                     <-- Detailed Markdown Guide
│   ├── README.txt                    <-- Plaintext Reference
│   └── assets/                       <-- App metadata & configs
│
├── ui_monitor.py                     <-- Compact CPU Rate & Fan Speed UI
├── run_monitor.bat                   <-- Compact UI launcher
└── README.md                         <-- Workspace Documentation
```
