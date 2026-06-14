"""
live_measure.py — FIXED DMM timeout issue
TDS 2014B + Keithley DMM 7510 → CSV logger
"""

import pyvisa
import csv
import time
from datetime import datetime

# ── Config ─────────────────────────────────────────────────
SCOPE_ADDR   = "USB0::0x0699::0x0368::C031361::INSTR"
DMM_ADDR     = "USB0::0x05E6::0x7510::04420289::INSTR"
CHANNEL      = "CH1"
SAMPLES      = 20
INTERVAL_SEC = 1.0
CSV_FILE     = f"dut_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# ── Connect ─────────────────────────────────────────────────
rm = pyvisa.ResourceManager()

scope = rm.open_resource(SCOPE_ADDR)
scope.timeout          = 5000
scope.write_termination = "\n"
scope.read_termination  = "\n"

dmm = rm.open_resource(DMM_ADDR)
dmm.timeout            = 15000   # increased to 15 seconds
dmm.write_termination  = "\n"
dmm.read_termination   = "\n"

print("=" * 55)
print(f"Scope : {scope.query('*IDN?').strip()}")
print(f"DMM   : {dmm.query('*IDN?').strip()}")
print("=" * 55)

# ── Setup DMM ───────────────────────────────────────────────
dmm.write("*RST")
dmm.write("*CLS")
time.sleep(2)                              # wait for reset to complete
dmm.write("SENS:FUNC 'VOLT:DC'")
dmm.write("SENS:VOLT:DC:RANG:AUTO ON")
dmm.write("SENS:VOLT:DC:NPLC 1")          # 1 power line cycle = fast + stable
time.sleep(0.5)

# ── Setup Scope ─────────────────────────────────────────────
scope.write(f"SELECT:{CHANNEL} ON")
scope.write(f"MEASUREMENT:IMMED:SOURCE {CHANNEL}")
scope.write("MEASUREMENT:IMMED:TYPE FREQUENCY")

# ── CSV ─────────────────────────────────────────────────────
with open(CSV_FILE, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        "Sample No.",
        "Timestamp",
        "Frequency (Hz)",
        "Frequency (kHz)",
        "DC Voltage (V)",
        "Status"
    ])

    print(f"\nLogging to : {CSV_FILE}")
    print(f"Samples    : {SAMPLES}")
    print(f"Interval   : {INTERVAL_SEC}s")
    print(f"{'─'*55}")
    print(f"{'#':<6} {'Time':<12} {'Frequency (Hz)':<20} {'Voltage (V)':<14} Status")
    print(f"{'─'*55}")

    for i in range(1, SAMPLES + 1):
        timestamp = datetime.now().strftime("%H:%M:%S")

        # ── Measure Frequency ──────────────────────────────
        raw_freq = scope.query("MEASUREMENT:IMMED:VALUE?").strip()
        freq_hz  = float(raw_freq)

        if freq_hz >= 9.0e37:
            freq_hz  = 0.0
            freq_khz = 0.0
            status   = "NO SIGNAL"
        else:
            freq_khz = freq_hz / 1000
            status   = "OK"

        # ── Measure Voltage — FIX: use READ? directly ─────
        # READ? = triggers + waits + returns in ONE command
        # Much more reliable than INIT + FETCH? separately
        raw_volt = dmm.query("READ?").strip()
        voltage  = float(raw_volt)

        # Print
        print(
            f"{i:<6} {timestamp:<12} "
            f"{freq_hz:<20.3f} "
            f"{voltage:<14.6f} "
            f"{status}"
        )

        # Write CSV
        writer.writerow([
            i,
            timestamp,
            f"{freq_hz:.3f}",
            f"{freq_khz:.3f}",
            f"{voltage:.6f}",
            status
        ])
        f.flush()

        time.sleep(INTERVAL_SEC)

# ── Summary ─────────────────────────────────────────────────
print(f"{'─'*55}")
print(f"\nDone! {SAMPLES} samples saved to: {CSV_FILE}")

# ── Cleanup ─────────────────────────────────────────────────
scope.close()
dmm.close()
rm.close()

# ── Preview CSV ─────────────────────────────────────────────
print(f"\nCSV Preview:")
print(f"{'─'*55}")
with open(CSV_FILE, 'r') as f:
    lines = f.readlines()
    for line in lines[:1]:
        print(line.strip())
    for line in lines[1:6]:
        print(line.strip())
