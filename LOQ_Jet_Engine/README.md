# 🚀 LOQ JET ENGINE (Lenovo LOQ 15IRX9 - 83DV)

Controlled Fan Stress & Telemetry Testing Application for:
* **CPU**: Intel Core i7-13645HX (14 Cores / 20 Threads: 6 P-cores + 8 E-cores)
* **GPU**: NVIDIA GeForce RTX 4050 Laptop GPU (6 GB GDDR6)
* **RAM**: 32 GB DDR5 | **OS**: Windows 11 64-bit

---

## 📋 Exact Instructions: How to Run

### Step 1: Lenovo LOQ Performance Prep
1. Plug in your **Lenovo 170W / 230W charger**.
2. Press <kbd>Fn</kbd> + <kbd>Q</kbd> until the power button LED glows **RED** (Performance Mode).

### Step 2: One-Click Setup (First Time Only)
Double-click **[`setup.bat`](file:///c:/Users/user/Desktop/sound/LOQ_Jet_Engine/setup.bat)** to automatically install required packages (`customtkinter`, `psutil`, `pillow`).

### Step 3: Launch Application
Double-click **[`run.bat`](file:///c:/Users/user/Desktop/sound/LOQ_Jet_Engine/run.bat)**.

### Step 4: Run the Jet Engine Fan Test
1. Select your desired intensity (`25%`, `50%`, `75%`, or `100%`).
2. Select your workload mode (`CPU + GPU` recommended).
3. Click **`🚀 START JET ENGINE`**.
4. The application will smoothly ramp the workload:
   $$0\% \longrightarrow 25\% \longrightarrow 50\% \longrightarrow 75\% \longrightarrow 100\%$$
5. Watch your CPU utilization reach 100%, RTX 4050 compute activate, and your laptop's fans spin up to high cooling speed!

### Step 5: Stopping the Test
- **Normal Stop**: Click **`🛑 STOP ENGINE`**.
- **Instant Emergency Stop**: Click **`⚠ EMERGENCY STOP`** or press <kbd>ESC</kbd>.

---

## 🛡️ Safety Systems
- **CPU Thermal Trip**: Stops automatically if CPU reaches **92°C** (Warn: 85°C).
- **GPU Thermal Trip**: Stops automatically if GPU reaches **87°C** (Warn: 80°C).
- **Settings Menu**: Click **`⚙ SETTINGS`** in the app to adjust safety thresholds.
- **Zero EC Writes**: No dangerous fan register or BIOS modifications.
