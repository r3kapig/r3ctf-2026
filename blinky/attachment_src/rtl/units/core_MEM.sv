import structures::EX_regs_t;
import structures::MEM_regs_t;
import structures::LOAD_WORD;
import structures::NO_STORE;
import structures::mem_bus_req_t;
import structures::mem_bus_resp_t;
import structures::cache_action_t;
import structures::DCACHE;

module core_MEM (
    input logic clock,
    input logic reset,
    /* verilator lint_off UNUSEDSIGNAL */
    input EX_regs_t EX_regs,
    /* verilator lint_on UNUSEDSIGNAL */
    input logic [63:0] fetch_pc,
    input logic [63:0] ID_pc,
    input logic ID_reserved_inst_E,
    input logic [7:0] interrupt_sources,
    input logic flush,
    input logic ID_ERET,
    input logic d_valid,
    input logic [63:0] d_rdata,
    output MEM_regs_t MEM_regs,
    output logic [63:0] MEM1_forward_data,
    output logic [4:0] MEM1_forward_regnum,
    output logic MEM1_forward_write_enable,
    output logic data_cache_miss_stall  /* verilator public */,
`ifdef ENABLE_PAC
    output logic kernel_mode,  // CP0 effective mode forwarded to the branch unit
    output logic [63:0] pac_key,  // CP0 PAC key forwarded to the branch/IF verifiers
    input  logic pac_gate_valid,  // deferred PAC gate reaching MEM (from branch unit)
    input  logic pac_gate_ok,     // its tag authenticated
`endif

    // -- mem bus --
    output mem_bus_req_t  data_req,
    input  mem_bus_resp_t data_resp
);

    typedef struct packed {
        logic [63:0] EPC, EX_out, EX_pc4, c0_rd_data;
        logic [4:0] W_regnum;
        logic write_enable,
            EX_mem_load, takenHandler, EX_linkpc, EX_MFC0
        ;  // ofs being used, if change, also change coreTest
`ifdef DEBUGGER
        logic [31:0] inst;
        logic [63:0] pc;
`endif
    } MEM1_t;

    MEM1_t MEM1;
    logic [63:0] EPC, c0_rd_data, data_out;
    logic takenHandler  /* verilator public */, data_cache_miss;
    // Peripheral read result pipelined MEM1 -> MEM2. d_rdata/d_valid are
    // combinational off the *current* MEM1 instruction, but the alu_mem_mux
    // consumes them for the instruction now in MEM2, so they must be registered
    // to stay aligned with MEM1.EX_mem_load (cache data_out is already registered
    // inside cache_L1, which is why cache loads did not need this).
    logic d_valid_r;
    logic [63:0] d_rdata_r;

    // -- MEM cycle 1 --
    // -- cp0 --
    cp0 cp0_ (
        .rd_data(c0_rd_data),
        .EPC(EPC),
        .takenHandler(takenHandler),
`ifdef ENABLE_PAC
        .kernel_mode(kernel_mode),
        .pac_key(pac_key),
`endif
        .wr_data(EX_regs.B_data),
        .regnum(EX_regs.cp0_rd),
        .sel(EX_regs.sel),
        .IF_pc(fetch_pc),
        .curr_pc(ID_pc),
        .MTC0(EX_regs.MTC0),
        .ERET(ID_ERET),
        .interrupt_source(interrupt_sources),
        .clock(clock),
        .reset(reset),
        .overflow(EX_regs.overflow),
        .reserved_inst(ID_reserved_inst_E),
        .break_(EX_regs.break_),
        .spec(EX_regs.spec),  // squash this instr's exceptions if it is speculative
`ifdef ENABLE_PAC
        .pac_fail(EX_regs.pac_fail),
        .pac_ld_fail(EX_regs.pac_ld_fail),
        .pac_gate_valid(pac_gate_valid),
        .pac_gate_ok(pac_gate_ok),
`endif
        .syscall(EX_regs.syscall)
    );

    cache_action_t cache_action_temp;

    cache_L1 data_cache (
        .clock(clock),
        .reset(reset),
        .enable(1'b1),
        .clear(1'b0),
        .signed_type(EX_regs.signed_mem_out),
        .addr(EX_regs.out),
        .wdata(EX_regs.B_data),
        .mem_load_type(EX_regs.mem_load_type & {3{~d_valid}}), // mmio use memory load type but not load from
        .mem_store_type(EX_regs.mem_store_type & {3{~d_valid}}), // mmio use memory store type but not store into
        .rdata(data_out),
        .miss(data_cache_miss),
        .cache_inst(EX_regs.cache && (cache_action_temp.t == DCACHE)),
        .cache_op(cache_action_temp.op),  // W_regnum filled with rt which is cache op with target
        .req(data_req),
        .resp(data_resp)
    );

    // -- MEM cycle 2 --
    logic [63:0] alu_mem_d_out, W_data, W_data_lui_linkpc;
    mux4v #(64) alu_mem_mux (
        alu_mem_d_out,
        MEM1.EX_out,
        data_out,
        'x,  // peripheral write, mem_out will not be used
        d_rdata_r,
        {d_valid_r, MEM1.EX_mem_load}
    );


    mux2v #(64) mfc0_mux (
        W_data,
        alu_mem_d_out,
        MEM1.c0_rd_data,
        MEM1.EX_MFC0
    );

    mux2v #(64) linkpc_mux (
        W_data_lui_linkpc,
        W_data,
        MEM1.EX_pc4,
        MEM1.EX_linkpc
    );

    mux4v #(64) forward_mux (
        MEM1_forward_data,
        MEM1.EX_out,
        MEM1.c0_rd_data,
        MEM1.EX_out,
        MEM1.EX_pc4,
        {MEM1.EX_linkpc, MEM1.EX_MFC0}
    );

    always_comb begin
        data_cache_miss_stall = data_cache_miss && !data_resp.mem_ready;
        cache_action_temp = EX_regs.W_regnum;
        MEM1_forward_regnum = MEM1.W_regnum;
        MEM1_forward_write_enable = MEM1.write_enable && !MEM1.EX_mem_load;
    end

    always_ff @(posedge clock, posedge reset) begin
`ifdef DEBUG
        if (|EX_regs.mem_load_type) begin
            $display("read addr: %h, data: %h, final: %h, reg=$%d, type = %d",
                     EX_regs.out, data_out, W_data_lui_linkpc,
                     EX_regs.W_regnum, EX_regs.mem_load_type);
        end
        if (|EX_regs.mem_store_type) begin
            $display("write addr: %h, data: %h, type: %d", EX_regs.out,
                     EX_regs.B_data, EX_regs.mem_store_type);
        end
`endif
        if (reset) begin
            MEM1 <= '0;
            d_valid_r <= '0;
            d_rdata_r <= '0;
            MEM_regs.EPC <= '0;
            MEM_regs.W_regnum <= '0;
            MEM_regs.write_enable <= '0;
            MEM_regs.takenHandler <= '0;

`ifdef DEBUGGER
            MEM_regs.pc   <= '0;
            MEM_regs.inst <= '0;
`endif
        end else begin
            d_valid_r <= d_valid;
            d_rdata_r <= d_rdata;
            MEM1.EPC <= EPC;
            MEM1.W_regnum <= EX_regs.W_regnum;
            MEM1.write_enable <= EX_regs.write_enable;
            MEM1.takenHandler <= takenHandler;
            MEM1.EX_out <= EX_regs.out;
            MEM1.EX_pc4 <= EX_regs.pc4;
            MEM1.c0_rd_data <= c0_rd_data;
            MEM1.EX_mem_load <= |EX_regs.mem_load_type;
            MEM1.EX_linkpc <= EX_regs.linkpc;
            MEM1.EX_MFC0 <= EX_regs.MFC0;

            MEM_regs.EPC <= MEM1.EPC;
            MEM_regs.takenHandler <= MEM1.takenHandler;
            MEM_regs.W_regnum <= MEM1.W_regnum;
            MEM_regs.write_enable <= MEM1.write_enable;
            MEM_regs.W_data <= W_data_lui_linkpc;

`ifdef DEBUGGER
            MEM1.pc <= EX_regs.pc;
            MEM1.inst <= EX_regs.inst;
            MEM_regs.pc <= MEM1.pc;
            MEM_regs.inst <= MEM1.inst;
`endif
        end
    end
endmodule
