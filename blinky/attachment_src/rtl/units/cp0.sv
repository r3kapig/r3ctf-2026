module cp0 #(
    parameter [4:0] STATUS_REGISTER = 5'd12,
    parameter [4:0] CAUSE_REGISTER = 5'd13,
    parameter [4:0] EPC_REGISTER    = 5'd14,
    parameter [4:0] BAD_INSTR_REGISTER = 5'd8
) (
    output logic [63:0] rd_data,
    output logic [63:0] EPC,
    output logic        takenHandler,
`ifdef ENABLE_PAC
    output logic        kernel_mode  /* verilator public */,  // effective mode: 1 = kernel (KSU/EXL/ERL)
    output logic [63:0] pac_key,      // secret PAC key: kernel-writable, user cannot read
`endif
    input  logic [63:0] wr_data,
    input  logic [ 4:0] regnum,
    input  logic [ 2:0] sel,
    input  logic [63:0] IF_pc,
    input  logic [63:0] curr_pc,
    input  logic        MTC0,
    input  logic        ERET,
    input  logic [ 7:0] interrupt_source,
    input  logic        clock,
    input  logic        reset,
    input  logic        overflow,
    input  logic        reserved_inst,
    input  logic        break_,
    input  logic        spec,  // MEM-stage instr is a wrong-path speculative drain
`ifdef ENABLE_PAC
    input  logic        pac_fail,  // deferred I-cache PAC fault (direct kernel fetch)
    input  logic        pac_ld_fail,  // deferred PAC-gated-load fault (bad tag)
    input  logic        pac_gate_valid,  // deferred JR PAC gate reached MEM (commit now)
    input  logic        pac_gate_ok,     // its tag authenticated
`endif
    input  logic        syscall
);
    logic [4:0] exc_code  /* verilator public */, next_exc_code;
    /* verilator lint_off UNUSEDSIGNAL */
    logic [31:0] user_status  /* verilator public */;  // Status; KSU = [4:3]
    /* verilator lint_on UNUSEDSIGNAL */
    logic [31:0] badinstr_D, cause_reg, status_reg;
    logic [63:0] EPC_D;
    logic exception_level, takenInterrupt, takenException;

`ifdef ENABLE_PAC
    // Custom CP0 register 22 (sel 0) holds the PAC key. MIPS reserves register 22
    // for implementation-defined use, so it does not clash with any real CP0 reg.
    localparam [4:0] PAC_KEY_REGISTER = 5'd22;
    // -- true kernel privilege ----------------------------------------------
    // The predicate the PAC guard and key access trust. It is raised ONLY by
    // genuine kernel execution:
    //   * boot: set at reset, held until the boot code ERETs to user;
    //   * user->kernel entry ONLY via an authenticated PAC gate (pac_gate_ok).
    // It is NOT derived from Status.KSU/EXL (both are reachable from user mode:
    // KSU via MTC0 $12, EXL via any exception, which vectors to the user-owned
    // 0x00 handler). Cleared by ERET (drop back to user).
    logic true_kernel  /* verilator public */;

    // -- PAC fault rate limiter --
    // Count *committed* PAC faults (exc 0x10) only; a squashed/speculative
    // instruction never reaches here so it never counts. After PAC_FAULT_LIMIT
    // committed faults the core is permanently `pac_locked`: the authenticated
    // gate can no longer raise privilege, so even the correct tag can no longer
    // enter the kernel. The count is per power-on (only reset clears it).
    // Default 1: a SINGLE committed bad-tag fault locks the core, so a naive
    // architectural brute force gets exactly one guess per power-on/submission
    // (combined with the per-run random PAC key this makes cross-submission
    // brute force infeasible).
`ifndef PAC_FAULT_LIMIT
`define PAC_FAULT_LIMIT 16'd1
`endif
    logic [15:0] pac_fault_count  /* verilator public */;
    logic        pac_locked       /* verilator public */;
    logic        committed_pac_fault;
    assign pac_locked = (pac_fault_count >= `PAC_FAULT_LIMIT);
`endif

    // TODO reset BEV, ERL should be 1
    // but can't rlly set BEV to 1, because I don't use boot vector yet.
    // when reset:
    // - enable all exception interrupts
    // - enable IE
    register #(32, 32'b0000_0000_0000_0000_1111_1111_0000_0001) user_status_reg (
        user_status,
        wr_data[31:0],
        clock,
        MTC0 && (regnum == STATUS_REGISTER) && (sel == 0),
        reset
    );

    register #(32) badinstr_reg (
        badinstr_D,
        wr_data[31:0],
        clock,
        takenException,
        ERET || reset
    );

    register #(1) exception_lv_reg (
        exception_level,
        takenHandler ? 1'b1 : wr_data[1],
        clock,
        takenHandler || ((MTC0 && regnum == STATUS_REGISTER) && (sel == 0)),
        ERET || reset
    );

    mux3v #(64) data_pc_mux (
        EPC_D,
        wr_data,
        curr_pc,  // exception just return to ID
        IF_pc,  // interrupt need to return to next instruction(bc it will not shut the pipeline)
        {takenInterrupt, takenException}
    );
    register #(64) EPC_reg (
        EPC,
        EPC_D,
        clock,
        (MTC0 && (regnum == EPC_REGISTER) & (sel == 0)) || takenHandler,
        reset
    );

`ifdef ENABLE_PAC
    // Provisioned at reset with the default key; the kernel may rotate it via
    // (D)MTC0. The write is mode-gated so user code cannot install its own key
    // (and the read path below returns 0 outside kernel mode).
    register #(64, 64'h0123_4567_89ab_cdef) pac_key_reg (
        pac_key,
        wr_data,
        clock,
        MTC0 && (regnum == PAC_KEY_REGISTER) && (sel == 3'b0) && kernel_mode,
        reset
    );

    // A good deferred gate (reached MEM un-squashed) commits the kernel entry;
    // ERET drops back to user; reset boots in kernel. Once locked (pac_locked)
    // no gate can raise privilege. Ordering: reset > ERET > gate-raise (they do
    // not collide in practice).
    always_ff @(posedge clock, posedge reset) begin
        if (reset)                                             true_kernel <= 1'b1;
        else if (ERET)                                         true_kernel <= 1'b0;
        else if (pac_gate_valid && pac_gate_ok && !pac_locked) true_kernel <= 1'b1;
    end
`endif

    always_comb begin
        cause_reg = {
            16'b0,
            interrupt_source,  // 7 outside interrupt sources
            1'b0,
            exc_code,  // ExcCode
            2'b0
        };
        status_reg = {
            user_status[31:3],
            user_status[2],  // ERL
            exception_level,  // EXL
            user_status[0]  // IE
        };

`ifdef ENABLE_PAC
        // The PAC-guard / key-access privilege is EXACTLY `true_kernel`, NOT the
        // raw Status.KSU/EXL/ERL bits (those are reachable from user mode).
        // `true_kernel` is raised only at reset or by an authenticated PAC gate.
        kernel_mode = true_kernel;
`endif

        unique case ({
            regnum, sel
        })
            {STATUS_REGISTER, 3'b0}: rd_data = {32'b0, status_reg};
            {CAUSE_REGISTER, 3'b0}:  rd_data = {32'b0, cause_reg};
            {EPC_REGISTER, 3'b0}:    rd_data = EPC;
            {BAD_INSTR_REGISTER, 3'b1}: rd_data = {32'b0, badinstr_D};
`ifdef ENABLE_PAC
            // user code cannot read the key back; kernel may (e.g. to save it)
            {PAC_KEY_REGISTER, 3'b0}: rd_data = kernel_mode ? pac_key : 64'b0;
`endif
            default: rd_data = 'x;
        endcase
        case (1'b1)
            overflow:      next_exc_code = 5'h0c;
            reserved_inst: next_exc_code = 5'h0a;
            syscall:       next_exc_code = 5'h08;
            break_:        next_exc_code = 5'h09;
`ifdef ENABLE_PAC
            // A direct kernel-region fetch faults only while still in user mode.
            // A *valid* JR gate commits kernel mode one cycle before its target's
            // I-cache fault reaches here, so by now kernel_mode==1 and the target
            // is let through -- that is how a good tag enters the kernel cleanly.
            (pac_fail && !kernel_mode):
                           next_exc_code = 5'h10;
            (pac_gate_valid && !pac_gate_ok):
                           next_exc_code = 5'h10;  // bad-tag JR gate, committed at MEM
            pac_ld_fail:   next_exc_code = 5'h10;  // bad-tag PAC-gated load (any mode)
`endif
            default:       next_exc_code = 5'h00;
        endcase

        // A wrong-path speculative (drained) instruction commits no synchronous
        // exception: the speculative flag (EX_regs.spec) gates the commit point, so a
        // squashed instruction's fault never reaches here. This is a generic
        // pipeline property and applies to every exception, not just the PAC-gated
        // load. Interrupts are asynchronous and are NOT gated here.
        takenException = (|next_exc_code) && !spec;  // ExcCode != 0 and not squashed
        takenInterrupt = ((|(cause_reg[15:8] & status_reg[15:8])) && // if enabled interrupt sources
        (!(|exc_code)) &&  // ExcCode = 0
        (status_reg[0]) &&  // IE = 1
        (!status_reg[2]));  // ERL = 0
        takenHandler = (takenInterrupt || takenException) && (!status_reg[1]);  // EXL = 0
`ifdef ENABLE_PAC
        // a PAC fault that actually commits to the handler this cycle
        committed_pac_fault = takenHandler && (next_exc_code == 5'h10);
`endif
    end

    always_ff @(posedge clock, posedge reset) begin
`ifdef DEBUG
        if (regnum == BAD_INSTR_REGISTER) $display("CP0: readBadInstr = %h", rd_data);
        if (regnum == CAUSE_REGISTER && sel == 0) $display("CP0: readCause = %h", rd_data);
        if (regnum == STATUS_REGISTER && sel == 0) $display("CP0: readStatus = %h", rd_data);
        if (break_) $display("CP0: break, EPC = %h", EPC);
        if (syscall) $display("CP0: syscall, EPC = %h", EPC);
        if (takenHandler)
            $display(
                "CP0: taken handler, ExcCode = %h, EPC wr = %h B_data = %h, return pc = %h",
                next_exc_code,
                EPC_D,
                wr_data,
                curr_pc
            );
        if (ERET) $display("CP0: ERET, EPC = %h", EPC);
        if (MTC0) $display("CP0: MTC0, regnum = %d(sel=%d), data = %h", regnum, sel, wr_data);
`endif
        if (reset) begin
            exc_code <= 5'h00;
        end else begin
            if (takenHandler) exc_code <= next_exc_code;
            else if (ERET) exc_code <= '0;
        end
`ifdef ENABLE_PAC
        // Accumulate committed PAC faults across the whole run (only reset clears
        // it -- ERET does not). Saturate once locked.
        if (reset) pac_fault_count <= 16'd0;
        else if (committed_pac_fault && !pac_locked)
            pac_fault_count <= pac_fault_count + 16'd1;
`endif
    end

endmodule
