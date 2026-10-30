module receiver #(
    parameter SAMPLE_SIZE = 64
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

  typedef enum logic [3:0] {
    OPCD,
    ADDR,
    BLKCNT,
    SMPL,
    FINSH
  } state_t;

  state_t curr_state, next_state;

  logic addrCounter;
  logic [ 1:0] sampleCounter;
  logic [15:0] timeDeltaCounter;
  localparam bit maxAddrCount = 1'b1;
  localparam bit [1:0] maxSampleCount = 2'b11;

  always_comb
    case (curr_state)
      OPCD:
        if (data_in[15:8] == 8'b11111111) next_state = ADDR;
        else next_state = OPCD;
      ADDR:
        if (addrCounter == maxAddrCount) next_state = BLKCNT;  // addresses read, prepare to read block counts
        else next_state = ADDR;
      BLKCNT: next_state = SMPL;  // block counts read, prepare to read sample
      SMPL:
        if (sampleCounter == maxSampleCount) next_state = FINSH;  // sample read, finishing
        else next_state = SMPL;
      FINSH: next_state = OPCD;  // all done, getting ready for next cycle
      default: next_state = OPCD;
    endcase

  always_ff @(posedge clk)
    if (reset_n == 1'b0) begin
      opcode <= 4'b0;
      lba <= 32'b0;
      block_count <= 16'b0;
      data_sample <= 64'b0;
      addrCounter <= 1'b0;
      sampleCounter <= 2'b0;
      event_valid <= 1'b0;
      timeDeltaCounter <= 16'b0;
      time_delta <= 16'b0;
      curr_state <= OPCD;
    end else begin
      case (curr_state)
        OPCD: begin
          event_valid       <= 1'b0;
          timeDeltaCounter <= timeDeltaCounter + 16'b1;
          if (data_in[15:8] == 8'b11111111) begin
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
        BLKCNT: block_count <= data_in;
        SMPL: begin
          data_sample[63 - 16 * sampleCounter -: 16] <= data_in;
          if (sampleCounter == maxSampleCount) sampleCounter <= 2'b0;
          else sampleCounter <= sampleCounter + 2'b1;
        end
        FINSH: begin
          time_delta  <= timeDeltaCounter;
          event_valid <= 1'b1;  // when finish is done, event_valid is true
        end
        default:;
      endcase
      curr_state <= next_state;
    end

endmodule
