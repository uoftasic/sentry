// Module for window controller

// For every event:
//   1. event is sent to every feature tracker (tracker_event_valid)
//   2. increment the event count
//
// When WINDOW_SIZE events have been processed:
//   1. Every tracker's features are collected
//   2. combined into one vector: the top level concatenates the trackers'
//      feature outputs onto features_in.
//   3. features_in is latched into feature_vector and feature_valid pulses for
//      one cycle. window_index identifies the window (0, 1, 2, ...).
//   4. window_reset pulses for one cycle to clear every tracker's window state.
//   5. Counting restarts for the next window.

module window_controller #(
    parameter int WINDOW_SIZE   = 64,  // see issue on github
    parameter int FEATURE_WIDTH = 16,  // width of the concatenated feature bus
    parameter int INDEX_WIDTH   = 8    // window index width, wraps around
) 
(   input logic clk,
    input logic reset_n,

    input logic event_valid, // from input_receiver.sv

    output logic tracker_event_valid, // To / from the feature trackers
    output logic window_reset,
    input  logic [FEATURE_WIDTH - 1:0] features_in,

    // To the classifier
    output logic feature_valid,
    output logic [FEATURE_WIDTH - 1:0] feature_vector,
    output logic [INDEX_WIDTH - 1:0] window_index
);

  localparam int countWidth = $clog2(WINDOW_SIZE + 1); // Width of the event counter
  localparam bit [countWidth - 1:0] lastCount = countWidth'(WINDOW_SIZE - 1); // the counter value on the last event of a window.

  logic [countWidth - 1:0] event_count;  // events seen in the current window
  logic capture;  // high for the cycle after the last event of a window


  assign tracker_event_valid = event_valid; // send every event to every tracker

  always_ff @(posedge clk)
    if (reset_n == 1'b0) 
      begin
        event_count <= '0;
        capture <= 1'b0;
        feature_valid <= 1'b0;
        feature_vector <= '0;
        window_index <= '1;  // first completed window wraps this to 0
      end
    else
      begin
        capture <= 1'b0;
        feature_valid <= 1'b0;

        // count events and detect the end of the window.
        if (event_valid)
        begin
          if (event_count == lastCount) begin
            event_count <= '0;  // step 5: begin the next window
            capture     <= 1'b1;
          end else begin
            event_count <= event_count + 1'b1;
          end
        end

      //  the combined feature vector.
      if (capture) begin
        feature_vector <= features_in;
        feature_valid  <= 1'b1;
        window_index   <= window_index + 1'b1;
      end
    end

  assign window_reset = capture;

`ifndef SYNTHESIS
  always @(posedge clk)
    if (reset_n && capture && event_valid)
      $error("window_controller: event_valid asserted during window_reset");
`endif

endmodule
