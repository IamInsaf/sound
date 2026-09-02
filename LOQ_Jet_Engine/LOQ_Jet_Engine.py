"""
==============================================================================
                              LOQ JET ENGINE
         Controlled Fan Stress & Telemetry Testing Application
      Engineered for Lenovo LOQ 15IRX9 (83DV) - i7-13645HX / RTX 4050
==============================================================================
SAFETY NOTICE:
This utility DOES NOT modify or write to Lenovo Embedded Controller (EC)
registers, fan PWM tables, BIOS, firmware, voltages, or clock frequencies.
Fan speed increases naturally and safely via Lenovo's built-in factory
thermal management system in response to controlled CPU/GPU workloads.
==============================================================================
"""

import sys
import os
import time
import math
import json
import ctypes
import threading
import multiprocessing
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, List

import psutil
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# Set appearance theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ==============================================================================
# 1. MULTIPROCESSING WORKLOAD KERNELS (Module Level for Windows pickle support)
# ==============================================================================

def _cpu_worker_task(stop_event, intensity_val, core_id):
    """
    High-intensity mathematical computation loop for one CPU logical core.
    Modulates workload duty-cycle based on shared intensity value.
    """
    x = 1.000001 + (core_id * 0.001)
    
    while not stop_event.is_set():
        current_intensity = intensity_val.value
        if current_intensity <= 0.01:
            time.sleep(0.05)
            continue
            
        if current_intensity >= 0.99:
            # 100% Continuous Stress: Tight arithmetic & trigonometric loop
            for _ in range(40000):
                x = (x * 1.000000314159) % 1000000.0
                x = math.sin(x) * math.cos(x) + 1.5
        else:
            # Duty-cycle modulation (e.g. 50% = 50ms compute, 50ms sleep)
            compute_slice = max(0.01, current_intensity * 0.08)
            rest_slice = max(0.005, (1.0 - current_intensity) * 0.08)
            
            t_end = time.time() + compute_slice
            while time.time() < t_end and not stop_event.is_set():
                x = (x * 1.000000314159) % 1000000.0
                x = math.sin(x) * math.cos(x) + 1.5
                
            time.sleep(rest_slice)

def _gpu_worker_task(stop_event, intensity_val):
    """
    NVIDIA GeForce RTX 4050 GPU compute worker using native CUDA Driver API.
    Executes heavy floating-point FMA & trigonometric compute shaders directly
    on the Ada Lovelace streaming multiprocessors without external toolkits.
    """
    cuda_path = r"C:\Windows\System32\nvcuda.dll"
    if not os.path.exists(cuda_path):
        return

    try:
        cuda = ctypes.CDLL(cuda_path)
        if cuda.cuInit(0) != 0:
            return

        dev = ctypes.c_int()
        if cuda.cuDeviceGet(ctypes.byref(dev), 0) != 0:
            return

        ctx = ctypes.c_void_p()
        if cuda.cuCtxCreate_v2(ctypes.byref(ctx), 0, dev.value) != 0:
            return

        # PTX Assembly for high-throughput arithmetic stress
        ptx_code = """
.version 7.0
.target sm_50
.address_size 64

.visible .entry stress_kernel(
    .param .u64 d_out,
    .param .u32 iterations
)
{
    .reg .pred      %p<4>;
    .reg .b32       %r<10>;
    .reg .f32       %f<10>;
    .reg .b64       %rd<6>;

    ld.param.u64    %rd1, [d_out];
    ld.param.u32    %r1, [iterations];
    mov.u32         %r2, %tid.x;
    mov.u32         %r3, %ctaid.x;
    mov.u32         %r4, %ntid.x;
    mad.lo.s32      %r5, %r3, %r4, %r2;

    mov.f32         %f1, 1.0;
    mov.f32         %f2, 2.7182818;
    mov.f32         %f3, 3.1415926;
    mov.u32         %r6, 0;

BB0_1:
    setp.ge.u32     %p1, %r6, %r1;
    @%p1 bra        BB0_2;

    fma.rn.f32      %f1, %f1, %f2, %f3;
    sin.approx.f32  %f2, %f1;
    cos.approx.f32  %f3, %f2;
    add.u32         %r6, %r6, 1;
    bra             BB0_1;

BB0_2:
    cvta.to.global.u64 %rd2, %rd1;
    mul.wide.s32    %rd3, %r5, 4;
    add.s64         %rd4, %rd2, %rd3;
    st.global.f32   [%rd4], %f1;
    ret;
}
""".encode('utf-8')

        mod = ctypes.c_void_p()
        if cuda.cuModuleLoadData(ctypes.byref(mod), ptx_code) != 0:
            return

        func = ctypes.c_void_p()
        if cuda.cuModuleGetFunction(ctypes.byref(func), mod, b"stress_kernel") != 0:
            return

        # Allocate 16MB VRAM scratch buffer on RTX 4050
        d_mem = ctypes.c_void_p()
        cuda.cuMemAlloc_v2(ctypes.byref(d_mem), 16 * 1024 * 1024)

        iters = ctypes.c_uint(120000)
        args = (ctypes.c_void_p * 2)(ctypes.addressof(d_mem), ctypes.addressof(iters))

        while not stop_event.is_set():
            current_intensity = intensity_val.value
            if current_intensity <= 0.01:
                time.sleep(0.05)
                continue

            # Launch 512 blocks * 256 threads = 131,072 GPU threads
            cuda.cuLaunchKernel(
                func,
                512, 1, 1,
                256, 1, 1,
                0, None,
                args, None
            )
            cuda.cuCtxSynchronize()

            # Modulate duty cycle if intensity < 100%
            if current_intensity < 0.99:
                sleep_time = max(0.005, (1.0 - current_intensity) * 0.06)
                time.sleep(sleep_time)

    except Exception:
        pass


# ==============================================================================
# 2. HARDWARE TELEMETRY ENGINE (Windows Native & NVML)
# ==============================================================================

class TelemetryEngine:
    """
    Direct hardware telemetry manager for Windows 11 & NVIDIA GPU.
    Follows strict integrity: never reports synthetic sensor numbers.
    """
    def __init__(self):
        self.nvml_initialized = False
        self.nvml_handle = None
        self.gpu_name = "NVIDIA GeForce RTX 4050 Laptop GPU"
        self._init_nvml()

    def _init_nvml(self):
        """Initializes NVML ctypes bindings from Windows System32."""
        try:
            nvml_path = r"C:\Windows\System32\nvml.dll"
            if os.path.exists(nvml_path):
                self.nvml = ctypes.CDLL(nvml_path)
                if self.nvml.nvmlInit_v2() == 0:
                    handle = ctypes.c_void_p()
                    if self.nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle)) == 0:
                        self.nvml_handle = handle
                        self.nvml_initialized = True
                        
                        name_buf = ctypes.create_string_buffer(96)
                        if self.nvml.nvmlDeviceGetName(handle, name_buf, 96) == 0:
                            self.gpu_name = name_buf.value.decode("utf-8", errors="ignore")
        except Exception:
            self.nvml_initialized = False

    def get_gpu_telemetry(self) -> Dict[str, Any]:
        """Queries genuine GPU temperature, utilization, and power draw."""
        res = {
            "temp": None,
            "util": None,
            "mem_util": None,
            "power": None,
            "available": False
        }
        
        if not self.nvml_initialized or not self.nvml_handle:
            return res

        try:
            # GPU Temperature (Sensor Type 0 = Core)
            temp = ctypes.c_uint()
            if self.nvml.nvmlDeviceGetTemperature(self.nvml_handle, 0, ctypes.byref(temp)) == 0:
                res["temp"] = float(temp.value)

            # GPU & Memory Utilization
            class nvmlUtilization_t(ctypes.Structure):
                _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]
            
            util = nvmlUtilization_t()
            if self.nvml.nvmlDeviceGetUtilizationRates(self.nvml_handle, ctypes.byref(util)) == 0:
                res["util"] = float(util.gpu)
                res["mem_util"] = float(util.memory)

            # GPU Power Draw (milliwatts -> Watts)
            power = ctypes.c_uint()
            if self.nvml.nvmlDeviceGetPowerUsage(self.nvml_handle, ctypes.byref(power)) == 0:
                res["power"] = float(power.value) / 1000.0

            res["available"] = (res["temp"] is not None or res["util"] is not None)
        except Exception:
            pass

        return res

    def get_cpu_telemetry(self) -> Dict[str, Any]:
        """Queries CPU utilization, frequency, and native temperatures."""
        res = {
            "util": 0.0,
            "freq_ghz": None,
            "temp": None,
            "available": True
        }

        try:
            # CPU Utilization (Instantaneous non-blocking sample)
            res["util"] = psutil.cpu_percent(interval=None)

            # CPU Frequency
            freq = psutil.cpu_freq()
            if freq and freq.current:
                res["freq_ghz"] = freq.current / 1000.0

            # Native CPU Temperature (psutil / ACPI)
            # On Windows without kernel driver, psutil.sensors_temperatures() is often restricted
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries and len(entries) > 0:
                            res["temp"] = float(entries[0].current)
                            break
        except Exception:
            pass

        return res

    def get_fan_telemetry(self) -> Optional[float]:
        """Queries hardware Fan RPM if exposed by Windows/OEM ACPI."""
        try:
            if hasattr(psutil, "sensors_fans"):
                fans = psutil.sensors_fans()
                if fans:
                    for name, entries in fans.items():
                        if entries and len(entries) > 0 and entries[0].current:
                            return float(entries[0].current)
        except Exception:
            pass
        return None


# ==============================================================================
# 3. CONFIGURATION & THERMAL SAFETY CONTROLLER
# ==============================================================================

@dataclass
class SafetyConfig:
    cpu_warn_temp: float = 85.0
    cpu_stop_temp: float = 92.0
    gpu_warn_temp: float = 80.0
    gpu_stop_temp: float = 87.0
    ramp_step_sec: float = 3.0  # Time spent per ramp step (0->25->50->75->100)

class ThermalSafetyController:
    """
    Independent safety protection guard.
    Monitors hardware temperatures and executes automatic shutdown if thresholds are reached.
    """
    def __init__(self, config: SafetyConfig):
        self.config = config

    def evaluate(self, cpu_temp: Optional[float], gpu_temp: Optional[float]) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Evaluates temperatures.
        Returns: (state, warning_message, stop_reason)
        state in ["OK", "WARNING", "TRIP"]
        """
        # 1. Check Automatic Stop Thresholds
        if gpu_temp is not None and gpu_temp >= self.config.gpu_stop_temp:
            reason = f"GPU Temperature reached {gpu_temp:.1f}°C (Safety Limit: {self.config.gpu_stop_temp:.1f}°C)"
            return ("TRIP", None, reason)

        if cpu_temp is not None and cpu_temp >= self.config.cpu_stop_temp:
            reason = f"CPU Temperature reached {cpu_temp:.1f}°C (Safety Limit: {self.config.cpu_stop_temp:.1f}°C)"
            return ("TRIP", None, reason)

        # 2. Check Warning Thresholds
        warnings = []
        if gpu_temp is not None and gpu_temp >= self.config.gpu_warn_temp:
            warnings.append(f"GPU: {gpu_temp:.1f}°C ≥ {self.config.gpu_warn_temp:.1f}°C")

        if cpu_temp is not None and cpu_temp >= self.config.cpu_warn_temp:
            warnings.append(f"CPU: {cpu_temp:.1f}°C ≥ {self.config.cpu_warn_temp:.1f}°C")

        if warnings:
            return ("WARNING", " • ".join(warnings), None)

        return ("OK", None, None)


# ==============================================================================
# 4. WORKLOAD SUPERVISOR & PROCESS MANAGEMENT
# ==============================================================================

class WorkloadSupervisor:
    """
    Controls CPU & GPU worker processes, ramps workload smoothly, and manages lifecycle.
    """
    def __init__(self):
        self.total_cores = multiprocessing.cpu_count()
        self.cpu_workers: List[multiprocessing.Process] = []
        self.gpu_worker: Optional[multiprocessing.Process] = None
        
        self.stop_event = multiprocessing.Event()
        self.shared_cpu_intensity = multiprocessing.Value('d', 0.0)
        self.shared_gpu_intensity = multiprocessing.Value('d', 0.0)
        
        self.is_running = False
        self.is_ramping = False
        self.target_intensity = 1.0
        self.current_intensity = 0.0
        self.mode = "CPU+GPU"
        self.ramp_thread: Optional[threading.Thread] = None

    def start_workload(self, target_intensity: float, mode: str, ramp_step_sec: float, on_ramp_step_cb):
        """Spawns workers and starts controlled ramp."""
        self.stop_all_workers_now()
        
        self.target_intensity = target_intensity
        self.mode = mode
        self.is_running = True
        self.is_ramping = True
        self.current_intensity = 0.0
        self.stop_event.clear()
        self.shared_cpu_intensity.value = 0.0
        self.shared_gpu_intensity.value = 0.0

        # 1. Spawn CPU Workers across all detected cores
        if "CPU" in mode:
            self.cpu_workers = []
            for i in range(self.total_cores):
                p = multiprocessing.Process(
                    target=_cpu_worker_task,
                    args=(self.stop_event, self.shared_cpu_intensity, i),
                    daemon=True
                )
                p.start()
                self.cpu_workers.append(p)

        # 2. Spawn GPU Worker on RTX 4050
        if "GPU" in mode:
            self.gpu_worker = multiprocessing.Process(
                target=_gpu_worker_task,
                args=(self.stop_event, self.shared_gpu_intensity),
                daemon=True
            )
            self.gpu_worker.start()

        # 3. Start Ramping Thread
        def ramp_runner():
            steps = [0.25, 0.50, 0.75, 1.0]
            # Filter steps up to target
            target_steps = [s for s in steps if s <= target_intensity]
            if not target_steps or target_steps[-1] < target_intensity:
                target_steps.append(target_intensity)

            for step in target_steps:
                if not self.is_running or self.stop_event.is_set():
                    break
                self.current_intensity = step
                if "CPU" in self.mode:
                    self.shared_cpu_intensity.value = step
                if "GPU" in self.mode:
                    self.shared_gpu_intensity.value = step
                    
                if on_ramp_step_cb:
                    on_ramp_step_cb(step)
                    
                time.sleep(ramp_step_sec)

            self.is_ramping = False

        self.ramp_thread = threading.Thread(target=ramp_runner, daemon=True)
        self.ramp_thread.start()

    def set_live_intensity(self, intensity: float):
        """Dynamically adjusts intensity while running."""
        self.target_intensity = intensity
        self.current_intensity = intensity
        if "CPU" in self.mode:
            self.shared_cpu_intensity.value = intensity
        if "GPU" in self.mode:
            self.shared_gpu_intensity.value = intensity

    def stop_graceful(self):
        """Normal graceful shutdown of all stress workers."""
        self.is_running = False
        self.is_ramping = False
        self.stop_event.set()
        self.shared_cpu_intensity.value = 0.0
        self.shared_gpu_intensity.value = 0.0

        for p in self.cpu_workers:
            if p.is_alive():
                p.terminate()

        if self.gpu_worker and self.gpu_worker.is_alive():
            self.gpu_worker.terminate()

        for p in self.cpu_workers:
            p.join(timeout=0.2)
        if self.gpu_worker:
            self.gpu_worker.join(timeout=0.2)

        self.cpu_workers.clear()
        self.gpu_worker = None

    def stop_all_workers_now(self):
        """Aggressive instant kill on all worker processes (SIGKILL)."""
        self.is_running = False
        self.is_ramping = False
        self.stop_event.set()
        self.shared_cpu_intensity.value = 0.0
        self.shared_gpu_intensity.value = 0.0

        for p in self.cpu_workers:
            try:
                if p.is_alive():
                    p.kill()
            except Exception:
                pass

        if self.gpu_worker:
            try:
                if self.gpu_worker.is_alive():
                    self.gpu_worker.kill()
            except Exception:
                pass

        for p in self.cpu_workers:
            try:
                p.join(timeout=0.05)
            except Exception:
                pass
        if self.gpu_worker:
            try:
                self.gpu_worker.join(timeout=0.05)
            except Exception:
                pass

        self.cpu_workers.clear()
        self.gpu_worker = None


# ==============================================================================
# 5. LIVE MINI-GRAPH CANVAS WIDGET
# ==============================================================================

class MiniTelemetryGraph(tk.Canvas):
    """
    Lightweight, smooth rolling telemetry mini-graph with gradient fills and gridlines.
    """
    def __init__(self, master, title: str, unit: str, line_color: str, max_val: float = 100.0, height: int = 80, **kwargs):
        super().__init__(
            master,
            height=height,
            bg="#11131c",
            highlightthickness=1,
            highlightbackground="#222738",
            **kwargs
        )
        self.title = title
        self.unit = unit
        self.line_color = line_color
        self.max_val = max_val
        self.history: List[Optional[float]] = [0.0] * 30
        self.bind("<Configure>", lambda e: self.redraw())

    def add_sample(self, value: Optional[float]):
        """Pushes a new sample into the rolling history."""
        self.history.pop(0)
        self.history.append(value)
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return

        # Background gridlines
        self.create_line(0, h * 0.25, w, h * 0.25, fill="#1a1e2e", dash=(2, 4))
        self.create_line(0, h * 0.50, w, h * 0.50, fill="#1a1e2e", dash=(2, 4))
        self.create_line(0, h * 0.75, w, h * 0.75, fill="#1a1e2e", dash=(2, 4))

        # Title & Unit
        self.create_text(8, 10, text=f"{self.title}", fill="#747d8c", font=("Segoe UI", 9, "bold"), anchor="w")

        # Check if sensor is completely unavailable
        valid_points = [p for p in self.history if p is not None]
        latest = self.history[-1]

        if not valid_points or latest is None:
            self.create_text(w / 2, h / 2 + 4, text="N/A — sensor unavailable", fill="#57606f", font=("Segoe UI", 10, "italic"))
            return

        # Latest Value Badge
        val_str = f"{latest:.1f} {self.unit}" if self.unit == "°C" else f"{int(latest)} {self.unit}"
        self.create_text(w - 8, 10, text=val_str, fill=self.line_color, font=("Segoe UI", 10, "bold"), anchor="e")

        # Calculate polyline points
        n = len(self.history)
        step_x = w / float(n - 1)
        points = []
        pad_top = 22
        pad_bot = 6
        usable_h = h - pad_top - pad_bot

        for i, val in enumerate(self.history):
            x = i * step_x
            v = val if val is not None else 0.0
            v_clamped = max(0.0, min(self.max_val, v))
            y = h - pad_bot - (v_clamped / self.max_val) * usable_h
            points.append((x, y))

        # Draw filled polygon under curve
        poly_pts = [points[0][0], h]
        for pt in points:
            poly_pts.extend([pt[0], pt[1]])
        poly_pts.extend([points[-1][0], h])

        # Dark shaded fill
        self.create_polygon(poly_pts, fill="#161b29", outline="")

        # Draw main glow line
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            self.create_line(p1[0], p1[1], p2[0], p2[1], fill=self.line_color, width=2, smooth=True)

        # Highlight newest point
        last_pt = points[-1]
        self.create_oval(last_pt[0] - 3, last_pt[1] - 3, last_pt[0] + 3, last_pt[1] + 3, fill="#ffffff", outline=self.line_color, width=2)


# ==============================================================================
# 6. SETTINGS MODAL DIALOG
# ==============================================================================

class SettingsDialog(ctk.CTkToplevel):
    """Settings modal to adjust thermal thresholds and ramp parameters safely."""
    def __init__(self, parent, config: SafetyConfig, on_save_cb):
        super().__init__(parent)
        self.parent = parent
        self.config = config
        self.on_save_cb = on_save_cb

        self.title("Thermal Safety & Ramp Configuration")
        self.geometry("520x460")
        self.resizable(False, False)
        self.configure(fg_color="#0e1017")
        self.transient(parent)
        self.grab_set()

        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(
            self,
            text="⚙ THERMAL PROTECTION SETTINGS",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color="#00d2d3"
        ).pack(pady=(18, 4))

        ctk.CTkLabel(
            self,
            text="Configure hardware safety limits with strict enforcement boundaries.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#747d8c"
        ).pack(pady=(0, 14))

        form_frame = ctk.CTkFrame(self, fg_color="#151824", corner_radius=10, border_width=1, border_color="#24293c")
        form_frame.pack(fill="both", expand=True, padx=20, pady=6)

        # Grid inputs
        labels = [
            ("CPU Warning Temp (°C) [60 - 95]:", "cpu_warn", str(self.config.cpu_warn_temp)),
            ("CPU Auto-Stop Temp (°C) [70 - 100]:", "cpu_stop", str(self.config.cpu_stop_temp)),
            ("GPU Warning Temp (°C) [50 - 88]:", "gpu_warn", str(self.config.gpu_warn_temp)),
            ("GPU Auto-Stop Temp (°C) [60 - 92]:", "gpu_stop", str(self.config.gpu_stop_temp)),
            ("Ramp Step Duration (Seconds) [1 - 10]:", "ramp_step", str(self.config.ramp_step_sec)),
        ]

        self.entries = {}
        for row_idx, (text, key, val) in enumerate(labels):
            ctk.CTkLabel(
                form_frame,
                text=text,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color="#dcdde1"
            ).grid(row=row_idx, column=0, padx=16, pady=10, sticky="w")

            entry = ctk.CTkEntry(
                form_frame,
                width=90,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                fg_color="#0f111a",
                border_color="#2f3542"
            )
            entry.insert(0, val)
            entry.grid(row=row_idx, column=1, padx=16, pady=10, sticky="e")
            self.entries[key] = entry

        # Bottom Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=16)

        ctk.CTkButton(
            btn_frame,
            text="RESET DEFAULTS",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#2f3542",
            hover_color="#57606f",
            width=130,
            command=self.reset_defaults
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="SAVE CONFIG",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#00d2d3",
            hover_color="#01a3a4",
            text_color="#0e1017",
            width=130,
            command=self.save_config
        ).pack(side="right")

    def reset_defaults(self):
        defaults = SafetyConfig()
        self.entries["cpu_warn"].delete(0, "end"); self.entries["cpu_warn"].insert(0, str(defaults.cpu_warn_temp))
        self.entries["cpu_stop"].delete(0, "end"); self.entries["cpu_stop"].insert(0, str(defaults.cpu_stop_temp))
        self.entries["gpu_warn"].delete(0, "end"); self.entries["gpu_warn"].insert(0, str(defaults.gpu_warn_temp))
        self.entries["gpu_stop"].delete(0, "end"); self.entries["gpu_stop"].insert(0, str(defaults.gpu_stop_temp))
        self.entries["ramp_step"].delete(0, "end"); self.entries["ramp_step"].insert(0, str(defaults.ramp_step_sec))

    def save_config(self):
        try:
            cw = float(self.entries["cpu_warn"].get())
            cs = float(self.entries["cpu_stop"].get())
            gw = float(self.entries["gpu_warn"].get())
            gs = float(self.entries["gpu_stop"].get())
            rs = float(self.entries["ramp_step"].get())

            # Validation boundaries
            if not (60.0 <= cw <= 95.0):
                messagebox.showerror("Invalid Input", "CPU Warning must be between 60°C and 95°C.")
                return
            if not (70.0 <= cs <= 100.0) or cs <= cw:
                messagebox.showerror("Invalid Input", "CPU Auto-Stop must be between 70°C and 100°C and greater than Warning.")
                return
            if not (50.0 <= gw <= 88.0):
                messagebox.showerror("Invalid Input", "GPU Warning must be between 50°C and 88°C.")
                return
            if not (60.0 <= gs <= 92.0) or gs <= gw:
                messagebox.showerror("Invalid Input", "GPU Auto-Stop must be between 60°C and 92°C and greater than Warning.")
                return
            if not (1.0 <= rs <= 10.0):
                messagebox.showerror("Invalid Input", "Ramp step duration must be between 1.0 and 10.0 seconds.")
                return

            self.config.cpu_warn_temp = cw
            self.config.cpu_stop_temp = cs
            self.config.gpu_warn_temp = gw
            self.config.gpu_stop_temp = gs
            self.config.ramp_step_sec = rs

            self.on_save_cb(self.config)
            self.destroy()

        except ValueError:
            messagebox.showerror("Invalid Format", "Please enter valid numeric numbers for all settings.")


# ==============================================================================
# 7. MAIN APPLICATION GUI
# ==============================================================================

class LOQJetEngineApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # System & Window Config
        self.title("LOQ JET ENGINE • Fan Stress & Hardware Telemetry Utility")
        self.geometry("960x780")
        self.minsize(900, 720)
        self.configure(fg_color="#0a0b10")

        # Modules
        self.telemetry = TelemetryEngine()
        self.config = SafetyConfig()
        self.safety = ThermalSafetyController(self.config)
        self.supervisor = WorkloadSupervisor()

        # State Variables
        self.current_state = "READY"
        self.selected_intensity = 1.0
        self.selected_mode = "CPU+GPU"
        self.start_time: Optional[float] = None
        self.running = True
        self.trip_reason: Optional[str] = None

        # Build UI
        self.setup_ui()

        # Keyboard Shortcuts & Safe Exit Hook
        self.bind("<Escape>", lambda e: self.trigger_emergency_stop())
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Background Telemetry & GUI Update Loops
        self.telemetry_thread = threading.Thread(target=self.telemetry_loop, daemon=True)
        self.telemetry_thread.start()

        self.gui_update_loop()

    def setup_ui(self):
        # 1. Top Lenovo LOQ Performance Notice Banner
        notice_banner = ctk.CTkFrame(self, fg_color="#18233c", corner_radius=8, border_width=1, border_color="#2b4374")
        notice_banner.pack(fill="x", padx=20, pady=(14, 8))

        ctk.CTkLabel(
            notice_banner,
            text="⚡ NOTICE: For maximum fan speed, connect the charger and set Lenovo Performance mode with Fn+Q before starting.",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#70a1ff"
        ).pack(side="left", padx=16, pady=8)

        # 2. Main Header (Title, Specs, Status Badge, Runtime)
        header_frame = ctk.CTkFrame(self, fg_color="#12141e", corner_radius=12, border_width=1, border_color="#212638")
        header_frame.pack(fill="x", padx=20, pady=6)

        # Title Box
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=18, pady=12)

        ctk.CTkLabel(
            title_box,
            text="LOQ JET ENGINE",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#ffffff"
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text=f"Lenovo LOQ 15IRX9 (83DV) • Intel i7-13645HX • {self.telemetry.gpu_name}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#747d8c"
        ).pack(anchor="w")

        # Right Side: Status Badge & Stopwatch
        status_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        status_box.pack(side="right", padx=18, pady=12)

        self.status_badge = ctk.CTkLabel(
            status_box,
            text="● READY",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#2ed573",
            fg_color="#102b1f",
            corner_radius=8,
            padx=16,
            pady=6
        )
        self.status_badge.pack(anchor="e", pady=(0, 4))

        self.runtime_label = ctk.CTkLabel(
            status_box,
            text="Runtime: 00:00:00",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#a4b0be"
        )
        self.runtime_label.pack(anchor="e")

        # 3. Telemetry Display Grid (4 Cards + 4 Mini-Graphs)
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=20, pady=8)
        self.grid_frame.columnconfigure((0, 1), weight=1, uniform="grid")
        self.grid_frame.rowconfigure((0, 1), weight=1, uniform="grid")

        # Card 1: CPU Temperature
        self.cpu_temp_card = ctk.CTkFrame(self.grid_frame, fg_color="#131520", corner_radius=12, border_width=1, border_color="#22273a")
        self.cpu_temp_card.grid(row=0, column=0, padx=(0, 6), pady=(0, 6), sticky="nsew")
        
        self.cpu_temp_header = ctk.CTkFrame(self.cpu_temp_card, fg_color="transparent")
        self.cpu_temp_header.pack(fill="x", padx=14, pady=(10, 2))
        ctk.CTkLabel(self.cpu_temp_header, text="CPU TEMPERATURE", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#00d2d3").pack(side="left")
        self.cpu_temp_val_lbl = ctk.CTkLabel(self.cpu_temp_header, text="-- °C", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#ffffff")
        self.cpu_temp_val_lbl.pack(side="right")
        
        self.cpu_temp_graph = MiniTelemetryGraph(self.cpu_temp_card, title="CPU Temp History", unit="°C", line_color="#00d2d3", max_val=100.0)
        self.cpu_temp_graph.pack(fill="both", expand=True, padx=12, pady=(4, 10))

        # Card 2: GPU Temperature
        self.gpu_temp_card = ctk.CTkFrame(self.grid_frame, fg_color="#131520", corner_radius=12, border_width=1, border_color="#22273a")
        self.gpu_temp_card.grid(row=0, column=1, padx=(6, 0), pady=(0, 6), sticky="nsew")
        
        self.gpu_temp_header = ctk.CTkFrame(self.gpu_temp_card, fg_color="transparent")
        self.gpu_temp_header.pack(fill="x", padx=14, pady=(10, 2))
        ctk.CTkLabel(self.gpu_temp_header, text="GPU TEMPERATURE", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#ff4757").pack(side="left")
        self.gpu_temp_val_lbl = ctk.CTkLabel(self.gpu_temp_header, text="-- °C", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#ffffff")
        self.gpu_temp_val_lbl.pack(side="right")

        self.gpu_temp_graph = MiniTelemetryGraph(self.gpu_temp_card, title="GPU Temp History", unit="°C", line_color="#ff4757", max_val=100.0)
        self.gpu_temp_graph.pack(fill="both", expand=True, padx=12, pady=(4, 10))

        # Card 3: CPU Utilization
        self.cpu_util_card = ctk.CTkFrame(self.grid_frame, fg_color="#131520", corner_radius=12, border_width=1, border_color="#22273a")
        self.cpu_util_card.grid(row=1, column=0, padx=(0, 6), pady=(6, 0), sticky="nsew")
        
        self.cpu_util_header = ctk.CTkFrame(self.cpu_util_card, fg_color="transparent")
        self.cpu_util_header.pack(fill="x", padx=14, pady=(10, 2))
        ctk.CTkLabel(self.cpu_util_header, text="CPU UTILIZATION", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#a55eea").pack(side="left")
        self.cpu_util_val_lbl = ctk.CTkLabel(self.cpu_util_header, text="0 %", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#ffffff")
        self.cpu_util_val_lbl.pack(side="right")

        self.cpu_util_graph = MiniTelemetryGraph(self.cpu_util_card, title="CPU Load History", unit="%", line_color="#a55eea", max_val=100.0)
        self.cpu_util_graph.pack(fill="both", expand=True, padx=12, pady=(4, 10))

        # Card 4: GPU Utilization
        self.gpu_util_card = ctk.CTkFrame(self.grid_frame, fg_color="#131520", corner_radius=12, border_width=1, border_color="#22273a")
        self.gpu_util_card.grid(row=1, column=1, padx=(6, 0), pady=(6, 0), sticky="nsew")
        
        self.gpu_util_header = ctk.CTkFrame(self.gpu_util_card, fg_color="transparent")
        self.gpu_util_header.pack(fill="x", padx=14, pady=(10, 2))
        ctk.CTkLabel(self.gpu_util_header, text="GPU UTILIZATION", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#ffa502").pack(side="left")
        self.gpu_util_val_lbl = ctk.CTkLabel(self.gpu_util_header, text="0 %", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#ffffff")
        self.gpu_util_val_lbl.pack(side="right")

        self.gpu_util_graph = MiniTelemetryGraph(self.gpu_util_card, title="GPU Load History", unit="%", line_color="#ffa502", max_val=100.0)
        self.gpu_util_graph.pack(fill="both", expand=True, padx=12, pady=(4, 10))

        # 4. Sensor & Fan Info Bar
        self.fan_info_bar = ctk.CTkFrame(self, fg_color="#10121a", corner_radius=8)
        self.fan_info_bar.pack(fill="x", padx=20, pady=(6, 6))

        self.fan_rpm_label = ctk.CTkLabel(
            self.fan_info_bar,
            text="Fan Speed: N/A — sensor unavailable",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#747d8c"
        )
        self.fan_rpm_label.pack(side="left", padx=16, pady=4)

        self.power_draw_label = ctk.CTkLabel(
            self.fan_info_bar,
            text="GPU Power: 0.0 W",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#747d8c"
        )
        self.power_draw_label.pack(side="right", padx=16, pady=4)

        # 5. Workload Selectors & Configuration Panel
        config_bar = ctk.CTkFrame(self, fg_color="#12141e", corner_radius=10, border_width=1, border_color="#212638")
        config_bar.pack(fill="x", padx=20, pady=6)

        # Mode Selection
        mode_box = ctk.CTkFrame(config_bar, fg_color="transparent")
        mode_box.pack(side="left", padx=14, pady=10)

        ctk.CTkLabel(mode_box, text="WORKLOAD MODE:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#a4b0be").pack(side="left", padx=(0, 8))

        self.mode_var = ctk.StringVar(value="CPU+GPU")
        self.mode_seg = ctk.CTkSegmentedButton(
            mode_box,
            values=["CPU + GPU", "CPU Load", "GPU Load"],
            command=self.on_mode_change,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            selected_color="#00d2d3",
            selected_hover_color="#01a3a4"
        )
        self.mode_seg.set("CPU + GPU")
        self.mode_seg.pack(side="left")

        # Intensity Selection
        intensity_box = ctk.CTkFrame(config_bar, fg_color="transparent")
        intensity_box.pack(side="right", padx=14, pady=10)

        ctk.CTkLabel(intensity_box, text="INTENSITY:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#a4b0be").pack(side="left", padx=(0, 8))

        self.intensity_seg = ctk.CTkSegmentedButton(
            intensity_box,
            values=["25%", "50%", "75%", "100%"],
            command=self.on_intensity_change,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            selected_color="#ff4757",
            selected_hover_color="#eb2f06"
        )
        self.intensity_seg.set("100%")
        self.intensity_seg.pack(side="left", padx=(0, 10))

        # Settings button
        self.settings_btn = ctk.CTkButton(
            intensity_box,
            text="⚙ SETTINGS",
            width=80,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#2f3542",
            hover_color="#57606f",
            command=self.open_settings
        )
        self.settings_btn.pack(side="left")

        # 6. Action Buttons Bar (START, STOP, EMERGENCY STOP)
        actions_bar = ctk.CTkFrame(self, fg_color="transparent")
        actions_bar.pack(fill="x", padx=20, pady=(6, 16))

        # Start Button
        self.start_btn = ctk.CTkButton(
            actions_bar,
            text="🚀 START JET ENGINE",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color="#00d2d3",
            hover_color="#01a3a4",
            text_color="#0a0b10",
            height=50,
            corner_radius=10,
            command=self.start_jet_engine
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Stop Button
        self.stop_btn = ctk.CTkButton(
            actions_bar,
            text="🛑 STOP ENGINE",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#2f3542",
            hover_color="#57606f",
            text_color="#dcdde1",
            height=50,
            corner_radius=10,
            state="disabled",
            command=self.stop_jet_engine
        )
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Emergency Stop Button
        self.emergency_btn = ctk.CTkButton(
            actions_bar,
            text="⚠ EMERGENCY STOP (ESC)",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#eb2f06",
            hover_color="#b71540",
            text_color="#ffffff",
            border_width=2,
            border_color="#ff6b81",
            height=50,
            corner_radius=10,
            command=self.trigger_emergency_stop
        )
        self.emergency_btn.pack(side="left", fill="x", expand=True)

    # --------------------------------------------------------------------------
    # CONTROLLER EVENT HANDLERS
    # --------------------------------------------------------------------------

    def on_mode_change(self, value: str):
        if value == "CPU + GPU":
            self.selected_mode = "CPU+GPU"
        elif value == "CPU Load":
            self.selected_mode = "CPU"
        elif value == "GPU Load":
            self.selected_mode = "GPU"

    def on_intensity_change(self, value: str):
        val_map = {"25%": 0.25, "50%": 0.50, "75%": 0.75, "100%": 1.0}
        self.selected_intensity = val_map.get(value, 1.0)
        if self.supervisor.is_running and not self.supervisor.is_ramping:
            self.supervisor.set_live_intensity(self.selected_intensity)

    def open_settings(self):
        SettingsDialog(self, self.config, self.on_save_config)

    def on_save_config(self, new_config: SafetyConfig):
        self.config = new_config
        self.safety = ThermalSafetyController(self.config)

    def start_jet_engine(self):
        """Launches the stress test with ramp."""
        self.trip_reason = None
        self.current_state = "RAMPING"
        self.start_time = time.time()

        self.start_btn.configure(state="disabled", fg_color="#1c2b36")
        self.stop_btn.configure(state="normal", fg_color="#eb4d4b", text_color="#ffffff")

        def on_ramp_step(step_val):
            pct = int(step_val * 100)
            self.current_state = f"RAMPING ({pct}%)"

        self.supervisor.start_workload(
            target_intensity=self.selected_intensity,
            mode=self.selected_mode,
            ramp_step_sec=self.config.ramp_step_sec,
            on_ramp_step_cb=on_ramp_step
        )

    def stop_jet_engine(self):
        """Normal graceful stop."""
        self.supervisor.stop_graceful()
        self.current_state = "STOPPED"
        self.start_btn.configure(state="normal", fg_color="#00d2d3")
        self.stop_btn.configure(state="disabled", fg_color="#2f3542", text_color="#dcdde1")

    def trigger_emergency_stop(self):
        """Aggressive instant kill on all worker processes."""
        self.supervisor.stop_all_workers_now()
        self.current_state = "EMERGENCY HALTED"
        
        self.start_btn.configure(state="normal", fg_color="#00d2d3")
        self.stop_btn.configure(state="disabled", fg_color="#2f3542", text_color="#dcdde1")

        # Visual Flash
        self.emergency_btn.configure(text="🛑 KILLED ALL PROCESSES", fg_color="#ffffff", text_color="#eb2f06")
        self.after(1400, lambda: self.emergency_btn.configure(text="⚠ EMERGENCY STOP (ESC)", fg_color="#eb2f06", text_color="#ffffff"))

    def trigger_thermal_safety_trip(self, reason: str):
        """Automatic safety shutdown triggered by temperature limits."""
        self.trip_reason = reason
        self.supervisor.stop_all_workers_now()
        self.current_state = "THERMAL STOP"
        
        self.start_btn.configure(state="normal", fg_color="#00d2d3")
        self.stop_btn.configure(state="disabled", fg_color="#2f3542", text_color="#dcdde1")

        # Display alert dialog
        messagebox.showwarning(
            "Automatic Thermal Safety Trip",
            f"AUTOMATIC WORKLOAD HALT TRIGGERED:\n\n{reason}\n\nWorkloads were terminated to protect hardware."
        )

    # --------------------------------------------------------------------------
    # BACKGROUND TELEMETRY & GUI REFRESH
    # --------------------------------------------------------------------------

    def telemetry_loop(self):
        """Background thread polling sensors ~1x/sec and checking thermal safety."""
        while self.running:
            try:
                cpu_data = self.telemetry.get_cpu_telemetry()
                gpu_data = self.telemetry.get_gpu_telemetry()
                fan_rpm = self.telemetry.get_fan_telemetry()

                # Safety Evaluation
                if self.supervisor.is_running:
                    safety_status, warn_msg, trip_reason = self.safety.evaluate(cpu_data["temp"], gpu_data["temp"])
                    
                    if safety_status == "TRIP":
                        self.after(0, lambda r=trip_reason: self.trigger_thermal_safety_trip(r))
                    elif safety_status == "WARNING":
                        if not self.supervisor.is_ramping:
                            self.current_state = "THERMAL WARNING"
                    elif not self.supervisor.is_ramping:
                        self.current_state = "JET ENGINE ACTIVE"

                # Push samples to live mini-graphs
                self.after(0, lambda c=cpu_data, g=gpu_data, f=fan_rpm: self.update_telemetry_ui(c, g, f))

            except Exception:
                pass

            time.sleep(1.0)

    def update_telemetry_ui(self, cpu_data: Dict[str, Any], gpu_data: Dict[str, Any], fan_rpm: Optional[float]):
        """Updates graph samples and labels on main UI thread."""
        # 1. CPU Temp
        self.cpu_temp_graph.add_sample(cpu_data["temp"])
        if cpu_data["temp"] is not None:
            self.cpu_temp_val_lbl.configure(text=f"{cpu_data['temp']:.1f} °C", text_color="#00d2d3")
        else:
            self.cpu_temp_val_lbl.configure(text="N/A — sensor unavailable", text_color="#747d8c")

        # 2. GPU Temp
        self.gpu_temp_graph.add_sample(gpu_data["temp"])
        if gpu_data["temp"] is not None:
            self.gpu_temp_val_lbl.configure(text=f"{gpu_data['temp']:.1f} °C", text_color="#ff4757")
        else:
            self.gpu_temp_val_lbl.configure(text="N/A — sensor unavailable", text_color="#747d8c")

        # 3. CPU Util
        self.cpu_util_graph.add_sample(cpu_data["util"])
        freq_str = f" @ {cpu_data['freq_ghz']:.2f} GHz" if cpu_data["freq_ghz"] else ""
        self.cpu_util_val_lbl.configure(text=f"{cpu_data['util']:.1f} %{freq_str}")

        # 4. GPU Util & Power
        self.gpu_util_graph.add_sample(gpu_data["util"])
        if gpu_data["util"] is not None:
            self.gpu_util_val_lbl.configure(text=f"{int(gpu_data['util'])} %")
        else:
            self.gpu_util_val_lbl.configure(text="N/A — sensor unavailable")

        if gpu_data["power"] is not None:
            self.power_draw_label.configure(text=f"GPU Power Draw: {gpu_data['power']:.1f} W")
        else:
            self.power_draw_label.configure(text="GPU Power Draw: N/A")

        # 5. Fan Speed
        if fan_rpm is not None:
            self.fan_rpm_label.configure(text=f"Fan Speed: {int(fan_rpm):,} RPM", text_color="#2ed573")
        else:
            self.fan_rpm_label.configure(text="Fan Speed: N/A — sensor unavailable", text_color="#747d8c")

    def gui_update_loop(self):
        """Smooth state badge and timer updates (~10 FPS)."""
        if not self.running:
            return

        # Update Runtime Timer
        if self.supervisor.is_running and self.start_time:
            elapsed = int(time.time() - self.start_time)
            m, s = divmod(elapsed, 60)
            h, m = divmod(m, 60)
            self.runtime_label.configure(text=f"Runtime: {h:02d}:{m:02d}:{s:02d}")

        # Update Status Badge
        st = self.current_state
        if "RAMPING" in st:
            self.status_badge.configure(text=f"⚡ {st}", text_color="#00d2d3", fg_color="#0b2c34")
        elif st == "JET ENGINE ACTIVE":
            self.status_badge.configure(text="🚀 JET ENGINE ACTIVE", text_color="#ff4757", fg_color="#3a131b")
        elif st == "THERMAL WARNING":
            self.status_badge.configure(text="⚠ THERMAL WARNING", text_color="#ffa502", fg_color="#352410")
        elif st == "THERMAL STOP":
            self.status_badge.configure(text="🛑 SAFETY TRIPPED", text_color="#ff4757", fg_color="#3a131b")
        elif st == "EMERGENCY HALTED":
            self.status_badge.configure(text="🚨 EMERGENCY STOPPED", text_color="#ff4757", fg_color="#3a131b")
        elif st == "STOPPED":
            self.status_badge.configure(text="⏹ STOPPED", text_color="#a4b0be", fg_color="#1e2230")
        else:
            self.status_badge.configure(text="● READY", text_color="#2ed573", fg_color="#102b1f")

        self.after(100, self.gui_update_loop)

    def on_close(self):
        """Guaranteed clean exit: terminates all child processes immediately."""
        self.running = False
        self.supervisor.stop_all_workers_now()
        self.destroy()


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    # Required for Windows multiprocessing support
    multiprocessing.freeze_support()
    app = LOQJetEngineApp()
    app.mainloop()
