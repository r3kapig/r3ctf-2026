import structures::IF_regs_t;
import structures::mem_bus_req_t;
import structures::mem_bus_resp_t;
import structures::LOAD_WORD;
import structures::NO_STORE;
import structures::cache_action_t;
import structures::ICACHE;

`ifdef ENABLE_PAC
// PAC config -- mirror of core_branch.sv. ifndef-guarded so whichever bare-core
// file is compiled first defines them and the rest are no-ops. The key is not a
// macro: it lives in a CP0 register and arrives on the `pac_key` port.
`ifndef PAC_MODIFIER
`define PAC_MODIFIER 64'd0
`endif
`ifndef PAC_KERNEL_BASE
`define PAC_KERNEL_BASE 64'h0000_0000_0000_0100
`endif
`ifndef PAC_KERNEL_END
`define PAC_KERNEL_END 64'h0000_0000_0010_0000
`endif
`ifndef PAC_TAG_BITS
`define PAC_TAG_BITS 16
`endif
`endif

module core_IF #(
    // The core boots (in kernel mode) at the kernel base, so RESET_PC tracks
    // PAC_KERNEL_BASE when PAC is enabled (the user region sits below it).
`ifdef ENABLE_PAC
    parameter RESET_PC = `PAC_KERNEL_BASE
`else
    parameter RESET_PC = 64'h100
`endif
) (
    input logic clock,
    input logic reset,
    input logic [63:0] next_fetch_pc,
    input logic [63:0] pred_npc,  // predicted next PC for the inst now in IF1
    input logic stall,
    input logic flush,
    input logic EX_cache_inst,
    input cache_action_t EX_cache_action,
`ifdef ENABLE_PAC
    input logic kernel_mode,  // CP0 effective mode (KSU/EXL/ERL): 1 = kernel
    input logic [63:0] pac_key,  // secret PAC key from CP0
`endif

    output logic [63:0] first_half_pc  /* verilator public */,
    output logic [63:0] first_half_pc4  /* verilator public */,
    output IF_regs_t IF_regs,

    // -- mem bus --
    output mem_bus_req_t  inst_req,
    input  mem_bus_resp_t inst_resp
);
    typedef struct packed {logic [63:0] fetch_pc4, fetch_pc;} IF1_t;

    IF1_t IF1;
    logic [63:0] inst_L1;
    logic [63:0] if_fetch_pc, if_fetch_pc4, if_predicted_npc;
    logic inst_cache_miss, inst_cache_miss_stall  /* verilator public */;
    logic if1_pac_exc;  // PAC auth failed for the address now in IF1
    logic if_pac_fail;  // registered, travels in IF_regs alongside if_fetch_pc

    cache_L1 inst_cache (
        .clock(clock),
        .reset(reset),
        .enable(!stall),
        .clear(flush),
        .signed_type(1'b0),
        .addr(IF1.fetch_pc),
        .wdata('x),
        .mem_load_type(LOAD_WORD),
        .mem_store_type(NO_STORE),
        .rdata(inst_L1),
        .miss(inst_cache_miss),
        .cache_inst(EX_cache_inst && (EX_cache_action.t == ICACHE)),
        .cache_op(EX_cache_action.op),
        .req(inst_req),
        .resp(inst_resp)
    );

`ifdef ENABLE_PAC
    // -- I-cache PAC: authenticate user->kernel instruction fetches --
    // Same cross-region policy as the JR check in core_branch: fire only when we
    // are in user mode (kernel_mode == 0) and the tag-stripped fetch target lands
    // in the kernel region. The fault is NOT acted on here -- the fetch proceeds;
    // the failure rides the pipeline as IF_regs.pac_fail and is committed (or
    // squashed by a misprediction flush) in MEM/cp0.
    logic        if_pac_tgt_kernel, if_pac_cross;
    logic [63:0] if_pac_va;

    assign if_pac_va         = {{`PAC_TAG_BITS{1'b0}}, IF1.fetch_pc[63-`PAC_TAG_BITS:0]};
    assign if_pac_tgt_kernel = (if_pac_va >= `PAC_KERNEL_BASE)
                            && (if_pac_va <  `PAC_KERNEL_END);
    assign if_pac_cross      = !kernel_mode && if_pac_tgt_kernel;

    pac_verify pac_if_verify (
        .signed_ptr   (IF1.fetch_pc),  // fetch target register carries the tag
        .modifier     (`PAC_MODIFIER),
        .key          (pac_key),
        .check        (if_pac_cross),
        .auth_ptr     (),                // tag stripping is handled in core_branch
        .verify_ok    (),
        .pac_exception(if1_pac_exc)
    );
`else
    assign if1_pac_exc = 1'b0;
`endif

    always_comb begin
        first_half_pc = IF1.fetch_pc;
        first_half_pc4 = IF1.fetch_pc4;
        IF_regs.fetch_pc4 = if_fetch_pc4;
        IF_regs.fetch_pc = if_fetch_pc;
        IF_regs.predicted_npc = if_predicted_npc;
        IF_regs.pac_fail = if_pac_fail;
        IF_regs.inst = inst_L1[31:0];
        inst_cache_miss_stall = inst_cache_miss && !inst_resp.mem_ready;
    end

    always_ff @(posedge clock, posedge reset) begin
        // $display("t=%0t, inst_cache_miss_stall = %d", $time,
        //          inst_cache_miss_stall);
        if (reset) begin
            IF1.fetch_pc  <= RESET_PC;
            IF1.fetch_pc4 <= RESET_PC;
            if_fetch_pc   <= '0;
            if_fetch_pc4  <= '0;
            if_predicted_npc <= '0;
            if_pac_fail   <= 1'b0;
        end else if (!(stall || inst_cache_miss_stall) || flush) begin
            IF1.fetch_pc  <= next_fetch_pc;
            IF1.fetch_pc4 <= next_fetch_pc + 4;

            if (flush) begin
                if_fetch_pc  <= '0;
                if_fetch_pc4 <= '0;
                if_predicted_npc <= '0;
                if_pac_fail  <= 1'b0;
            end else begin
                if_fetch_pc  <= IF1.fetch_pc;
                if_fetch_pc4 <= IF1.fetch_pc4;
                // prediction made for the inst moving IF1 -> IF this cycle
                if_predicted_npc <= pred_npc;
                // PAC result computed for the same address (IF1.fetch_pc)
                if_pac_fail  <= if1_pac_exc;
            end
        end
    end
endmodule
