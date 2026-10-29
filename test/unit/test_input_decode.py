import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


CLOCK_PERIOD_NS = 10


async def reset_dut(dut):
    dut.rst_n.value = 0

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_reset(dut):
    cocotb.start_soon(
        Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start()
    )

    await reset_dut(dut)

    # Add assertions for the expected reset state.
    # Example:
    # assert int(dut.output_signal.value) == 0


@cocotb.test()
async def test_basic_operation(dut):
    cocotb.start_soon(
        Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start()
    )

    await reset_dut(dut)

    # Drive inputs here.
    # Example:
    # dut.input_signal.value = 1
    # await RisingEdge(dut.clk)

    # Check outputs here.
    # Example:
    # assert int(dut.output_signal.value) == expected_value