module receiver(
    input logic clk,
    input logic reset_n,

    input logic [7:0] data_in,
    input logic input_valid,

    output logic [3:0] op_code,
    output logic [31:0] start_addr,
    output logic [7:0] blk_count,
    output logic [31:0] data_sample,
    output logic input_ready,
    output logic event_valid,
);

    typedef enum logic [3:0] {
        IDLE, OPCD, STRTLBA1, STRTLBA2, STRTLBA3, STRTLBA4, BLKCNT,
        DTA1, DTA2, DTA3, DTA4
    } state_t;

    state_t curr_state, next_state;

    always_ff @( clk ) begin
        if (reset_n == 1'b0) begin
            op_code <= 4'b0;
            start_addr <= 32'b0;
            blk_count <= 8'b0;
            data_sample <= 32'b0;
            curr_state <= IDLE;
        end
        else begin
            curr_state <= next_state;
        end
    end

    

endmodule