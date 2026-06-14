"""
conftest.py
Shared fixtures for:
  - Tektronix TDS 2014B  (oscilloscope  → frequency measurement)
  - Keithley DMM 7510    (multimeter    → voltage measurement)
Both connected via USB.
"""
import pytest
import pyvisa


# ──────────────────────────────────────────────────────────────
# CLI OPTIONS
# ──────────────────────────────────────────────────────────────
def pytest_addoption(parser):
    parser.addoption(
        "--scope-addr",
        default="USB0::0x0699::0x036A::XXXXXXXX::INSTR",
        help="VISA address of Tektronix TDS 2014B",
    )
    parser.addoption(
        "--dmm-addr",
        default="USB0::0x05E6::0x7510::XXXXXXXX::INSTR",
        help="VISA address of Keithley DMM 7510",
    )
    parser.addoption(
        "--scope-channel",
        default="CH1",
        help="Oscilloscope channel: CH1 / CH2 / CH3 / CH4",
    )


# ──────────────────────────────────────────────────────────────
# OSCILLOSCOPE FIXTURE  (TDS 2014B)
# ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def scope(request):
    """
    Open USB connection to Tektronix TDS 2014B.
    Session-scoped → one connection for entire test run.
    """
    addr = request.config.getoption("--scope-addr")
    rm   = pyvisa.ResourceManager()
    inst = rm.open_resource(addr)
    inst.timeout          = 5000
    inst.write_termination = "\n"
    inst.read_termination  = "\n"

    idn = inst.query("*IDN?")
    assert "TEKTRONIX" in idn.upper(), f"Not a Tektronix scope! IDN: {idn}"
    print(f"\n[scope]  Connected → {idn.strip()}")

    yield inst

    inst.write("*CLS")
    inst.close()
    rm.close()


# ──────────────────────────────────────────────────────────────
# DMM FIXTURE  (Keithley DMM 7510)
# ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def dmm(request):
    """
    Open USB connection to Keithley DMM 7510.
    Session-scoped → one connection for entire test run.
    """
    addr = request.config.getoption("--dmm-addr")
    rm   = pyvisa.ResourceManager()
    inst = rm.open_resource(addr)
    inst.timeout          = 10000   # DMM needs more time for ranging
    inst.write_termination = "\n"
    inst.read_termination  = "\n"

    idn = inst.query("*IDN?")
    assert "KEITHLEY" in idn.upper(), f"Not a Keithley DMM! IDN: {idn}"
    print(f"\n[dmm]    Connected → {idn.strip()}")

    # Reset to known state
    inst.write("*RST")
    inst.write("*CLS")

    yield inst

    inst.write("*CLS")
    inst.close()


# ──────────────────────────────────────────────────────────────
# CHANNEL FIXTURE
# ──────────────────────────────────────────────────────────────
@pytest.fixture
def channel(request, scope):
    """Return the scope channel string and ensure it is ON."""
    ch = request.config.getoption("--scope-channel")
    scope.write(f"SELECT:{ch} ON")
    return ch


# ──────────────────────────────────────────────────────────────
# AUTOSCALE FIXTURE
# ──────────────────────────────────────────────────────────────
@pytest.fixture
def autoscale(scope):
    """Run AUTOSET on the scope before a test."""
    import time
    scope.write("AUTOSET EXECUTE")
    time.sleep(3)
    yield
