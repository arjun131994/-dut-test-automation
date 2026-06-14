"""
test_dut.py
═══════════════════════════════════════════════════════════════
Dual-instrument pytest suite for DUT verification:
  ✔ TDS 2014B  → frequency measurement
  ✔ Keithley DMM 7510 → DC / AC voltage measurement
  ✔ Combined test  → freq + voltage in one test
  ✔ Parametrize, markers, assert, xfail, skip
═══════════════════════════════════════════════════════════════
"""

import time
import statistics
import pytest


# ═══════════════════════════════════════════════════════════════
# HELPERS — SCOPE
# ═══════════════════════════════════════════════════════════════

def measure_freq(scope, channel: str, retries: int = 3) -> float:
    """
    Query frequency from TDS 2014B via SCPI.
    Returns Hz. Retries on Tektronix sentinel 9.9E+37.
    """
    scope.write(f"MEASUREMENT:IMMED:SOURCE {channel}")
    scope.write("MEASUREMENT:IMMED:TYPE FREQUENCY")

    for _ in range(retries):
        raw      = scope.query("MEASUREMENT:IMMED:VALUE?").strip()
        freq_hz  = float(raw)
        if freq_hz < 9.0e37:
            return freq_hz
        time.sleep(0.5)

    pytest.fail(
        f"TDS 2014B: no valid frequency after {retries} retries. "
        f"Last raw = {raw}. Check probe / trigger / signal."
    )


# ═══════════════════════════════════════════════════════════════
# HELPERS — DMM 7510
# ═══════════════════════════════════════════════════════════════

def measure_voltage_dc(dmm, v_range: str = "AUTO") -> float:
    """
    Measure DC voltage with Keithley DMM 7510.
    v_range: 'AUTO' or explicit range e.g. '10' (10 V range)
    Returns volts (float).
    """
    if v_range == "AUTO":
        dmm.write("SENS:VOLT:DC:RANG:AUTO ON")
    else:
        dmm.write("SENS:VOLT:DC:RANG:AUTO OFF")
        dmm.write(f"SENS:VOLT:DC:RANG {v_range}")

    dmm.write("SENS:FUNC 'VOLT:DC'")
    dmm.write("INIT")
    raw = dmm.query("FETCH?").strip()
    return float(raw)


def measure_voltage_ac(dmm, v_range: str = "AUTO") -> float:
    """
    Measure AC RMS voltage with Keithley DMM 7510.
    Returns volts RMS (float).
    """
    if v_range == "AUTO":
        dmm.write("SENS:VOLT:AC:RANG:AUTO ON")
    else:
        dmm.write("SENS:VOLT:AC:RANG:AUTO OFF")
        dmm.write(f"SENS:VOLT:AC:RANG {v_range}")

    dmm.write("SENS:FUNC 'VOLT:AC'")
    dmm.write("INIT")
    raw = dmm.query("FETCH?").strip()
    return float(raw)


def within_tolerance(measured: float, expected: float, tol_pct: float) -> bool:
    """True if |measured - expected| / expected  <=  tol_pct / 100."""
    if expected == 0:
        return abs(measured) < 1e-9
    return abs(measured - expected) / abs(expected) <= tol_pct / 100.0


# ═══════════════════════════════════════════════════════════════
# TEST 1 — Smoke: scope reads a frequency
# ═══════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_scope_frequency_readable(scope, channel, autoscale):
    """
    Smoke: TDS 2014B must return a positive, finite frequency.
    """
    freq = measure_freq(scope, channel)
    assert freq > 0,   f"Expected positive freq, got {freq} Hz"
    assert freq < 1e9, f"Freq {freq} Hz too high for this scope"
    print(f"\n[smoke-scope]  Frequency = {freq:.3f} Hz")


# ═══════════════════════════════════════════════════════════════
# TEST 2 — Smoke: DMM reads a DC voltage
# ═══════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_dmm_voltage_readable(dmm):
    """
    Smoke: Keithley DMM 7510 must return a finite DC voltage.
    """
    voltage = measure_voltage_dc(dmm)
    assert voltage is not None
    assert abs(voltage) < 1100, f"Voltage {voltage} V out of DMM range"
    print(f"\n[smoke-dmm]    DC Voltage = {voltage:.6f} V")


# ═══════════════════════════════════════════════════════════════
# TEST 3 — Parametrize: expected DUT frequencies
# ═══════════════════════════════════════════════════════════════

FREQ_CASES = [
    (50.0,        2.0,  "50Hz_mains"),
    (1_000.0,     1.0,  "1kHz"),
    (10_000.0,    1.0,  "10kHz"),
    (100_000.0,   0.5,  "100kHz"),
    (1_000_000.0, 0.5,  "1MHz"),
]

@pytest.mark.regression
@pytest.mark.parametrize(
    "expected_hz, tol_pct, label",
    FREQ_CASES,
    ids=[c[2] for c in FREQ_CASES],
)
def test_frequency_tolerance(scope, channel, expected_hz, tol_pct, label):
    """
    Parametrized frequency test. Configure DUT to each frequency before run
    or drive it programmatically via a signal generator.
    """
    freq = measure_freq(scope, channel)

    assert within_tolerance(freq, expected_hz, tol_pct), (
        f"[{label}] FAIL: expected {expected_hz:.1f} Hz ±{tol_pct}%, "
        f"got {freq:.3f} Hz  (Δ={abs(freq-expected_hz)/expected_hz*100:.2f}%)"
    )
    print(
        f"\n[{label}]  expected={expected_hz:.1f} Hz  "
        f"measured={freq:.3f} Hz  "
        f"Δ={abs(freq-expected_hz)/expected_hz*100:.3f}%  ✔"
    )


# ═══════════════════════════════════════════════════════════════
# TEST 4 — Parametrize: expected DUT DC voltages
# ═══════════════════════════════════════════════════════════════

VOLTAGE_CASES = [
    (3.3,  2.0, "3V3_rail"),
    (5.0,  2.0, "5V_rail"),
    (12.0, 1.0, "12V_rail"),
    (24.0, 1.0, "24V_rail"),
]

@pytest.mark.regression
@pytest.mark.parametrize(
    "expected_v, tol_pct, label",
    VOLTAGE_CASES,
    ids=[c[2] for c in VOLTAGE_CASES],
)
def test_voltage_dc_tolerance(dmm, expected_v, tol_pct, label):
    """
    Parametrized DC voltage test. Probe each DUT rail.
    """
    voltage = measure_voltage_dc(dmm)

    assert within_tolerance(voltage, expected_v, tol_pct), (
        f"[{label}] FAIL: expected {expected_v:.2f} V ±{tol_pct}%, "
        f"got {voltage:.6f} V  (Δ={abs(voltage-expected_v)/expected_v*100:.3f}%)"
    )
    print(
        f"\n[{label}]  expected={expected_v:.2f} V  "
        f"measured={voltage:.6f} V  "
        f"Δ={abs(voltage-expected_v)/expected_v*100:.3f}%  ✔"
    )


# ═══════════════════════════════════════════════════════════════
# TEST 5 — Combined: frequency + voltage in one test
# ═══════════════════════════════════════════════════════════════

COMBINED_CASES = [
    # (freq_hz, freq_tol%, voltage_v, volt_tol%, label)
    (1_000.0, 1.0, 3.3, 2.0, "1kHz_3V3"),
    (10_000.0, 1.0, 5.0, 2.0, "10kHz_5V"),
]

@pytest.mark.regression
@pytest.mark.parametrize(
    "exp_hz, freq_tol, exp_v, volt_tol, label",
    COMBINED_CASES,
    ids=[c[4] for c in COMBINED_CASES],
)
def test_combined_freq_and_voltage(scope, channel, dmm, exp_hz, freq_tol, exp_v, volt_tol, label):
    """
    Combined test: measures frequency on scope AND voltage on DMM.
    Both must pass for test to pass.
    """
    freq    = measure_freq(scope, channel)
    voltage = measure_voltage_dc(dmm)

    freq_ok = within_tolerance(freq,    exp_hz, freq_tol)
    volt_ok = within_tolerance(voltage, exp_v,  volt_tol)

    print(
        f"\n[{label}]  "
        f"freq={freq:.2f} Hz (exp={exp_hz}, {'✔' if freq_ok else '✘'})  "
        f"voltage={voltage:.4f} V (exp={exp_v}, {'✔' if volt_ok else '✘'})"
    )

    assert freq_ok, (
        f"[{label}] Frequency FAIL: expected {exp_hz} Hz ±{freq_tol}%, "
        f"got {freq:.3f} Hz"
    )
    assert volt_ok, (
        f"[{label}] Voltage FAIL: expected {exp_v} V ±{volt_tol}%, "
        f"got {voltage:.6f} V"
    )


# ═══════════════════════════════════════════════════════════════
# TEST 6 — AC voltage parametrize
# ═══════════════════════════════════════════════════════════════

AC_VOLTAGE_CASES = [
    (5.0,  3.0, "5Vrms_ac"),
    (12.0, 2.0, "12Vrms_ac"),
]

@pytest.mark.regression
@pytest.mark.parametrize(
    "expected_v, tol_pct, label",
    AC_VOLTAGE_CASES,
    ids=[c[2] for c in AC_VOLTAGE_CASES],
)
def test_voltage_ac_tolerance(dmm, expected_v, tol_pct, label):
    """
    Parametrized AC RMS voltage test using DMM 7510.
    """
    voltage = measure_voltage_ac(dmm)

    assert within_tolerance(voltage, expected_v, tol_pct), (
        f"[{label}] FAIL: expected {expected_v:.2f} Vrms ±{tol_pct}%, "
        f"got {voltage:.6f} Vrms"
    )
    print(f"\n[{label}]  AC RMS = {voltage:.6f} V  ✔")


# ═══════════════════════════════════════════════════════════════
# TEST 7 — Stability: frequency stddev over N samples
# ═══════════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.parametrize("n_samples, max_stddev_pct", [
    (10, 0.5),
    (30, 0.3),
], ids=["stability_10", "stability_30"])
def test_frequency_stability(scope, channel, n_samples, max_stddev_pct):
    """Catch DUT jitter by checking stddev of N frequency samples."""
    samples = []
    for _ in range(n_samples):
        samples.append(measure_freq(scope, channel))
        time.sleep(0.1)

    mean       = statistics.mean(samples)
    stddev     = statistics.stdev(samples)
    stddev_pct = (stddev / mean) * 100 if mean else 0

    assert stddev_pct <= max_stddev_pct, (
        f"Frequency unstable: mean={mean:.3f} Hz, "
        f"stddev={stddev:.4f} Hz ({stddev_pct:.3f}%) > limit {max_stddev_pct}%"
    )
    print(f"\n[stability] n={n_samples}  mean={mean:.3f} Hz  stddev={stddev_pct:.3f}%  ✔")


# ═══════════════════════════════════════════════════════════════
# TEST 8 — Voltage stability: stddev over N samples
# ═══════════════════════════════════════════════════════════════

@pytest.mark.slow
@pytest.mark.parametrize("n_samples, max_stddev_mv", [
    (10, 5.0),   # stddev < 5 mV
    (30, 3.0),   # stddev < 3 mV
], ids=["vstab_10", "vstab_30"])
def test_voltage_stability(dmm, n_samples, max_stddev_mv):
    """Check DC voltage stability from DMM 7510 over N samples."""
    samples = []
    for _ in range(n_samples):
        samples.append(measure_voltage_dc(dmm))
        time.sleep(0.1)

    mean       = statistics.mean(samples)
    stddev_mv  = statistics.stdev(samples) * 1000   # convert to mV

    assert stddev_mv <= max_stddev_mv, (
        f"Voltage unstable: mean={mean:.4f} V, "
        f"stddev={stddev_mv:.3f} mV > limit {max_stddev_mv} mV"
    )
    print(f"\n[vstab] n={n_samples}  mean={mean:.4f} V  stddev={stddev_mv:.3f} mV  ✔")


# ═══════════════════════════════════════════════════════════════
# TEST 9 — xfail: high-freq edge case
# ═══════════════════════════════════════════════════════════════

@pytest.mark.xfail(reason="DUT may not support >50 MHz", strict=False)
@pytest.mark.regression
def test_high_frequency_edge(scope, channel):
    """Marked xfail — won't block CI if DUT doesn't reach 50 MHz."""
    freq = measure_freq(scope, channel)
    assert freq >= 50_000_000, f"Freq {freq} Hz below 50 MHz threshold"


# ═══════════════════════════════════════════════════════════════
# TEST 10 — skip: CH1-only test
# ═══════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_frequency_ch1_only(scope, request):
    """Skips automatically if not running on CH1."""
    ch = request.config.getoption("--scope-channel")
    if ch != "CH1":
        pytest.skip(f"Test requires CH1, but got --scope-channel={ch}")

    freq = measure_freq(scope, "CH1")
    assert freq > 0, "No valid frequency on CH1"
    print(f"\n[ch1-only]  CH1 freq = {freq:.3f} Hz  ✔")
