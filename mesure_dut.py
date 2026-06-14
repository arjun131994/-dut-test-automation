import pyvisa

SCOPE_ADDR = "USB0::0x0699::0x0368::C031361::INSTR"
DMM_ADDR   = "USB0::0x05E6::0x7510::04420289::INSTR"
CHANNEL    = "CH1"

rm = pyvisa.ResourceManager()

# ── Connect scope ──────────────────────────────────────
scope = rm.open_resource(SCOPE_ADDR)
scope.timeout = 5000
scope.write_termination = "\n"
scope.read_termination  = "\n"
print("Scope  :", scope.query("*IDN?").strip())

# ── Connect DMM ────────────────────────────────────────
dmm = rm.open_resource(DMM_ADDR)
dmm.timeout = 5000
dmm.write_termination = "\n"
dmm.read_termination  = "\n"
print("DMM    :", dmm.query("*IDN?").strip())

# ── Measure Frequency (Scope) ──────────────────────────
scope.write(f"MEASUREMENT:IMMED:SOURCE {CHANNEL}")
scope.write("MEASUREMENT:IMMED:TYPE FREQUENCY")
freq = float(scope.query("MEASUREMENT:IMMED:VALUE?").strip())
print(f"\nFrequency : {freq:.3f} Hz")

# ── Measure DC Voltage (DMM) ───────────────────────────
dmm.write("SENS:FUNC 'VOLT:DC'")
dmm.write("SENS:VOLT:DC:RANG:AUTO ON")
dmm.write("INIT")
voltage = float(dmm.query("FETCH?").strip())
print(f"Voltage   : {voltage:.6f} V")

# ── Cleanup ────────────────────────────────────────────
scope.close()
dmm.close()
rm.close()