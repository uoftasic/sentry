module receiver #(
    parameter int SAMPLE_SIZE = 64 // SAMPLE_SIZE MUST BE MULTIPLES OF 16!!!
) (
    input logic clk,
    input logic reset_n,

    input logic [15:0] data_in,

    output logic event_valid,
    output logic [3:0] opcode,
    output logic [31:0] lba,
    output logic [15:0] block_count,
    output logic [15:0] time_delta,
    output logic [SAMPLE_SIZE - 1:0] data_sample
);

  typedef enum logic [2:0] {
    OPCD,
    ADDR,
    BLKCNT,
    SMPL,
    FINISH
  } state_t;

  state_t curr_state, next_state;

  // LBA counters
  logic addrCounter;
  localparam bit maxAddrCount = 1'b1;

  // Data sample counters
  localparam int numData = SAMPLE_SIZE / 16 - 1;  // max count
  localparam int numBits = $clog2(
      numData + 1
  );  // convert to binary to get number of bits, add 1 because numData starts from 0
  localparam bit [numBits - 1:0] maxSampleCount = numBits'(numData);
  logic [numBits - 1:0] sampleCounter;

  // Time delta counters
  logic [15:0] timeDeltaCounter;

  // Start reading indicator
  logic [7:0] start = 8'b11111111;

  always_comb
    case (curr_state)
      OPCD:
      if (data_in[15:8] == start) next_state = ADDR;
      else next_state = OPCD;
      ADDR:
      if (addrCounter == maxAddrCount)
        next_state = BLKCNT;  // addresses read, prepare to read block counts
      else next_state = ADDR;
      BLKCNT: next_state = SMPL;  // block counts read, prepare to read sample
      SMPL:
      if (sampleCounter == maxSampleCount) next_state = FINISH;  // sample read, finishing
      else next_state = SMPL;
      FINISH: next_state = OPCD;  // all done, getting ready for next cycle
      default: next_state = OPCD;
    endcase

  always_ff @(posedge clk)
    if (reset_n == 1'b0) begin
      opcode <= 4'b0;
      lba <= 32'b0;
      addrCounter <= 1'b0;
      block_count <= 16'b0;
      data_sample <= '0;
      sampleCounter <= '0;
      event_valid <= 1'b0;
      timeDeltaCounter <= 16'b0;
      time_delta <= 16'b0;
      curr_state <= OPCD;
    end else begin
      case (curr_state)
        OPCD: begin
          event_valid      <= 1'b0;
          timeDeltaCounter <= timeDeltaCounter + 16'b1;
          if (data_in[15:8] == start) begin
            opcode <= data_in[3:0];
            time_delta <= timeDeltaCounter;
            timeDeltaCounter <= 16'b0;
          end
        end
        ADDR: begin
          lba[31 - 16 * addrCounter -: 16] <= data_in;
          if (addrCounter == maxAddrCount) addrCounter <= 1'b0;
          else addrCounter <= addrCounter + 1'b1;
        end
        BLKCNT:  block_count <= data_in;
        SMPL: begin
          data_sample[SAMPLE_SIZE - 1 - 16 * sampleCounter -: 16] <= data_in;
          if (sampleCounter == maxSampleCount) sampleCounter <= '0;
          else sampleCounter <= sampleCounter + 1'b1;
        end
        FINISH: begin
          event_valid <= 1'b1;  // when finish is done, event_valid is true
        end
        default:;
      endcase
      curr_state <= next_state;
    end

endmodule
