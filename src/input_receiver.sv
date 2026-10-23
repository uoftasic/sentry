module receiver(
    input logic clk,
    input logic reset_n,
    input logic read,

    input logic [7:0] data_in,
    input logic input_valid,

    output logic [3:0] op_code,
    output logic [31:0] start_addr,
    output logic [7:0] blk_count,
    output logic [31:0] data_sample,
    output logic input_ready,
    output logic event_valid
);

    typedef enum logic [3:0] {
        IDLE, OPCD, ADDR, BLKCNT, SMPL, FINSH
    } state_t;

    state_t curr_state, next_state;

    logic [1:0] addrCounter;
    logic [2:0] sampleCounter;
    parameter maxAddrCount = 3, maxSampleCount = 7;

    always_comb begin
        case (curr_state)
            IDLE: 
                if (input_valid) next_state = OPCD;
                else next_state = IDLE;
            OPCD: next_state = ADDR;
            ADDR: 
                if(addrCounter == maxAddrCount) next_state = BLKCNT;
                else next_state = ADDR;
            BLKCNT: next_state = SMPL;
            SMPL: 
                if(sampleCounter == maxSampleCount) next_state = FINSH;
                else next_state = SMPL;
            FINSH: 
                if(read) next_state = IDLE;
                else next_state = FINSH;
            default: next_state = IDLE;
        endcase
    end

    always_ff @(posedge clk) begin
        if (reset_n == 1'b0) begin
            op_code <= 4'b0;
            start_addr <= 32'b0;
            blk_count <= 8'b0;
            data_sample <= 32'b0;
            curr_state <= IDLE;
            addrCounter <= 2'b00;
            sampleCounter <= 3'b000;
        end else begin
            curr_state <= next_state;
            addrCounter <= addrCounter + 2'b1;
            sampleCounter <= sampleCounter + 3'b001;
        end

        // counters pls dont touch  
        if(addrCounter == maxAddrCount) addrCounter <= 2'b00;
        if(sampleCounter == maxSampleCount) sampleCounter <= 3'b000;
    end

endmodule