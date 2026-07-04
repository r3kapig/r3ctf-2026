/* Player linker script. Put your exploit in `.section .boot,"ax"` (loaded at 0x0,
 * the USER region [0, 0x2000)). For local runs, run_local.sh splices example_kernel.mem
 * in at 0x2000; the server DISCARDS anything you place at >= 0x2000 and splices its
 * own secret kernel there. See README.md / build.sh / run_local.sh. */
SECTIONS
{
    /DISCARD/ : {
        *(.eh_frame) *(.note*) *(.pdr) *(.MIPS.options) *(.got) *(.got.plt)
        *(.plt) *(.gnu.attributes) *(.MIPS.abiflags) *(.reginfo)
    }

    . = 0x0;
    .bootinfo : { KEEP(*(.boot*)) }          /* your USER submission */
    .comment  : { *(.comment) }

    . = 0x2000;                              /* PAC_KERNEL_BASE (server-owned) */
    .text : { *(.text) *(.text.*) }
    .rodata : { *(.rodata) *(.rodata.*) }
    .data : { PROVIDE(_gp = .); *(.sdata) *(.data) }
    .bss (NOLOAD) : { *(.sbss) *(.bss) *(COMMON) }
    .stack (NOLOAD) : ALIGN(16) { _stack_bottom = .; . += 0x200; PROVIDE(_stack_top = .); }
}
