// pac.sv -- Pointer Authentication (PAC).
//
// Two modules:
//   * pac_sign   -- compute a signed pointer {tag, VA}. Not exposed as an
//                   instruction: it is only instantiated inside pac_verify to
//                   recompute the expected tag.
//   * pac_verify -- authenticate a pointer. Instantiated at core_IF (I-cache
//                   fetch) and core_branch (JR/JALR target); a tag mismatch
//                   faults architecturally (I-cache: deferred cp0 exc 0x10;
//                   JR: redirect to the PAC handler).
//
// Pointer layout (TAG_BITS + VA_BITS must equal 64):
//
//      63            48 47                                   0
//     +----------------+--------------------------------------+
//     |   PAC tag      |        virtual address (VA)          |
//     +----------------+--------------------------------------+
//
// tag = PRF(key, VA, modifier): `key` is a secret held in a CP0 register that
// user code cannot read, `modifier` a per-use context/salt. No signing
// instruction is exposed to software.

// Tag width is configurable via +define+PAC_TAG_BITS (CMake ODMIPS_PAC_TAG_BITS).
`ifndef PAC_TAG_BITS
`define PAC_TAG_BITS 16
`endif

module pac_sign #(
    parameter int TAG_BITS = `PAC_TAG_BITS,
    parameter int VA_BITS  = 64 - `PAC_TAG_BITS,   // TAG_BITS + VA_BITS == 64
    parameter int ROUNDS   = 4
) (
    /* verilator lint_off UNUSEDSIGNAL */
    input logic [63:0] ptr,       // raw pointer; only [VA_BITS-1:0] is signed
    /* verilator lint_on UNUSEDSIGNAL */
    input  logic [63:0] modifier,  // context / salt
    input  logic [63:0] key,       // secret PAC key (from CP0)
    output logic [63:0] signed_ptr // {tag, VA}
);
    // Keyed ARX mixing function: adds fold in the key/modifier, rotations and
    // xorshift diffuse bits.
    function automatic logic [63:0] pac_prf(input logic [63:0] data,
                                            input logic [63:0] mod_in,
                                            input logic [63:0] k);
        logic [63:0] s;
        begin
            s = data ^ mod_in ^ k;
            for (int r = 0; r < ROUNDS; r++) begin
                s = s + {k[31:0], k[63:32]};   // add rotated key
                s = {s[58:0], s[63:59]};        // rotate left 5
                s = s ^ (s >> 17);              // xorshift diffuse
                s = s + mod_in;                 // mix modifier
                s = {s[40:0], s[63:41]};        // rotate left 23
                s = s ^ k;
            end
            pac_prf = s;
        end
    endfunction

    logic [63:0] va;
    logic [TAG_BITS-1:0] tag;

    always_comb begin
        va = {{(64 - VA_BITS) {1'b0}}, ptr[VA_BITS-1:0]};
        tag = pac_prf(va, modifier, key)[TAG_BITS-1:0];
        signed_ptr = {tag, ptr[VA_BITS-1:0]};
    end
endmodule

module pac_verify #(
    parameter int TAG_BITS = `PAC_TAG_BITS,
    parameter int VA_BITS  = 64 - `PAC_TAG_BITS,
    parameter int ROUNDS   = 4
) (
    input  logic [63:0] signed_ptr,    // pointer to authenticate {tag, VA}
    input  logic [63:0] modifier,      // must match the signing modifier
    input  logic [63:0] key,           // secret PAC key (from CP0)
    input  logic        check,         // this op is a PAC-gated access
    output logic [63:0] auth_ptr,      // tag-stripped canonical pointer to use
    output logic        verify_ok,     // 1 = tag matches
    output logic        pac_exception  // check & !verify_ok
);
    logic [63:0] stripped;
    /* verilator lint_off UNUSEDSIGNAL */
    logic [63:0] expected_signed;  // only the tag field [63:VA_BITS] is read
    /* verilator lint_on UNUSEDSIGNAL */
    logic [TAG_BITS-1:0] expected_tag, actual_tag;

    // canonical (tag-cleared) pointer
    assign stripped = {{(64 - VA_BITS) {1'b0}}, signed_ptr[VA_BITS-1:0]};

    // re-sign the stripped pointer and compare the resulting tag
    pac_sign #(
        .TAG_BITS(TAG_BITS),
        .VA_BITS (VA_BITS),
        .ROUNDS  (ROUNDS)
    ) recompute (
        .ptr       (stripped),
        .modifier  (modifier),
        .key       (key),
        .signed_ptr(expected_signed)
    );

    always_comb begin
        expected_tag  = expected_signed[63:VA_BITS];
        actual_tag    = signed_ptr[63:VA_BITS];
        verify_ok     = (expected_tag == actual_tag);
        auth_ptr      = stripped;
        pac_exception = check && !verify_ok;
    end
endmodule
