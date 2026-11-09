import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ReadWrite, RisingEdge

async def drive_word(dut, word: int) -> None:
    """Put one 16-bit word on data_in for one clock cycle."""
    dut.data_in.value = word
    await RisingEdge(dut.clk)
    await ReadWrite()

async def reset_dut(dut) -> None:
    # reset_n is synchronous, so reset must cover a rising clock edge.
    dut.reset_n.value = 0
    await drive_word(dut, 0)
    await drive_word(dut, 0)
    dut.reset_n.value = 1

async def send_event(
    dut,
    opcode: int,
    lba: int,
    block_count: int,
    samples: list[int],
) -> None:
    """Send one complete receiver frame."""
    assert len(samples) == 4  # SAMPLE_SIZE is 64 bits by default

    # Trigger word: upper byte must be 0xff.
    await drive_word(dut, 0xFF00 | (opcode & 0xF))

    # LBA is transmitted big-endian.
    await drive_word(dut, (lba >> 16) & 0xFFFF)
    await drive_word(dut, lba & 0xFFFF)

    await drive_word(dut, block_count & 0xFFFF)

    # Four 16-bit sample words.
    for sample in samples:
        await drive_word(dut, sample & 0xFFFF)

    # The decoder enters FINISH after the final sample.
    # event_valid becomes high on this following cycle.
    await drive_word(dut, 0)

@cocotb.test()
async def test_receiver_decodes_event(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    samples = [0x0123, 0x4567, 0x89AB, 0xCDEF]

    await send_event(
        dut,
        opcode=0xA,
        lba=0x12345678,
        block_count=0x0042,
        samples=samples,
    )

    assert int(dut.event_valid.value) == 1
    assert int(dut.opcode.value) == 0xA
    assert int(dut.lba.value) == 0x12345678
    assert int(dut.block_count.value) == 0x0042
    assert int(dut.time_delta.value) == 0

    # Samples are packed in the same order they were received.
    assert int(dut.data_sample.value) == 0x0123456789ABCDEF

    # event_valid is a one-cycle pulse.
    await drive_word(dut, 0)
    assert int(dut.event_valid.value) == 0

@cocotb.test()
async def test_receiver_ignores_invalid_trigger(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    # None of these words has an upper byte of 0xff.
    for word in [0x0000, 0xFE00, 0x1234]:
        await drive_word(dut, word)
        assert int(dut.event_valid.value) == 0

@cocotb.test()
async def test_trigger_like_values_are_valid_payload(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    # Values with an upper byte of 0xff are payload while the decoder
    # is reading the address, block count, or samples.
    await drive_word(dut, 0xFF0A)  # trigger, opcode = 0xA
    await drive_word(dut, 0xFFFF)  # LBA high word
    await drive_word(dut, 0xFFEE)  # LBA low word
    await drive_word(dut, 0xFFFF)  # block count

    samples = [0x1111, 0xFF22, 0x3333, 0xFF44]
    for sample in samples:
        await drive_word(dut, sample)

    await drive_word(dut, 0)

    assert int(dut.event_valid.value) == 1
    assert int(dut.opcode.value) == 0xA
    assert int(dut.lba.value) == 0xFFFF_FFEE
    assert int(dut.block_count.value) == 0xFFFF
    assert int(dut.data_sample.value) == 0x1111_FF22_3333_FF44

@cocotb.test()
async def test_receiver_time_delta(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    # The first trigger occurs immediately after reset.
    await send_event(
        dut,
        opcode=1,
        lba=0x00000001,
        block_count=1,
        samples=[1, 2, 3, 4],
    )
    assert int(dut.time_delta.value) == 0

    # Three idle OPCD cycles occur before the next trigger.
    for _ in range(3):
        await drive_word(dut, 0)

    await send_event(
        dut,
        opcode=2,
        lba=0x00000002,
        block_count=2,
        samples=[5, 6, 7, 8],
    )

    assert int(dut.event_valid.value) == 1
    assert int(dut.time_delta.value) == 3
