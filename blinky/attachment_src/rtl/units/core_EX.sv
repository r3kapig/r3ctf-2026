import structures::ID_regs_t;
import structures::EX_regs_t;
import structures::forward_type_t;
import structures::mem_load_type_t;
import structures::NO_LOAD;
import structures::mem_store_type_t;
import structures::NO_STORE;

`ifdef ENABLE_PAC
// Kernel-region bounds for the data-side guard -- mirror of core_branch/core_IF,
// so whichever bare-core file is compiled first defines them and the rest are
// no-ops.
`ifndef PAC_KERNEL_BASE
`define PAC_KERNEL_BASE 64'h0000_0000_0000_0100
`endif
`ifndef PAC_KERNEL_END
`define PAC_KERNEL_END 64'h0000_0000_0010_0000
`endif
`ifndef PAC_MODIFIER
`define PAC_MODIFIER 64'd0
`endif
// Tag width (pointer bits [63:64-TAG_BITS]); VA is the low 64-TAG_BITS bits.
`ifndef PAC_TAG_BITS
`define PAC_TAG_BITS 16
`endif
// USER-region line a PAC-gated load targets on a good tag. It sits below
// PAC_KERNEL_BASE, so a gated load never dereferences the (kernel) VA it
// authenticates.
`ifndef PAC_PROBE_ADDR
`define PAC_PROBE_ADDR 64'h0000_0000_0000_1000
`endif
`endif

module core_EX (
    input logic clock,
    input logic reset,
    input logic data_cache_miss_stall,
    /* verilator lint_off UNUSEDSIGNAL */
    input ID_regs_t ID_regs,
    /* verilator lint_on UNUSEDSIGNAL */
    input logic flush,
    input logic [63:0] MEM_data,
    input logic [63:0] MEM1_data,
    // -- forward --
    input forward_type_t forward_A,
    input forward_type_t forward_B,
    input logic takenHandler,
    input logic spec_squash,   // this flush is a misprediction -> drain, don't clear
`ifdef ENABLE_PAC
    input logic kernel_mode,       // CP0 effective mode (KSU/EXL/ERL): 1 = kernel
    input logic [63:0] pac_key,    // secret PAC key from CP0
`endif
    output EX_regs_t EX_regs
);
    logic negative, overflow, zero, borrow_out;
    logic [ 4:0] barrel_sa;
    logic [31:0] rotator32_tmp_out;
    logic [63:0]
        B_in_barrel,
        A_in_barrel,
        barrel_in,
        ext_out,
        alu_tmp_out,
        alu_out,
        lui_val,
        slt_calc,
        borrow_val,
        shifter_tmp_out,
        shifter_small_tmp_out,
        rotator_tmp_out,
        rotator_len_out,
        barrel_out,
        barrel_plus32_out,
        forwarded_A,
        forwarded_B,
        SignExtImm,
        ZeroExtImm,
        CacheExtImm,
        SEH_out,
        SEB_out;

    mux4v #(64) forward_mux_A (
        forwarded_A,
        ID_regs.A_data,
        EX_regs.out,
        MEM1_data,
        MEM_data,
        forward_A
    );

    mux4v #(64) forward_mux_B (
        forwarded_B,
        ID_regs.B_data,
        EX_regs.out,
        MEM1_data,
        MEM_data,
        forward_B
    );

    mux8v #(64) B_in_barrel_mux (
        B_in_barrel,
        forwarded_B,
        'x,
        SignExtImm,
        ZeroExtImm,
        CacheExtImm,
        'x,
        'x,
        'x,
        ID_regs.alu_b_src
    );

    mux3v #(64) A_in_barrel_mux (
        A_in_barrel,
        forwarded_A,
        shifter_small_tmp_out,
        ID_regs.pc,
        ID_regs.alu_a_src
    );

    mux2v #(64) barrel_in_mux (
        barrel_in,
        forwarded_B,
        forwarded_A,
        ID_regs.barrel_src
    );

    mux2v #(5) barrel_sa_mux (
        barrel_sa,
        ID_regs.shamt,
        forwarded_A[4:0],
        ID_regs.barrel_sa_src
    );

    // -- ALU --
    alu #(64) alu_ (
        .out(alu_tmp_out),
        .overflow(overflow),
        .zero(),
        .negative(negative),
        .borrow_out(borrow_out),
        .a(A_in_barrel),
        .b(B_in_barrel),
        .alu_op(ID_regs.alu_op)
    );
    mux3v #(64) cut_alu_out (
        alu_out,
        alu_tmp_out,
        {{32{alu_tmp_out[31]}}, alu_tmp_out[31:0]},
        {32'b0, alu_tmp_out[31:0]},
        ID_regs.cut_alu_out32
    );

    // -- barrel --
    barrel_shifter32 #(64) shifter (
        shifter_tmp_out,
        barrel_in,
        barrel_sa,
        ID_regs.barrel_right,
        ID_regs.shift_arith
    );
    barrel_shifter_left_small #(64) shifter_small (
        shifter_small_tmp_out,
        barrel_in,
        barrel_sa[2:0]
    );
    barrel_rotator32 #(64) rotator (
        rotator_tmp_out,
        barrel_in,
        barrel_sa,
        ID_regs.barrel_right
    );
    barrel_rotator32 #(32) rotator32 (
        rotator32_tmp_out,
        barrel_in[31:0],
        barrel_sa,
        ID_regs.barrel_right
    );
    mux2v #(64) rotator_len_mux (
        rotator_len_out,
        rotator_tmp_out,
        {32'b0, rotator32_tmp_out},
        ID_regs.rotator_src
    );
    mux4v #(64) cut_barrel_out (
        barrel_out,
        shifter_tmp_out,
        rotator_tmp_out,
        {{32{shifter_tmp_out[31]}}, shifter_tmp_out[31:0]},
        {{32{rotator_len_out[31]}}, rotator_len_out[31:0]},
        ID_regs.cut_barrel_out32
    );
    mux4v #(64) barrel_plus32_mux (
        barrel_plus32_out,
        barrel_out,
        {barrel_out[31:0], {32{1'b0}}},
        {{32{1'b0}}, barrel_out[63:32]},
        {barrel_out[31:0], barrel_out[63:32]},
        ID_regs.barrel_plus32
    );

    // Flatten the former alu_barrel -> lui -> slt -> ext mux cascade (4 serial
    // muxes, ~7 LUT levels on the 64-bit datapath) into one parallel mux. The
    // select ex_out_src is fully resolved in the decoder and matches the input
    // order below; the data now passes through a single mux level.
    mux8v #(64) out_sel (
        ext_out,
        alu_out,  // ALU_OUT
        barrel_plus32_out,  // SHIFTER_OUT
        ID_regs.pc_branch,  // PC_BRANCH
        lui_val,  // LUI_OUT
        slt_calc,  // SLT_OUT
        borrow_val,  // SLTU_OUT
        SEB_out,  // SEB_OUT
        SEH_out,  // SEH_OUT
        ID_regs.ex_out_src
    );

    always_comb begin
        SignExtImm = {{48{ID_regs.inst[15]}}, ID_regs.inst[15:0]};
        ZeroExtImm = {{48{1'b0}}, ID_regs.inst[15:0]};
        CacheExtImm = {{55{ID_regs.inst[15]}}, ID_regs.inst[15:7]};
        SEH_out = {{48{ID_regs.B_data[15]}}, ID_regs.B_data[15:0]};
        SEB_out = {{56{ID_regs.B_data[7]}}, ID_regs.B_data[7:0]};
        // bypass alu for timing constrain
        // also in MIPS64, nearly only branching or similar semantics
        // using zero signal, transform to equivalently with a equal b
        zero = A_in_barrel == B_in_barrel;

        // output value candidates selected by ex_out_src (see out_sel above)
        lui_val = {{32{ID_regs.inst[15]}}, ID_regs.inst[15:0], 16'b0};
        // if different sign, check if A < 0, else check negative flag from alu
        slt_calc = {
            63'b0,
            ((forwarded_A[63] ^ forwarded_B[63]) & forwarded_A[63]) | (~(forwarded_A[63] ^ forwarded_B[63]) & negative)
        };
        borrow_val = {63'b0, borrow_out};
    end

`ifdef ENABLE_PAC
    // -- PAC-gated data load ------------------------------------------------
    // A load whose address register carries a non-zero PAC tag in bits
    // [63:64-TAG_BITS] is authenticated against pac_key (PRF over the stripped
    // VA); it never dereferences the authenticated (kernel) VA.
    //   * good tag -> load proceeds to the USER line PAC_PROBE_ADDR; no fault.
    //   * bad tag  -> NO_LOAD (no cache access) + a deferred PAC fault (cp0 exc
    //     0x10), which the commit stage drops if the load is drained as
    //     speculative (drain_load).
    logic          pac_ld_gated, pac_ld_ok, pac_ld_fault;
    logic [63:0]   pac_ld_auth, pac_ld_addr;

    pac_verify pac_ld_verify (
        .signed_ptr   (ext_out),               // load address register (carries tag)
        .modifier     (`PAC_MODIFIER),
        .key          (pac_key),
        .check        (pac_ld_gated),
        .auth_ptr     (pac_ld_auth),           // {tag'b0, ext_out VA} (unused)
        .verify_ok    (pac_ld_ok),
        .pac_exception()                        // fault handled via pac_ld_fault below
    );
    assign pac_ld_gated = (|ID_regs.mem_load_type) && (|ext_out[63:64-`PAC_TAG_BITS]);
    // A good-tag gated load targets the USER line PAC_PROBE_ADDR; a non-gated
    // load keeps its canonical address.
    assign pac_ld_addr  = (pac_ld_gated && pac_ld_ok) ? `PAC_PROBE_ADDR : ext_out;
    assign pac_ld_fault = pac_ld_gated && !pac_ld_ok;

    // -- Kernel-region data guard (non-gated accesses) ---------------------
    // With no MMU, this region+mode check forbids a USER-mode load/store into
    // [PAC_KERNEL_BASE, PAC_KERNEL_END) with an untagged pointer -- except a
    // gated load, handled above. Suppressed (NO_LOAD/NO_STORE) + deferred fault.
    // VA compared tag-agnostically.
    logic [63:0] kmem_va;
    logic        kmem_addr, kmem_violation;
    assign kmem_va        = {{`PAC_TAG_BITS{1'b0}}, ext_out[63-`PAC_TAG_BITS:0]};   // tag-agnostic canonical VA
    assign kmem_addr      = (kmem_va >= `PAC_KERNEL_BASE)
                         && (kmem_va <  `PAC_KERNEL_END);
    assign kmem_violation = !kernel_mode && kmem_addr && !pac_ld_gated
                         && (|ID_regs.mem_load_type || |ID_regs.mem_store_type);

    // Effective load type: suppressed on a bad-tag gated load OR a kmem violation.
    mem_load_type_t pac_eff_load_type;
    assign pac_eff_load_type = (kmem_violation || (pac_ld_gated && !pac_ld_ok))
                             ? NO_LOAD : ID_regs.mem_load_type;
`endif

    // On a branch misprediction, if the wrong-path fall-through is a LOAD, let it
    // drain into MEM (marked speculative) instead of hard-clearing it, but strip
    // its commit (no writeback, no store) so it has no architectural effect.
    logic drain_load;
    assign drain_load = spec_squash && (|ID_regs.mem_load_type);

    always_ff @(posedge clock, posedge reset) begin
        if (reset || (flush && (!ID_regs.linkpc || takenHandler) && !drain_load)) begin
            EX_regs <= '0;
        end else if (!data_cache_miss_stall) begin
            EX_regs.spec <= drain_load;
`ifdef ENABLE_PAC
            EX_regs.out <= pac_ld_addr;   // gated good tag -> PROBE line; else canonical
`else
            EX_regs.out <= ext_out;
`endif
            EX_regs.B_data <= forwarded_B;
            EX_regs.W_regnum <= ID_regs.W_regnum;
            EX_regs.pc4 <= ID_regs.pc4;
            EX_regs.predicted_npc <= ID_regs.predicted_npc;
            EX_regs.pac_fail <= ID_regs.pac_fail;
`ifdef ENABLE_PAC
            // A bad-tag gated load or a non-gated kernel-region access carries a
            // deferred PAC fault (cp0 exc 0x10). The raw fault is propagated down
            // the pipe unconditionally; the generic commit-stage rule in cp0 (a
            // speculative EX_regs.spec instruction commits no exception) decides
            // whether it actually commits.
            EX_regs.pac_ld_fail <= (pac_ld_fault || kmem_violation);
`endif
            EX_regs.overflow <= overflow && (!ID_regs.ignore_overflow);
            EX_regs.zero <= zero;
            EX_regs.sel <= ID_regs.inst[2:0];
`ifdef ENABLE_PAC
            // suppress the access on a bad-tag gated load or a kmem violation (no
            // cache access); a good-tag gated load proceeds to PAC_PROBE_ADDR.
            EX_regs.mem_load_type  <= pac_eff_load_type;
            EX_regs.mem_store_type <= (drain_load || kmem_violation) ? NO_STORE
                                                                     : ID_regs.mem_store_type;
`else
            EX_regs.mem_load_type <= ID_regs.mem_load_type;
            EX_regs.mem_store_type <= drain_load ? NO_STORE : ID_regs.mem_store_type;
`endif
            EX_regs.MFC0 <= ID_regs.MFC0;
            EX_regs.MTC0 <= ID_regs.MTC0;
            EX_regs.break_ <= ID_regs.break_;
            EX_regs.syscall <= ID_regs.syscall;
            EX_regs.BEQ <= ID_regs.BEQ;
            EX_regs.BNE <= ID_regs.BNE;
            EX_regs.BC <= ID_regs.BC;
            EX_regs.BAL <= ID_regs.BAL;
            EX_regs.cache <= ID_regs.cache;
            EX_regs.pc_branch <= ID_regs.pc_branch;
            EX_regs.write_enable <= drain_load ? 1'b0 : ID_regs.write_enable;
            EX_regs.signed_mem_out <= ID_regs.signed_mem_out;
            EX_regs.linkpc <= ID_regs.linkpc;
            EX_regs.cp0_rd <= ID_regs.cp0_rd;
`ifdef DEBUGGER
            EX_regs.inst <= ID_regs.inst;
            EX_regs.pc   <= ID_regs.pc;
`endif
        end
    end
endmodule
