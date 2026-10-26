module receiver (
    input logic clk,
    input logic reset_n,
    input logic read,

    input logic [7:0] data_in,
    input logic data_valid,

    output logic data_ready,
    output logic event_valid,
    output logic [3:0] opcode,
    output logic [31:0] lba,
    output logic [7:0] block_count,
    output logic [15:0] time_delta,
    output logic [63:0] data_sample,
    output logic data_sample_valid
);

  typedef enum logic [3:0] {
    OPCD,
    ADDR,
    BLKCNT,
    SMPL,
    FINSH
  } state_t;

  state_t curr_state, next_state;

  logic [ 1:0] addrCounter;
  logic [ 2:0] sampleCounter;
  logic [15:0] timeDeltaCounter;
  localparam bit [1:0] maxAddrCount = 2'b11;
  localparam bit [2:0] maxSampleCount = 3'b111;

  always_comb
    case (curr_state)
      OPCD: next_state = data_valid ? ADDR : OPCD;  // opcodes read, prepare to read addresses
      ADDR:
      if (addrCounter == maxAddrCount)
        next_state = BLKCNT;  // addresses read, prepare to read block counts
      else next_state = ADDR;
      BLKCNT: next_state = SMPL;  // block counts read, prepare to read sample
      SMPL:
      if (sampleCounter == maxSampleCount) next_state = FINSH;  // sample read, finishing
      else next_state = SMPL;
      FINSH:
      if (read) next_state = OPCD;  // all done, go back to idle
      else next_state = FINSH;
      default: next_state = OPCD;
    endcase

  always_ff @(posedge clk)
    if (reset_n == 1'b0) begin
      opcode <= 4'b0;
      lba <= 32'b0;
      block_count <= 8'b0;
      data_sample <= 64'b0;
      curr_state <= OPCD;
      addrCounter <= 2'b0;
      sampleCounter <= 3'b0;
      data_ready <= 1'b0;
      event_valid <= 1'b0;
      data_sample_valid <= 1'b0;
      timeDeltaCounter <= 16'b0;
      time_delta <= 16'b0;
    end else begin
      case (curr_state)
        OPCD: begin
          data_ready        <= 1'b0;
          event_valid       <= 1'b0;
          data_sample_valid <= 1'b0;
          if (data_valid) opcode <= data_in[3:0];
        end
        ADDR: begin
          lba[31 - 8 * addrCounter -: 8] <= data_in;
          if (addrCounter == maxAddrCount) begin // when all addresses are ready, data_ready is true
            data_ready  <= 1'b1;
            addrCounter <= 2'b0;
          end else addrCounter <= addrCounter + 2'b1;
        end
        BLKCNT:  block_count <= data_in;
        SMPL: begin
          data_sample[63 - 8 * sampleCounter -: 8] <= data_in;
          if (sampleCounter == maxSampleCount) begin // when all sample data are ready, data_sample_valid is true
            data_sample_valid <= 1'b1;
            sampleCounter <= 3'b0;
          end else sampleCounter <= sampleCounter + 3'b1;
        end
        FINSH: begin
          time_delta  <= timeDeltaCounter;
          event_valid <= 1'b1;  // when finish is done, event_valid is true
        end
        default:;
      endcase
      if (curr_state == OPCD) timeDeltaCounter <= 16'b0;
      else if (curr_state != FINSH) timeDeltaCounter <= timeDeltaCounter + 16'b1;
      curr_state <= next_state;
    end

endmodule
