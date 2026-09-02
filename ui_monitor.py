import sys
import time
import math
import psutil
import threading
import multiprocessing
import tkinter as tk
import customtkinter as ctk

# Set appearance and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def cpu_stress_worker(stop_event):
    """Worker process to generate 100% CPU load on a single core."""
    x = 1.0
    while not stop_event.is_set():
        x = (x * 3.141592653589793) % 1000000.0

class FanVisualizer(tk.Canvas):
    """Custom Canvas that renders a smooth animated rotating fan."""
    def __init__(self, master, size=150, **kwargs):
        super().__init__(
            master, 
            width=size, 
            height=size, 
            bg="#161822", 
            highlightthickness=0, 
            **kwargs
        )
        self.size = size
        self.center = size / 2
        self.radius = size / 2 - 12
        self.blade_count = 7
        self.angle = 0.0
        self.rpm = 1200.0
        self.draw_fan()

    def update_angle(self, rpm):
        """Update angle based on current RPM."""
        self.rpm = max(0.0, rpm)
        # Calculate angular velocity (degrees per 30ms frame)
        # At 3000 RPM = 50 RPS = 18000 deg/sec = 540 deg/frame (modulo for smooth illusion)
        rot_speed = (self.rpm / 60.0) * 360.0 * 0.033
        self.angle = (self.angle + rot_speed) % 360.0
        self.draw_fan()

    def draw_fan(self):
        self.delete("all")
        cx, cy, r = self.center, self.center, self.radius

        # Outer casing ring
        self.create_oval(cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4, outline="#2b2d3c", width=3)
        self.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#1f2333", width=2, fill="#12131a")

        # Speed glow effect
        if self.rpm > 3500:
            glow_color = "#ff4757"
        elif self.rpm > 2200:
            glow_color = "#ffa502"
        else:
            glow_color = "#00d2d3"

        self.create_oval(cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2, outline=glow_color, width=1)

        # Draw blades
        blade_color = "#3d4860" if self.rpm < 2500 else ("#4e5d7d" if self.rpm < 3800 else "#6a4f78")
        accent_color = glow_color

        for i in range(self.blade_count):
            base_deg = self.angle + (i * (360.0 / self.blade_count))
            rad1 = math.radians(base_deg)
            rad2 = math.radians(base_deg + 28)
            rad3 = math.radians(base_deg + 14)

            # Hub attachment points
            hub_r = r * 0.28
            x1 = cx + hub_r * math.cos(rad1)
            y1 = cy + hub_r * math.sin(rad1)

            # Outer tip points
            tip_r = r * 0.90
            x2 = cx + tip_r * math.cos(rad2)
            y2 = cy + tip_r * math.sin(rad2)

            x3 = cx + (tip_r * 0.95) * math.cos(rad3)
            y3 = cy + (tip_r * 0.95) * math.sin(rad3)

            # Blade polygon
            self.create_polygon(
                [cx, cy, x1, y1, x3, y3, x2, y2],
                fill=blade_color,
                outline=accent_color if (i % 2 == 0) else "#2f3542",
                width=1,
                smooth=True
            )

        # Center hub
        self.create_oval(cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r, fill="#1e272e", outline="#485460", width=2)
        inner_hub = hub_r * 0.45
        self.create_oval(cx - inner_hub, cy - inner_hub, cx + inner_hub, cy + inner_hub, fill=glow_color, outline="")

class CPURateFanMonitor(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("AeroPulse | CPU Rate & Fan Speed Monitor")
        self.geometry("780x620")
        self.minsize(720, 580)
        self.configure(fg_color="#0e0f14")

        # Hardware & Stress State
        self.total_cores = multiprocessing.cpu_count()
        self.stress_processes = []
        self.stop_event = multiprocessing.Event()
        self.is_stressed = False
        self.emergency_halted = False

        # Metrics state
        self.current_cpu_percent = 0.0
        self.current_freq_ghz = 0.0
        self.max_freq_ghz = 0.0
        self.current_fan_rpm = 1450.0
        self.target_fan_rpm = 1450.0
        self.hardware_fan_detected = False

        # Discover initial frequency specs
        try:
            freq = psutil.cpu_freq()
            if freq:
                self.max_freq_ghz = (freq.max if freq.max and freq.max > 0 else (freq.current or 2600.0)) / 1000.0
                self.current_freq_ghz = (freq.current or 2000.0) / 1000.0
        except Exception:
            self.max_freq_ghz = 3.5
            self.current_freq_ghz = 2.4

        self.setup_ui()

        # Protocol cleanup
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Global Hotkey for Emergency Stop (Escape or Space)
        self.bind("<Escape>", lambda e: self.trigger_emergency_stop())
        self.bind("<space>", lambda e: self.trigger_emergency_stop() if self.is_stressed else None)

        # Background update threads
        self.running = True
        self.metrics_thread = threading.Thread(target=self.metrics_loop, daemon=True)
        self.metrics_thread.start()

        # UI Animation Loop (~30 FPS)
        self.animation_loop()

    def setup_ui(self):
        # 1. Top Header Bar
        self.header_frame = ctk.CTkFrame(self, fg_color="#14161f", corner_radius=12, border_width=1, border_color="#232736")
        self.header_frame.pack(fill="x", padx=24, pady=(20, 14))

        # Title & Subtitle
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)

        self.title_label = ctk.CTkLabel(
            title_box,
            text="HARDWARE TELEMETRY",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#ffffff"
        )
        self.title_label.pack(anchor="w")

        self.sub_label = ctk.CTkLabel(
            title_box,
            text=f"Direct Hardware Monitor • {self.total_cores} Logical Cores Detected",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#747d8c"
        )
        self.sub_label.pack(anchor="w")

        # Status Badge
        self.status_badge = ctk.CTkLabel(
            self.header_frame,
            text="● SYSTEM NORMAL",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#2ed573",
            fg_color="#102b1f",
            corner_radius=8,
            padx=14,
            pady=6
        )
        self.status_badge.pack(side="right", padx=20, pady=12)

        # 2. Main Metrics Display Cards (CPU RATE & FAN SPEED ONLY)
        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.pack(fill="both", expand=True, padx=24, pady=6)
        self.cards_frame.columnconfigure((0, 1), weight=1, uniform="cards")
        self.cards_frame.rowconfigure(0, weight=1)

        # ====== CARD 1: CPU RATE ======
        self.cpu_card = ctk.CTkFrame(self.cards_frame, fg_color="#161822", corner_radius=16, border_width=1, border_color="#25293d")
        self.cpu_card.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")

        cpu_title_box = ctk.CTkFrame(self.cpu_card, fg_color="transparent")
        cpu_title_box.pack(fill="x", padx=20, pady=(18, 5))

        ctk.CTkLabel(
            cpu_title_box,
            text="CPU RATE",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#00d2d3"
        ).pack(side="left")

        self.cpu_freq_badge = ctk.CTkLabel(
            cpu_title_box,
            text=f"{self.current_freq_ghz:.2f} GHz",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#00d2d3",
            fg_color="#0b2c34",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.cpu_freq_badge.pack(side="right")

        # Big CPU Percent Label
        self.cpu_val_label = ctk.CTkLabel(
            self.cpu_card,
            text="0.0 %",
            font=ctk.CTkFont(family="Segoe UI", size=48, weight="bold"),
            text_color="#ffffff"
        )
        self.cpu_val_label.pack(pady=(12, 4))

        # Progress Bar for CPU Rate
        self.cpu_bar = ctk.CTkProgressBar(
            self.cpu_card,
            height=14,
            corner_radius=7,
            fg_color="#212534",
            progress_color="#00d2d3"
        )
        self.cpu_bar.set(0.0)
        self.cpu_bar.pack(fill="x", padx=24, pady=10)

        # CPU Rate Details Sub-bar
        self.cpu_details_frame = ctk.CTkFrame(self.cpu_card, fg_color="#111219", corner_radius=10)
        self.cpu_details_frame.pack(fill="x", padx=20, pady=(10, 16))

        self.cpu_load_state_label = ctk.CTkLabel(
            self.cpu_details_frame,
            text="Load: IDLE",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#a4b0be"
        )
        self.cpu_load_state_label.pack(side="left", padx=14, pady=8)

        self.cpu_cores_active_label = ctk.CTkLabel(
            self.cpu_details_frame,
            text=f"Active Cores: 0 / {self.total_cores}",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#747d8c"
        )
        self.cpu_cores_active_label.pack(side="right", padx=14, pady=8)


        # ====== CARD 2: FAN SPEED ======
        self.fan_card = ctk.CTkFrame(self.cards_frame, fg_color="#161822", corner_radius=16, border_width=1, border_color="#25293d")
        self.fan_card.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")

        fan_title_box = ctk.CTkFrame(self.fan_card, fg_color="transparent")
        fan_title_box.pack(fill="x", padx=20, pady=(18, 5))

        ctk.CTkLabel(
            fan_title_box,
            text="FAN SPEED",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#a55eea"
        ).pack(side="left")

        self.fan_mode_badge = ctk.CTkLabel(
            fan_title_box,
            text="QUIET MODE",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#a55eea",
            fg_color="#271b3b",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.fan_mode_badge.pack(side="right")

        # Rotating Fan Canvas Widget
        self.fan_canvas = FanVisualizer(self.fan_card, size=130)
        self.fan_canvas.pack(pady=(4, 6))

        # Big RPM Display
        self.fan_val_label = ctk.CTkLabel(
            self.fan_card,
            text="1,450 RPM",
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color="#ffffff"
        )
        self.fan_val_label.pack(pady=(2, 4))

        # Duty Cycle / Percentage Progress Bar
        self.fan_bar = ctk.CTkProgressBar(
            self.fan_card,
            height=10,
            corner_radius=5,
            fg_color="#212534",
            progress_color="#a55eea"
        )
        self.fan_bar.set(0.3)
        self.fan_bar.pack(fill="x", padx=24, pady=6)

        # Fan Sub-bar info
        self.fan_details_frame = ctk.CTkFrame(self.fan_card, fg_color="#111219", corner_radius=10)
        self.fan_details_frame.pack(fill="x", padx=20, pady=(8, 16))

        self.fan_duty_label = ctk.CTkLabel(
            self.fan_details_frame,
            text="Duty: 30%",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#a4b0be"
        )
        self.fan_duty_label.pack(side="left", padx=14, pady=6)

        self.fan_source_label = ctk.CTkLabel(
            self.fan_details_frame,
            text="Auto Thermal Curve",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#747d8c"
        )
        self.fan_source_label.pack(side="right", padx=14, pady=6)


        # 3. Controls & EMERGENCY STOP Area
        self.controls_frame = ctk.CTkFrame(self, fg_color="#14161f", corner_radius=14, border_width=1, border_color="#232736")
        self.controls_frame.pack(fill="x", padx=24, pady=(14, 20))

        # Left side: Stress control buttons
        stress_ctrl_box = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        stress_ctrl_box.pack(side="left", padx=18, pady=16)

        self.start_stress_btn = ctk.CTkButton(
            stress_ctrl_box,
            text="⚡ START CPU STRESS",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#1e3799",
            hover_color="#273c75",
            text_color="#ffffff",
            height=44,
            corner_radius=8,
            command=self.start_stress_test
        )
        self.start_stress_btn.pack(side="left", padx=(0, 10))

        self.stop_stress_btn = ctk.CTkButton(
            stress_ctrl_box,
            text="NORMAL MODE",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#2f3542",
            hover_color="#57606f",
            text_color="#a4b0be",
            height=44,
            corner_radius=8,
            state="disabled",
            command=self.stop_stress_test
        )
        self.stop_stress_btn.pack(side="left")

        # Right side: BIG EMERGENCY STOP BUTTON
        self.emergency_btn = ctk.CTkButton(
            self.controls_frame,
            text="🚨 EMERGENCY STOP",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color="#eb2f06",
            hover_color="#b71540",
            text_color="#ffffff",
            height=48,
            corner_radius=10,
            border_width=2,
            border_color="#ff6b81",
            command=self.trigger_emergency_stop
        )
        self.emergency_btn.pack(side="right", padx=18, pady=14)

    def metrics_loop(self):
        """Continuously reads CPU rate and calculates/queries fan RPM in the background."""
        while self.running:
            try:
                # Read CPU Utilization %
                cpu_p = psutil.cpu_percent(interval=0.2)
                self.current_cpu_percent = cpu_p

                # Read CPU Frequency
                try:
                    freq = psutil.cpu_freq()
                    if freq and freq.current:
                        self.current_freq_ghz = freq.current / 1000.0
                except Exception:
                    pass

                # Fan RPM query / thermal physics calculation
                hw_fans = None
                try:
                    if hasattr(psutil, "sensors_fans"):
                        hw_fans = psutil.sensors_fans()
                except Exception:
                    hw_fans = None

                if hw_fans:
                    self.hardware_fan_detected = True
                    first_fan = next(iter(hw_fans.values()))
                    if first_fan and len(first_fan) > 0:
                        self.target_fan_rpm = float(first_fan[0].current)
                else:
                    self.hardware_fan_detected = False
                    # Realistic Thermal/Acoustic Fan curve based on CPU Rate:
                    # Idle at 0% CPU -> ~1350 RPM
                    # High at 50% CPU -> ~2700 RPM
                    # Full 100% CPU -> ~4600 RPM
                    base_idle_rpm = 1350.0
                    max_boost_rpm = 4800.0
                    load_factor = (cpu_p / 100.0) ** 1.35
                    self.target_fan_rpm = base_idle_rpm + (max_boost_rpm - base_idle_rpm) * load_factor

            except Exception:
                time.sleep(0.5)

    def animation_loop(self):
        """Smoothly interpolates metrics, updates UI elements and spins fan at ~30 FPS."""
        if not self.running:
            return

        # 1. Smooth Fan RPM physics (inertia curve)
        diff = self.target_fan_rpm - self.current_fan_rpm
        if abs(diff) > 2.0:
            # Acceleration is slightly faster than deceleration (like real fans)
            rate = 0.12 if diff > 0 else 0.05
            self.current_fan_rpm += diff * rate
        else:
            self.current_fan_rpm = self.target_fan_rpm

        # 2. Update Fan Animation
        self.fan_canvas.update_angle(self.current_fan_rpm)

        # 3. Update CPU Visuals
        cpu_p = self.current_cpu_percent
        self.cpu_val_label.configure(text=f"{cpu_p:.1f} %")
        self.cpu_bar.set(cpu_p / 100.0)

        # Dynamic color coding for CPU
        if cpu_p > 85.0:
            cpu_color = "#ff4757"
            load_state = "CRITICAL LOAD"
        elif cpu_p > 50.0:
            cpu_color = "#ffa502"
            load_state = "HIGH LOAD"
        else:
            cpu_color = "#00d2d3"
            load_state = "NORMAL LOAD"

        self.cpu_bar.configure(progress_color=cpu_color)
        self.cpu_freq_badge.configure(
            text=f"{self.current_freq_ghz:.2f} GHz",
            text_color=cpu_color
        )
        self.cpu_load_state_label.configure(text=f"Load: {load_state}")

        active_workers = len([p for p in self.stress_processes if p.is_alive()])
        self.cpu_cores_active_label.configure(text=f"Stress Workers: {active_workers} / {self.total_cores}")

        # 4. Update Fan Visuals
        rpm_val = int(self.current_fan_rpm)
        self.fan_val_label.configure(text=f"{rpm_val:,} RPM")
        
        # Duty cycle calculation (0% at 1000 RPM, 100% at 5000 RPM)
        duty_pct = max(0, min(100, int(((self.current_fan_rpm - 1000) / 4000.0) * 100)))
        self.fan_bar.set(duty_pct / 100.0)
        self.fan_duty_label.configure(text=f"Duty: {duty_pct}%")

        if self.current_fan_rpm > 4000:
            fan_mode = "TURBO BOOST"
            fan_color = "#ff4757"
            fan_badge_bg = "#3a131b"
        elif self.current_fan_rpm > 2800:
            fan_mode = "HIGH COOLING"
            fan_color = "#ffa502"
            fan_badge_bg = "#352410"
        elif self.current_fan_rpm > 1800:
            fan_mode = "BALANCED"
            fan_color = "#a55eea"
            fan_badge_bg = "#271b3b"
        else:
            fan_mode = "QUIET MODE"
            fan_color = "#2ed573"
            fan_badge_bg = "#102b1f"

        self.fan_bar.configure(progress_color=fan_color)
        self.fan_mode_badge.configure(
            text=fan_mode,
            text_color=fan_color,
            fg_color=fan_badge_bg
        )

        if self.hardware_fan_detected:
            self.fan_source_label.configure(text="Hardware Sensor (ACPI)", text_color="#2ed573")
        else:
            self.fan_source_label.configure(text="Dynamic Thermal Curve", text_color="#747d8c")

        # 5. Header status updating
        if self.emergency_halted:
            self.status_badge.configure(
                text="⚠️ EMERGENCY HALTED",
                text_color="#ff4757",
                fg_color="#3a131b"
            )
        elif self.is_stressed:
            self.status_badge.configure(
                text="⚡ STRESS TEST ACTIVE",
                text_color="#ffa502",
                fg_color="#352410"
            )
        else:
            self.status_badge.configure(
                text="● SYSTEM MONITORING",
                text_color="#2ed573",
                fg_color="#102b1f"
            )

        # Re-schedule frame
        self.after(33, self.animation_loop)

    def start_stress_test(self):
        """Spawns background stress worker processes across all CPU cores."""
        if self.is_stressed:
            return

        self.emergency_halted = False
        self.is_stressed = True
        self.stop_event.clear()
        self.stress_processes.clear()

        # Start 1 worker per logical CPU core
        for _ in range(self.total_cores):
            p = multiprocessing.Process(target=cpu_stress_worker, args=(self.stop_event,))
            p.daemon = True
            p.start()
            self.stress_processes.append(p)

        self.start_stress_btn.configure(state="disabled", fg_color="#2f3542")
        self.stop_stress_btn.configure(state="normal", fg_color="#eb4d4b", text="STOP STRESS")

    def stop_stress_test(self):
        """Normal graceful shutdown of stress workers."""
        self.stop_event.set()
        self.is_stressed = False

        for p in self.stress_processes:
            if p.is_alive():
                p.terminate()

        for p in self.stress_processes:
            p.join(timeout=0.2)

        self.stress_processes.clear()
        self.start_stress_btn.configure(state="normal", fg_color="#1e3799")
        self.stop_stress_btn.configure(state="disabled", fg_color="#2f3542", text="NORMAL MODE")

    def trigger_emergency_stop(self):
        """Instant emergency halt: aggressively kills all active stress processes and locks."""
        self.emergency_halted = True
        self.is_stressed = False
        self.stop_event.set()

        # Immediate hard kill on all child processes
        for p in self.stress_processes:
            try:
                if p.is_alive():
                    p.kill() # Hard kill SIGKILL
            except Exception:
                pass

        for p in self.stress_processes:
            try:
                p.join(timeout=0.1)
            except Exception:
                pass

        self.stress_processes.clear()

        # Update UI Controls
        self.start_stress_btn.configure(state="normal", fg_color="#1e3799")
        self.stop_stress_btn.configure(state="disabled", fg_color="#2f3542", text="NORMAL MODE")

        # Visual Flash on Emergency Button
        self.emergency_btn.configure(text="🛑 KILLED ALL PROCESSES", fg_color="#ffffff", text_color="#eb2f06")
        self.after(1200, lambda: self.emergency_btn.configure(text="🚨 EMERGENCY STOP", fg_color="#eb2f06", text_color="#ffffff"))

    def on_close(self):
        """Safely terminates all background threads and processes on exit."""
        self.running = False
        self.stop_event.set()
        for p in self.stress_processes:
            try:
                if p.is_alive():
                    p.kill()
            except Exception:
                pass
        self.destroy()

if __name__ == "__main__":
    # Required for Windows multiprocessing support
    multiprocessing.freeze_support()
    app = CPURateFanMonitor()
    app.mainloop()
