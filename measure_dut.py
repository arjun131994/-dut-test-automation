import pyvisa
import numpy as np
import matplotlib.pyplot as plt

SCOPE_ADDR = "USB0::0x0699::0x0368::C031361::INSTR"
DMM_ADDR   = "USB0::0x05E6::0x7510::04420289::INSTR"
CHANNEL    = "CH1"

rm = pyvisa.ResourceManager()

# ── Connect ────────────────────────────────────────────
scope = rm.open_resource(SCOPE_ADDR)
scope.timeout = 10000
scope.write_termination = "\n"
scope.read_termination  = "\n"

dmm = rm.open_resource(DMM_ADDR)
dmm.timeout = 5000
dmm.write_termination = "\n"
dmm.read_termination  = "\n"

print("Scope :", scope.query("*IDN?").strip())
print("DMM   :", dmm.query("*IDN?").strip())

# ── Measure Frequency ──────────────────────────────────
scope.write(f"MEASUREMENT:IMMED:SOURCE {CHANNEL}")
scope.write("MEASUREMENT:IMMED:TYPE FREQUENCY")
freq = float(scope.query("MEASUREMENT:IMMED:VALUE?").strip())

# ── Measure Voltage (DMM) ──────────────────────────────
dmm.write("SENS:FUNC 'VOLT:DC'")
dmm.write("SENS:VOLT:DC:RANG:AUTO ON")
dmm.write("INIT")
voltage = float(dmm.query("FETCH?").strip())

print(f"\nFrequency : {freq:.3f} Hz")
print(f"Voltage   : {voltage:.6f} V")

# ── Grab Waveform from Scope ───────────────────────────
scope.write(f"DATA:SOURCE {CHANNEL}")
scope.write("DATA:WIDTH 1")
scope.write("DATA:ENC RPB")          # Raw Positive Binary

# Get scaling factors
x_incr  = float(scope.query("WFMPRE:XINCR?"))
x_zero  = float(scope.query("WFMPRE:XZERO?"))
y_mult  = float(scope.query("WFMPRE:YMULT?"))
y_zero  = float(scope.query("WFMPRE:YZERO?"))
y_off   = float(scope.query("WFMPRE:YOFF?"))

# Transfer raw waveform bytes
scope.write("CURVE?")
raw = scope.read_raw()

# Strip header  (#<n><n bytes><data>)
header_len = 2 + int(chr(raw[1]))
data_bytes = raw[header_len:-1]      # trim trailing newline

# Convert to voltage values
samples = np.frombuffer(data_bytes, dtype=np.uint8).astype(float)
voltage_wave = (samples - y_off) * y_mult + y_zero

# Build time axis
n = len(voltage_wave)
time_axis = x_zero + np.arange(n) * x_incr
time_us   = time_axis * 1e6          # convert to microseconds

# ── Plot ───────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7))
fig.suptitle("DUT Measurement Dashboard", fontsize=14, fontweight="bold")

# Waveform plot
ax1.plot(time_us, voltage_wave, color="#1f77b4", linewidth=1)
ax1.set_xlabel("Time (µs)")
ax1.set_ylabel("Voltage (V)")
ax1.set_title(f"Oscilloscope Waveform — {CHANNEL}   |   Frequency: {freq:.2f} Hz")
ax1.grid(True, linestyle="--", alpha=0.5)
ax1.axhline(0, color="gray", linewidth=0.8)

# Voltage bar (DMM reading)
ax2.barh(["DMM DC Voltage"], [voltage], color="#2ca02c", height=0.4)
ax2.set_xlabel("Voltage (V)")
ax2.set_title(f"Keithley DMM 7510 — DC Voltage: {voltage:.6f} V")
ax2.axvline(0, color="gray", linewidth=0.8)
ax2.set_xlim(left=min(0, voltage - abs(voltage)*0.2),
             right=max(voltage + abs(voltage)*0.2, 0.1))
for spine in ["top", "right"]:
    ax2.spines[spine].set_visible(False)

plt.tight_layout()
plt.savefig("dut_measurement.png", dpi=150, bbox_inches="tight")
plt.show()
print("\nGraph saved as dut_measurement.png")

# ── Cleanup ────────────────────────────────────────────
scope.close()
dmm.close()
rm.close()