`ifdef ENABLE_PAC
// PAC configuration -- overridable at build time with +define+PAC_*=...
// (kept as macros because core_branch is a bare-core module and may not import
//  the SoC-level `configurations` package). The key is NOT a macro: it lives in
//  a CP0 register and arrives on the `pac_key` port.
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
// Where a bad-tag JR steers fetch. Default 0x180 is in the kernel region; it can
// be overridden to an address below PAC_KERNEL_BASE with +define+PAC_HANDLER_ADDR
// (the coreTest build does this).
`ifndef PAC_HANDLER_ADDR
`define PAC_HANDLER_ADDR 64'h0000_0000_0000_0180
`endif
`endif

import structures::control_type_t;
import structures::NORMAL;
import structures::J;
import structures::JR;
import structures::ID_regs_t;
import structures::EX_regs_t;
import structures::forward_type_t;

module core_branch (
    /* verilator lint_off UNUSEDSIGNAL */
    input ID_regs_t ID_regs,
    input EX_regs_t EX_regs,
    /* verilator lint_on UNUSEDSIGNAL */
    input forward_type_t forward_A,
    input logic [63:0] MEM1_data,
    input logic [63:0] MEM_data,
    input logic [63:0] pred_npc,  // speculative next PC from branch predictor
    input logic [63:0] EPC,
    input logic takenHandler,
    input logic reset,
`ifdef ENABLE_PAC
    input logic kernel_mode,  // CP0 effective mode (KSU/EXL/ERL): 1 = kernel
    input logic [63:0] pac_key,  // secret PAC key from CP0
    // Deferred PAC gate decision, resolved here in ID but NOT acted on here: it
    // rides the pipeline to cp0/MEM, which commits it (fault for a bad tag, kernel
    // entry for a good one), or drops it if this jr is squashed. Only the fetch
    // steering (target vs handler) happens here.
    output logic pac_gate_valid,  // a user->kernel PAC cross resolved this cycle
    output logic pac_gate_ok,     // its tag authenticated (verify_ok)
    // JR resolved in ID this cycle: feed its (PAC-steered) target back to the
    // predictor so the BTB learns it and predicts it at IF1 next time.
    output logic pac_jr_train,
    output logic [63:0] pac_jr_train_target,
`endif
    output logic [63:0] next_fetch_pc  /* verilator public */,
    // 1 = this flush is a branch MISprediction. The fall-through (wrong-path)
    // instruction is then drained as speculative (no architectural commit)
    // instead of being hard-cleared.
    output logic spec_squash,
    output logic flush
);
    logic [63:0] interrupeHandlerAddr  /* verilator public */ = 64'd0;
    logic [63:0] forwarded_A;
    logic [63:0] correct_npc;
    logic is_cond_branch, actual_taken, mispredict;
`ifdef ENABLE_PAC
    logic [63:0] jr_resolved;  // JR's PAC-steered target (ID resolution)
`endif

    mux4v #(64) forward_mux_A (
        forwarded_A,
        ID_regs.A_data,
        EX_regs.out,
        MEM1_data,
        MEM_data,
        forward_A
    );

`ifdef ENABLE_PAC
    // -- PAC: authenticate cross-region (user -> kernel) indirect transfers --
    // "currently in user mode" comes from CP0's KSU bit (kernel_mode), NOT from
    // an address compare; only the *target* region is tested, once, here.
    logic        pac_tgt_kernel, pac_cross, pac_exc;
    logic [63:0] pac_va, pac_auth_ptr;

    pac_verify pac_jr_verify (
        .signed_ptr   (forwarded_A),         // jump target register (carries tag)
        .modifier     (`PAC_MODIFIER),
        .key          (pac_key),
        .check        (pac_cross),
        .auth_ptr     (pac_auth_ptr),        // tag-stripped target to actually fetch
        .verify_ok    (),                    // unused; fault is signalled via pac_exc
        .pac_exception(pac_exc)
    );

    // Kept as continuous assigns (not in the always_comb below) so the block that
    // consumes pac_exc does not also produce pac_cross -- otherwise Verilator sees
    // a false comb loop (UNOPTFLAT) through pac_jr_verify.
    // a transfer is PAC-checked iff we are in user mode (KSU) and the
    // tag-stripped target VA lands in the kernel region.
    assign pac_va         = {{`PAC_TAG_BITS{1'b0}}, forwarded_A[63-`PAC_TAG_BITS:0]};
    assign pac_tgt_kernel = (pac_va >= `PAC_KERNEL_BASE) && (pac_va < `PAC_KERNEL_END);
    assign pac_cross      = !kernel_mode && pac_tgt_kernel;
`endif

    always_comb begin
`ifdef ENABLE_PAC
        pac_gate_valid = 1'b0;  // set only by a JR cross (below)
        pac_gate_ok    = 1'b0;
        pac_jr_train   = 1'b0;  // set only when a JR resolves (below)
        pac_jr_train_target = 64'd0;
        jr_resolved    = forwarded_A;
`endif
        // -- resolve conditional branch in EX and check the prediction --
        is_cond_branch = EX_regs.BEQ || EX_regs.BNE || EX_regs.BC || EX_regs.BAL;
        actual_taken   = EX_regs.BC || EX_regs.BAL ||
                         (EX_regs.BEQ && EX_regs.zero) ||
                         (EX_regs.BNE && !EX_regs.zero);
        correct_npc    = actual_taken ? EX_regs.pc_branch : EX_regs.pc4;
        // the predictor steered fetch to EX_regs.predicted_npc; flush only if
        // that disagrees with the resolved next PC.
        mispredict     = is_cond_branch && (EX_regs.predicted_npc != correct_npc);
        spec_squash    = 1'b0;  // set only on a real misprediction (below)

        if (reset) begin
            next_fetch_pc = 64'd0;
            flush = 1'b1;
        end else if (takenHandler) begin
            next_fetch_pc = interrupeHandlerAddr;
            flush = 1'b1;
        end else if (ID_regs.ERET) begin
            next_fetch_pc = EPC;
            flush = 1'b1;
        end else if (mispredict) begin
            next_fetch_pc = correct_npc;
            flush = 1'b1;
            spec_squash = 1'b1;  // drain the wrong-path fall-through as speculative
        end else
            // jump resolve in ID stage
            /* verilator lint_off CASEINCOMPLETE */
            unique case (ID_regs.control_type)
                NORMAL: begin
                    // follow the predicted (speculative) path
                    next_fetch_pc = pred_npc;
                    flush = 1'b0;
                end
                J: begin
                    next_fetch_pc = ID_regs.jumpAddr;
                    flush = 1'b1;
                end
                JR: begin
                    // jalr and jr
`ifdef ENABLE_PAC
                    // Fetch steering (no architectural commit here): a valid cross
                    // steers to the stripped target, a bad cross to the handler.
                    // The real fault / kernel-entry is deferred to cp0/MEM via
                    // pac_gate_* (dropped if this jr is squashed).
                    jr_resolved = pac_cross ? (pac_exc ? `PAC_HANDLER_ADDR
                                                       : pac_auth_ptr)
                                            : forwarded_A;
                    // A JR is predicted at IF1 through the BTB (predicted_npc rides
                    // the pipe). Follow that prediction: continue speculatively when
                    // the PAC-steered target matches it (0 bubbles, no flush); flush
                    // and redirect only on a mispredict. A good tag matching a BTB
                    // entry trained to the target is the fast path; a bad tag steers
                    // to the handler instead => mispredict + handler-line refetch.
                    if (jr_resolved == ID_regs.predicted_npc) begin
                        next_fetch_pc = pred_npc;  // prediction held, keep fetching
                        flush = 1'b0;
                    end else begin
                        next_fetch_pc = jr_resolved;
                        flush = 1'b1;
                    end
                    // A bad-tag gated JR ALWAYS commits its fault (rate-limited): the
                    // commit must not be deferred by a BTB misprediction, or a
                    // perpetually-mispredicted (BTB-aliased) architectural JR could
                    // steer each wrong tag to the PAC handler without ever committing
                    // a fault, sidestepping the rate limiter. The gate decision is
                    // therefore resolved from the tag alone, independent of the branch
                    // prediction. A genuinely wrong-path JR (fetched behind an OLDER
                    // mispredicted branch) is still squashed by the gate flush-gating
                    // in core.sv, so this does not commit faults for instructions that
                    // never retire.
                    pac_gate_valid = pac_cross;
                    pac_gate_ok    = !pac_exc;
                    pac_jr_train        = 1'b1;
                    pac_jr_train_target = jr_resolved;
`else
                    next_fetch_pc = forwarded_A;
                    flush = 1'b1;
`endif
                end
            endcase
        /* verilator lint_on CASEINCOMPLETE */
    end
endmodule
