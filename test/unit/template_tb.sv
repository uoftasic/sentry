`default_nettype none
`timescale 1ns / 1ps

// ============================================================================
// Template self-checking SystemVerilog testbench
// ============================================================================
//
// Copy this file to test/unit/<module>_tb.sv and edit the sections marked
// TODO. The example DUT is input_receiver so the template compiles and runs
// as-is.
//
// Run from the repository root (Icarus Verilog):
//
//   iverilog -g2012 -Wall -I src -s template_tb -o build/template_tb.vvp \
//       src/*.sv test/unit/template_tb.sv
//   vvp build/template_tb.vvp
//
// View waveforms with:
//
//   gtkwave template_tb.fst     (or surfer template_tb.fst)
//
// Timing convention used in this file:
//   - The DUT samples inputs on the RISING edge of clk.
//   - The testbench drives inputs on the FALLING edge, so inputs are stable
//     half a period before the DUT samples them. This avoids races between
//     the testbench and the DUT without needing clocking blocks.
//   - The testbench checks outputs shortly after the rising edge, once the
//     DUT's nonblocking assignments have updated.
// ============================================================================

module template_tb;

  // --------------------------------------------------------------------------
  // Parameters
  // --------------------------------------------------------------------------
  localparam int CLK_PERIOD_NS = 10;  // 100 MHz
  localparam int TIMEOUT_CYCLES = 10_000;  // Safety net for hung simulations

  // TODO: DUT parameters.
  localparam int SAMPLE_SIZE = 64;

  // --------------------------------------------------------------------------
  // Clock and reset
  // --------------------------------------------------------------------------
  logic clk = 1'b0;
  logic reset_n = 1'b0;  // Active-low reset, asserted at time 0

  always #(CLK_PERIOD_NS / 2) clk = ~clk;

  // --------------------------------------------------------------------------
  // DUT signals
  // --------------------------------------------------------------------------
  // TODO: Declare one signal per DUT port.
  logic [15:0] data_in = '0;

  logic event_valid;
  logic [3:0] opcode;
  logic [31:0] lba;
  logic [15:0] block_count;
  logic [15:0] time_delta;
  logic [SAMPLE_SIZE-1:0] data_sample;

  // --------------------------------------------------------------------------
  // DUT instance
  // --------------------------------------------------------------------------
  // TODO: Replace with the module under test. Use named port connections.
  input_receiver #(
      .SAMPLE_SIZE(SAMPLE_SIZE)
  ) dut (
      .clk        (clk),
      .reset_n    (reset_n),
      .data_in    (data_in),
      .event_valid(event_valid),
      .opcode     (opcode),
      .lba        (lba),
      .block_count(block_count),
      .time_delta (time_delta),
      .data_sample(data_sample)
  );

  // --------------------------------------------------------------------------
  // Waveform dump
  // --------------------------------------------------------------------------
  initial begin
    $dumpfile("template_tb.fst");
    $dumpvars(0, template_tb);
  end

  // --------------------------------------------------------------------------
  // Timeout watchdog
  // --------------------------------------------------------------------------
  initial begin
    repeat (TIMEOUT_CYCLES) @(posedge clk);
    $fatal(1, "TIMEOUT: simulation exceeded %0d cycles", TIMEOUT_CYCLES);
  end

  // --------------------------------------------------------------------------
  // Error tracking
  // --------------------------------------------------------------------------
  int error_count = 0;

  // Compare an actual value with an expected value and report mismatches.
  // Values up to 64 bits wide are supported; widen if needed.
  task automatic check(input string name, input logic [63:0] actual,
                       input logic [63:0] expected);
    if (actual !== expected) begin
      $error("[%0t] %s: expected 0x%0h, got 0x%0h", $time, name, expected, actual);
      error_count++;
    end
  endtask

  // --------------------------------------------------------------------------
  // Helper tasks
  // --------------------------------------------------------------------------

  // Hold reset for the given number of rising edges, then release it.
  // reset_n is synchronous in this DUT, so it must cover at least one edge.
  task automatic reset_dut(input int cycles);
    @(negedge clk);
    reset_n = 1'b0;
    repeat (cycles) @(posedge clk);
    @(negedge clk);
    reset_n = 1'b1;
  endtask

  // Drive one value for one clock cycle.
  // Returns just after the rising edge, when DUT outputs have updated.
  task automatic drive_word(input logic [15:0] word);
    @(negedge clk);
    data_in = word;
    @(posedge clk);
    #1;  // Let nonblocking assignments settle before checks
  endtask

  // Wait for a number of idle cycles while holding the input at zero.
  task automatic idle(input int cycles);
    repeat (cycles) drive_word(16'h0000);
  endtask

  // --------------------------------------------------------------------------
  // Tests
  // --------------------------------------------------------------------------
  // TODO: Replace these with tests for your module. Keep each test small and
  // reset the DUT at the start so tests do not depend on each other.

  task automatic test_reset_state();
    $display("[%0t] test_reset_state", $time);
    reset_dut(2);
    check("event_valid", event_valid, 0);
    check("opcode", opcode, 0);
    check("lba", lba, 0);
    check("block_count", block_count, 0);
    check("data_sample", data_sample, 0);
  endtask

  task automatic test_basic_operation();
    $display("[%0t] test_basic_operation", $time);
    reset_dut(2);

    // Drive inputs.
    drive_word(16'hFF0A);  // Trigger, opcode 0xA
    drive_word(16'h1234);  // LBA high word
    drive_word(16'h5678);  // LBA low word
    drive_word(16'h0042);  // Block count
    drive_word(16'h0123);  // Sample words
    drive_word(16'h4567);
    drive_word(16'h89AB);
    drive_word(16'hCDEF);
    drive_word(16'h0000);  // FINISH cycle

    // Check outputs.
    check("event_valid", event_valid, 1);
    check("opcode", opcode, 4'hA);
    check("lba", lba, 32'h1234_5678);
    check("block_count", block_count, 16'h0042);
    check("data_sample", data_sample, 64'h0123_4567_89AB_CDEF);

    idle(1);
    check("event_valid after pulse", event_valid, 0);
  endtask

  // --------------------------------------------------------------------------
  // Main sequence
  // --------------------------------------------------------------------------
  initial begin
    test_reset_state();
    test_basic_operation();

    if (error_count == 0) begin
      $display("PASS: all checks passed");
      $finish;
    end else begin
      $fatal(1, "FAIL: %0d check(s) failed", error_count);
    end
  end

endmodule

`default_nettype wire
