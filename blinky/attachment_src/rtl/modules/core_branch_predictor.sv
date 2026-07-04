// core_branch_predictor: a simple in-order dynamic branch predictor.
//
// It is a "bimodal" predictor: a Branch History Table (BHT) of 2-bit
// saturating counters gives the predicted direction, and a tagged, direct
// mapped Branch Target Buffer (BTB) gives the predicted target. Both are
// looked up in the first fetch sub-stage (IF1) using the fetch PC, so a
// correctly predicted taken branch costs 0 bubbles instead of the 2 bubbles
// a taken branch costs under the static predict-not-taken scheme.
//
// Correctness does NOT depend on this module: the real direction/target is
// still resolved in EX (for conditional branches) by core_branch, which
// compares the resolved next-PC against the speculative next-PC carried down
// the pipeline (`predicted_npc`) and flushes on a misprediction. This module
// only affects performance.
//
// Only conditional branches (BEQ/BNE/BC/BAL) are tracked here; unconditional
// jumps (J/JR) keep being resolved in ID by core_branch, so they are never
// installed in the BTB and never conflict with a prediction.

import structures::EX_regs_t;

module core_branch_predictor #(
    parameter IDX_BITS = 6,  // 2^IDX_BITS entries for both BHT and BTB
    parameter TAG_BITS = 16  // partial tag for the BTB (only perf if aliased)
) (
    input logic clock,
    input logic reset,

    // -- predict (IF1 stage) --
    input logic [63:0] pc,  // IF1.fetch_pc, address being looked up
    input logic [63:0] pc4,  // IF1.fetch_pc + 4, sequential fall-through
    output logic [63:0] pred_npc,  // predicted next fetch PC

    // -- update (EX stage resolution) --
    /* verilator lint_off UNUSEDSIGNAL */
    input EX_regs_t EX_regs
    /* verilator lint_on UNUSEDSIGNAL */
`ifdef ENABLE_PAC
    // -- JR training (ID stage resolution from core_branch) --
    // JR/JALR resolve in ID, one stage earlier than the conditional branches
    // trained above, so they are trained through this separate port instead of
    // EX_regs. Installing a JR target lets it be predicted at IF1: a correctly
    // predicted JR then costs 0 bubbles, and a JR whose PAC-resolved target
    // disagrees with the prediction mispredicts.
    ,
    input logic        jr_train,         // a JR resolved in ID this cycle
    input logic [63:0] jr_train_pc,      // its own PC (ID_regs.pc)
    input logic [63:0] jr_train_target   // its resolved (PAC-steered) target
`endif
);
    localparam ENTRIES = 1 << IDX_BITS;

    // direction predictor: 2-bit saturating counters (00/01 -> not taken,
    // 10/11 -> taken)
    logic [         1:0] bht       [ENTRIES];
    // branch target buffer
    logic                btb_valid [ENTRIES];
    logic [TAG_BITS-1:0] btb_tag   [ENTRIES];
    logic [        63:0] btb_target[ENTRIES];

    // ---- predict ----
    logic [IDX_BITS-1:0] rd_idx;
    logic [TAG_BITS-1:0] rd_tag;
    logic btb_hit, predict_taken;

    // ---- update ----
    logic [63:0] br_pc;
    logic [IDX_BITS-1:0] wr_idx;
    logic [TAG_BITS-1:0] wr_tag;
    logic is_cond_branch, actual_taken;
`ifdef ENABLE_PAC
    logic [IDX_BITS-1:0] jr_wr_idx;
    logic [TAG_BITS-1:0] jr_wr_tag;
`endif

    always_comb begin
        rd_idx = pc[IDX_BITS+1:2];  // skip 2 LSBs (4-byte aligned)
        rd_tag = pc[IDX_BITS+1+TAG_BITS:IDX_BITS+2];
        btb_hit = btb_valid[rd_idx] && (btb_tag[rd_idx] == rd_tag);
        predict_taken = btb_hit && bht[rd_idx][1];
        pred_npc = predict_taken ? btb_target[rd_idx] : pc4;

        br_pc = EX_regs.pc4 - 64'd4;  // branch's own PC
        wr_idx = br_pc[IDX_BITS+1:2];
        wr_tag = br_pc[IDX_BITS+1+TAG_BITS:IDX_BITS+2];
        is_cond_branch = EX_regs.BEQ || EX_regs.BNE || EX_regs.BC || EX_regs.BAL;
        actual_taken   = EX_regs.BC || EX_regs.BAL ||
                         (EX_regs.BEQ && EX_regs.zero) ||
                         (EX_regs.BNE && !EX_regs.zero);
`ifdef ENABLE_PAC
        jr_wr_idx = jr_train_pc[IDX_BITS+1:2];
        jr_wr_tag = jr_train_pc[IDX_BITS+1+TAG_BITS:IDX_BITS+2];
`endif
    end

    integer i;
    always_ff @(posedge clock, posedge reset) begin
        if (reset) begin
            for (i = 0; i < ENTRIES; i = i + 1) begin
                bht[i]       <= 2'b01;  // weakly not-taken
                btb_valid[i] <= 1'b0;
            end
        end else if (is_cond_branch) begin
            // 2-bit saturating counter
            if (actual_taken) begin
                if (bht[wr_idx] != 2'b11) bht[wr_idx] <= bht[wr_idx] + 2'b01;
            end else begin
                if (bht[wr_idx] != 2'b00) bht[wr_idx] <= bht[wr_idx] - 2'b01;
            end
            // (re)allocate the BTB entry on a taken branch
            if (actual_taken) begin
                btb_valid[wr_idx]  <= 1'b1;
                btb_tag[wr_idx]    <= wr_tag;
                btb_target[wr_idx] <= EX_regs.pc_branch;
            end
        end
`ifdef ENABLE_PAC
        // Train a JR entry. A JR is unconditional, so its direction is always
        // "taken": force the counter to strong-taken so the entry predicts its
        // target on the next lookup. (Written after the conditional-branch block
        // so a rare same-index collision resolves in the JR's favour.)
        if (jr_train) begin
            bht[jr_wr_idx]        <= 2'b11;
            btb_valid[jr_wr_idx]  <= 1'b1;
            btb_tag[jr_wr_idx]    <= jr_wr_tag;
            btb_target[jr_wr_idx] <= jr_train_target;
        end
`endif
    end
endmodule
