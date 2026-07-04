/* Linker script for the server-side SECRET kernel: KERNEL region starts at
 * 0x2000 (PAC_KERNEL_BASE for the timing variant). __start (reset entry) and the
 * kernel_flag WIN (.org 0x30 -> 0x2030) are pinned here; server.py splices this
 * over the player's user region [0, 0x2000). */
SECTIONS
{
    /DISCARD/ : {
        *(.eh_frame)
        *(.note*)
        *(.pdr)
        *(.MIPS.options)
        *(.got)
        *(.got.plt)
        *(.plt)
        *(.gnu.attributes)
        *(.MIPS.abiflags)
        *(.reginfo)
    }

    . = 0x0;

    .bootinfo : {
        KEEP(*(.boot*))
    }
    .comment : {
        *(.comment)
    }

    . = 0x2000;                       /* PAC_KERNEL_BASE (timing variant) */

    .text : {
        *(.text)
        *(.text.*)
    }

    .rodata : {
        *(.rodata)
        *(.rodata.*)
    }

    .data : {
        PROVIDE(_gp = .);
        *(.sdata)
        *(.data)
    }

    .bss (NOLOAD) : {
        *(.sbss)
        *(.bss)
        *(COMMON)
    }

    .stack (NOLOAD) : ALIGN(16) {
        _stack_bottom = .;
        . += 0x200;
        PROVIDE(_stack_top = .);
    }
}
