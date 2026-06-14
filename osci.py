"""
live_measure.py
═══════════════════════════════════════════════════════════════
Live DUT measurement — TDS 2014B + Keithley DMM 7510
Measures frequency + voltage continuously and logs to CSV
═══════════════════════════════════════════════════════════════
"""

import pyvisa
import csv
import time
import os
from datetime import datetime

# ── Config ─────────────────────────────────────────────────
SCOPE_ADDR   = "USB0::0x0699::0x0368::C031361::INSTR"
DMM_ADDR     = "USB0::0x05E6::0x7510::04420289::INSTR"
CHANNEL      = "CH1"
SAMPLES      = 20          # how many readings to take
INTERVAL_SEC = 1.0         # delay between each reading
CSV_FILE     = f"dut_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# ── Connect instruments ────────────────────────────────────
rm = pyvisa.ResourceManager()

scope = rm.open_resource(SCOPE_ADDR)
scope.timeout          = 5000
scope.write_termination = "\n"
scope.read_termination  = "\n"

dmm = rm.open_resource(DMM_ADDR)
dmm.timeout            = 10000
dmm.write_termination  = "\n"
dmm.read_termination   = "\n"

print("=" * 55)
print(f"Scope : {scope.query('*IDN?').strip()}")
print(f"DMM   : {dmm.query('*IDN?').strip()}")
print("=" * 55)

# ── Setup DMM for DC voltage ───────────────────────────────
dmm.write("*RST")
dmm.write("*CLS")
dmm.write("SENS:FUNC 'VOLT:DC'")
dmm.write("SENS:VOLT:DC:RANG:AUTO ON")

# ── Setup scope channel ────────────────────────────────────
scope.write(f"SELECT:{CHANNEL} ON")
scope.write(f"MEASUREMENT:IMMED:SOURCE {CHANNEL}")
scope.write("MEASUREMENT:IMMED:TYPE FREQUENCY")

# ── CSV setup ──────────────────────────────────────────────
with open(CSV_FILE, mode='w', newline='') as f:
    writer = csv.writer(f)

    # Write header
    writer.writerow([
        "Sample No.",
        "Timestamp",
        "Frequency (Hz)",
        "Frequency (kHz)",
        "DC Voltage (V)",
        "Status"
    ])

    print(f"\nLogging to: {CSV_FILE}")
    print(f"{'─'*55}")
    print(f"{'#':<6} {'Time':<12} {'Frequency':<18} {'Voltage':<14} {'Status'}")
    print(f"{'─'*55}")

    # ── Measurement loop ───────────────────────────────────
    for i in range(1, SAMPLES + 1):
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Measure frequency from scope
        raw_freq = scope.query("MEASUREMENT:IMMED:VALUE?").strip()
        freq_hz  = float(raw_freq)

        # Check Tektronix sentinel value
        if freq_hz >= 9.0e37:
            freq_hz  = 0.0
            freq_khz = 0.0
            status   = "NO SIGNAL"
        else:
            freq_khz = freq_hz / 1000
            status   = "OK"

        # Measure voltage from DMM
        dmm.write("INIT")
        raw_volt = dmm.query("FETCH?").strip()
        voltage  = float(raw_volt)

        # Print to terminal
        print(
            f"{i:<6} {timestamp:<12} "
            f"{freq_hz:<18.3f} "
            f"{voltage:<14.6f} "
            f"{status}"
        )

        # Write to CSV
        writer.writerow([
            i,
            timestamp,
            f"{freq_hz:.3f}",
            f"{freq_khz:.3f}",
            f"{voltage:.6f}",
            status
        ])

        f.flush()   # write to disk immediately

        time.sleep(INTERVAL_SEC)

# ── Summary ────────────────────────────────────────────────
print(f"{'─'*55}")
print(f"\nDone! {SAMPLES} samples logged to: {CSV_FILE}")

# ── Cleanup ────────────────────────────────────────────────
scope.close()
dmm.close()
rm.close()

# ── Print CSV summary ──────────────────────────────────────
print("\nCSV Preview (last 5 rows):")
print(f"{'─'*55}")
with open(CSV_FILE, 'r') as f:
    lines = f.readlines()
    for line in lines[:1]:           # header
        print(line.strip())
    for line in lines[-5:]:          # last 5 rows
        print(line.strip())
