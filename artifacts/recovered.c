/*
 * recovered.c — Phase 5.7.2 Conservative ARM64 Coverage Cleanup
 * Schema version: 5.7.2
 * Generated: 2026-06-18T23:36:16Z
 *
 * AUTO-GENERATED — DO NOT EDIT
 *
 * This file contains conservative function skeletons reconstructed
 * from binary analysis evidence. No source-level semantics are
 * invented. Missing evidence is acceptable; fabricated evidence
 * is not.
 */

#include <stdint.h>
#include <stddef.h>

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int8_t i8;
typedef int16_t i16;
typedef int32_t i32;
typedef int64_t i64;

/*
 * HEPHAESTUS_UNKNOWN_COND is a syntax adapter for unrecovered branch
 * predicates. Its argument preserves low-level evidence. The return value is
 * not a recovered program condition and must not be used for behavioral claims.
 */
static int HEPHAESTUS_UNKNOWN_COND(const char *evidence)
{
    (void)evidence;
    return 0;
}

/* ================================================== */
/*                 Forward Declarations                */
/* ================================================== */

int32_t main(int32_t argc, char **argv);
uint64_t FUN_100000494(void);
int32_t main_0x100000548(void);
uint64_t FUN_100000554(void);
uint64_t mixed_driver(void);
uint64_t recursive_sum(uint64_t arg1, uint64_t arg2, uint64_t arg_30h);
uint64_t cfg_pressure(void);
uint64_t FUN_1000008ec(void);
uint64_t even_path(uint64_t arg1, uint64_t arg_20h);
uint64_t table_walk(uint64_t arg1, uint64_t arg2, uint64_t arg_40h);
uint64_t apply_callback(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg4, uint64_t arg_50h);
uint64_t indirect_pressure(void);
uint64_t FUN_100000c4c(void);
uint64_t classify_value(uint64_t arg1, uint64_t arg2, uint64_t arg_10h);
uint64_t byte_halfword_pressure(void);
uint64_t pointer_churn(int32_t arg1, uint64_t arg2, uint64_t arg_40h);
uint64_t odd_path(uint64_t arg1, uint64_t arg_20h);
uint64_t scramble(uint64_t arg1, int32_t arg_10h);
uint64_t stack_chk_fail(void);
int32_t printf(void * format);
int32_t puts(void * s);
uint64_t strlen(void * s);

/* Conservative call target helpers */
u64 call_0x10000082c();
u64 call_0x1000008fc();
u64 call_0x100000978();
u64 call_0x100000b14();
u64 call_0x100000d94();
u64 call_0x100000ed0();
u64 call_0x100000f50();
u64 call_0x100000f94();
u64 call_0x100000fa0();
u64 call_0x100000fac();
u64 call_0x100000fb8();

/* ================================================== */
/*                 Function Definitions                */
/* ================================================== */

int32_t main(int32_t argc, char **argv)
{
    /* Entry: 0x100000460 */
    /* Body status: structured */
    /* 45 basic block(s), 243 instruction(s) */

    /* ABI argument bindings: */
    /*   ? => param 1 (stack_save_restore) */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[20, 24, 32, 44, 48, 52, 56, 60, 64, 68, 72, 76, 80, 84, 88, 100, 104, 168, 176, 180], sizes=[4] */
    /*   base=x8, kind=array_like, offsets=[0, 8], sizes=[4] */
    /*   base=x9, kind=array_like, offsets=[0, 4, 8], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 tmp_x27 = 0;
    u64 tmp_x28 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u32 tmp_w11 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m24 = 0;
    u32 stack_20 = 0;
    u64 stack_32 = 0;
    u64 stack_44 = 0;
    u64 stack_48 = 0;
    u64 stack_72 = 0;
    u64 stack_76 = 0;
    u64 stack_80 = 0;
    u64 stack_84 = 0;
    u64 stack_88 = 0;
    u32 stack_100 = 0;
    u64 stack_104 = 0;
    u64 stack_168 = 0;
    u32 stack_176 = 0;
    u64 stack_180 = 0;
    u64 stack_320 = 0;
    u64 stack_328 = 0;
    u64 stack_336 = 0;
    u64 stack_344 = 0;

    u64 arg1 = (u64)(uintptr_t)argv;       /* main ABI bridge: argv */

    /* Control flow structure: */
    /* block 0x100000460 */
    tmp_sp = tmp_sp - 352; /* sub sp, sp, 0x160 */
    stack_320 = tmp_x28; /* stp x28, x27, [sp + var_140h] */
    stack_328 = tmp_x27; /* paired store second register inferred offset +8 */
    stack_336 = tmp_fp; /* stp x29, x30, [sp + var_150h] */
    stack_344 = tmp_lr; /* paired store second register inferred offset +8 */
    tmp_fp = tmp_sp + 336; /* add x29, sp, 0x150 */
    arg1 = 0x100004000; /* adrp x8, reloc.__stack_chk_fail */
    arg1 = *(u64 *)(arg1 + 8); /* ldr x8, [x8, 8] */
    arg1 = *(u64 *)(arg1); /* ldr x8, [x8] */
    stack_m24 = arg1; /* stur x8, [x29, -0x18] */
    stack_104 = 0; /* str wzr, [sp + var_68h] */
    stack_100 = tmp_w0; /* str w0, [sp + var_64h] */
    stack_88 = tmp_x1; /* str x1, [sp + var_58h] */
    stack_84 = 0; /* str wzr, [sp + var_54h] */
    /* branch to 0x100000494 */ /* b 0x100000494 */
    /* loop kind: while_like */
    /* loop header: 0x100000494 */
    /* loop exits: ['0x10000057c'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x10000049c after subs at 0x100000498; target 0x10000057c; loop polarity inverted")) {
        /* if/else condition block: 0x100000494 */
        /* merge block: 0x1000004e8 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x10000049c after subs at 0x100000498; target 0x10000057c")) {
            /* block 0x1000004bc */
            /* branch to 0x1000004c0 */ /* b 0x1000004c0 */
            /* block 0x1000004c0 */
            arg1 = stack_84; /* ldr w8, [sp + var_54h] */
            tmp_w9 = 13; /* mov w9, 0xd */
            arg1 = arg1 * tmp_w9; /* mul w8, w8, w9 */
            stack_44 = arg1; /* str w8, [sp + var_2ch] */
            /* branch to 0x1000004e8 */ /* b 0x1000004e8 */
        } else {
            /* block 0x1000004d4 */
            arg1 = stack_84; /* ldr w8, [sp + var_54h] */
            tmp_w9 = 17; /* mov w9, 0x11 */
            /* 0x1000004dc: unsupported instruction: mneg w8, w8, w9 */
            stack_44 = arg1; /* str w8, [sp + var_2ch] */
            /* branch to 0x1000004e8 */ /* b 0x1000004e8 */
        }
        /* if/else condition block: 0x1000004e8 */
        /* merge block: 0x100000554 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000528 after subs at 0x100000524; target 0x100000548; polarity inverted")) {
            /* block 0x10000052c */
            /* branch to 0x100000530 */ /* b 0x100000530 */
            /* block 0x100000530 */
            arg1 = stack_84; /* ldr w8, [sp + var_54h] */
            tmp_w9 = arg1 + 1; /* add w9, w8, 1 */
            arg1 = tmp_fp - 120; /* sub x8, x29, 0x78 */
            arg1 = arg1 + ((i64)(i32)tmp_w9); /* add x8, x8, w9, sxtw 4 */
            stack_32 = arg1; /* str x8, [sp + var_20h] */
            /* branch to 0x100000554 */ /* b 0x100000554 */
        } else {
            /* block 0x100000548 */
            arg1 = 0; /* mov x8, 0 */
            stack_32 = arg1; /* str x8, [sp + var_20h] */
            /* branch to 0x100000554 */ /* b 0x100000554 */
        }
        /* block 0x100000554 */
        arg1 = stack_32; /* ldr x8, [sp + var_20h] */
        tmp_x10 = (i64)(i32)stack_84; /* ldrsw x10, [sp + var_54h] */
        tmp_x9 = tmp_fp - 120; /* sub x9, x29, 0x78 */
        tmp_x9 = tmp_x9 + (tmp_x10 << 0); /* add x9, x9, x10, lsl 4 */
        *(u64 *)(tmp_x9 + 8) = arg1; /* str x8, [x9, 8] */
        /* branch to 0x10000056c */ /* b 0x10000056c */
        /* block 0x10000056c */
        arg1 = stack_84; /* ldr w8, [sp + var_54h] */
        arg1 = arg1 + 1; /* add w8, w8, 1 */
        stack_84 = arg1; /* str w8, [sp + var_54h] */
        /* branch to 0x100000494 */ /* b 0x100000494 */
    }
    /* block 0x10000057c */
    arg1 = tmp_fp - 120; /* sub x8, x29, 0x78 */
    stack_168 = arg1; /* str x8, [sp + var_a8h] */
    tmp_w9 = stack_100; /* ldr w9, [sp + var_64h] */
    arg1 = 53261; /* mov w8, 0xd00d */
    /* 0x10000058c: unsupported instruction: movk w8, 0xc001, lsl 16 */
    arg1 = arg1 ^ tmp_w9; /* eor w8, w8, w9 */
    stack_176 = arg1; /* str w8, [sp + var_b0h] */
    arg1 = stack_100; /* ldr w8, [sp + var_64h] */
    tmp_w9 = 3; /* mov w9, 3 */
    arg1 = arg1 * tmp_w9; /* mul w8, w8, w9 */
    stack_180 = arg1; /* str w8, [sp + var_0h_5] */
    stack_80 = 0; /* str wzr, [sp + var_50h] */
    /* branch to 0x1000005b0 */ /* b 0x1000005b0 */
    /* loop kind: while_like */
    /* loop header: 0x1000005b0 */
    /* loop exits: ['0x100000604'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000005b8 after subs at 0x1000005b4; target 0x100000604; loop polarity inverted")) {
        /* block 0x1000005b0 */
        arg1 = stack_80; /* ldr w8, [sp + var_50h] */
        arg1 = arg1 - 32; /* subs w8, w8, 0x20; flags updated */
        /* conditional branch b.ge -> 0x100000604 */
        /* block 0x1000005bc */
        /* branch to 0x1000005c0 */ /* b 0x1000005c0 */
        /* block 0x1000005c0 */
        arg1 = stack_80; /* ldr w8, [sp + var_50h] */
        tmp_w9 = 11; /* mov w9, 0xb */
        arg1 = arg1 * tmp_w9; /* mul w8, w8, w9 */
        tmp_x9 = tmp_sp + 168; /* add x9, sp, 0xa8 */
        tmp_w10 = stack_176; /* ldr w10, [sp + var_b0h] */
        tmp_w11 = stack_80; /* ldr w11, [sp + var_50h] */
        tmp_w11 = tmp_w11 & 7; /* and w11, w11, 7 */
        tmp_w10 = tmp_w10 >> tmp_w11; /* lsr w10, w10, w11 */
        arg1 = arg1 ^ tmp_w10; /* eor w8, w8, w10 */
        tmp_x9 = tmp_x9 + 16; /* add x9, x9, 0x10 */
        tmp_x10 = (i64)(i32)stack_80; /* ldrsw x10, [sp + var_50h] */
        *(u8 *)(tmp_x9) = arg1; /* strb w8, [x9, x10] */
        /* branch to 0x1000005f4 */ /* b 0x1000005f4 */
        /* block 0x1000005f4 */
        arg1 = stack_80; /* ldr w8, [sp + var_50h] */
        arg1 = arg1 + 1; /* add w8, w8, 1 */
        stack_80 = arg1; /* str w8, [sp + var_50h] */
        /* branch to 0x1000005b0 */ /* b 0x1000005b0 */
    }
    /* block 0x100000604 */
    arg1 = stack_100; /* ldr w8, [sp + var_64h] */
    arg1 = arg1 - 1; /* subs w8, w8, 1; flags updated */
    /* conditional branch b.le -> 0x100000644 */
    /* block 0x100000610 */
    /* branch to 0x100000614 */ /* b 0x100000614 */
    /* block 0x100000614 */
    arg1 = stack_88; /* ldr x8, [sp + var_58h] */
    arg1 = *(u64 *)(arg1 + 8); /* ldr x8, [x8, 8] */
    /* cbz arg1 -> 0x100000644 */
    /* block 0x100000620 */
    /* branch to 0x100000624 */ /* b 0x100000624 */
    /* block 0x100000624 */
    arg1 = stack_88; /* ldr x8, [sp + var_58h] */
    tmp_x0 = *(u64 *)(arg1 + 8); /* ldr x0, [x8, 8] */
    call_0x100000fb8(tmp_x0); /* bl sym.imp.strlen; args refined from same-block evidence */
    tmp_x9 = tmp_x0; /* mov x9, x0 */
    arg1 = stack_176; /* ldr w8, [sp + var_b0h] */
    arg1 = arg1 ^ tmp_w9; /* eor w8, w8, w9 */
    stack_176 = arg1; /* str w8, [sp + var_b0h] */
    /* branch to 0x100000644 */ /* b 0x100000644 */
    /* block 0x100000644 */
    stack_76 = 0; /* str wzr, [sp + var_4ch] */
    /* branch to 0x10000064c */ /* b 0x10000064c */
    /* loop kind: while_like */
    /* loop header: 0x10000064c */
    /* loop exits: ['0x100000694'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000654 after subs at 0x100000650; target 0x100000694; loop polarity inverted")) {
        /* block 0x10000064c */
        arg1 = stack_76; /* ldr w8, [sp + var_4ch] */
        arg1 = arg1 - 10; /* subs w8, w8, 0xa; flags updated */
        /* conditional branch b.ge -> 0x100000694 */
        /* block 0x100000658 */
        /* branch to 0x10000065c */ /* b 0x10000065c */
        /* block 0x10000065c */
        arg1 = stack_176; /* ldr w8, [sp + var_b0h] */
        tmp_w9 = stack_76; /* ldr w9, [sp + var_4ch] */
        tmp_w9 = tmp_w9 & 15; /* and w9, w9, 0xf */
        tmp_w9 = arg1 >> tmp_w9; /* lsr w9, w8, w9 */
        arg1 = -100; /* mov w8, -0x64 */
        arg1 = arg1 + tmp_w9; /* add w8, w8, w9, uxtb */
        tmp_x10 = (i64)(i32)stack_76; /* ldrsw x10, [sp + var_4ch] */
        tmp_x9 = tmp_sp + 128; /* add x9, sp, 0x80 */
        *(u32 *)(tmp_x9) = arg1; /* str w8, [x9, x10, lsl 2] */
        /* branch to 0x100000684 */ /* b 0x100000684 */
        /* block 0x100000684 */
        arg1 = stack_76; /* ldr w8, [sp + var_4ch] */
        arg1 = arg1 + 1; /* add w8, w8, 1 */
        stack_76 = arg1; /* str w8, [sp + var_4ch] */
        /* branch to 0x10000064c */ /* b 0x10000064c */
    }
    /* block 0x100000694 */
    stack_72 = 0; /* str wzr, [sp + var_48h] */
    /* branch to 0x10000069c */ /* b 0x10000069c */
    /* loop kind: while_like */
    /* loop header: 0x10000069c */
    /* loop exits: ['0x1000006f8'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000006a4 after subs at 0x1000006a0; target 0x1000006f8; loop polarity inverted")) {
        /* block 0x10000069c */
        arg1 = stack_72; /* ldr w8, [sp + var_48h] */
        arg1 = arg1 - 20; /* subs w8, w8, 0x14; flags updated */
        /* conditional branch b.ge -> 0x1000006f8 */
        /* block 0x1000006a8 */
        /* branch to 0x1000006ac */ /* b 0x1000006ac */
        /* block 0x1000006ac */
        arg1 = stack_72; /* ldr w8, [sp + var_48h] */
        tmp_w10 = 10; /* mov w10, 0xa */
        tmp_w9 = ((i32)arg1) / ((i32)tmp_w10); /* sdiv w9, w8, w10 */
        tmp_w9 = tmp_w9 * tmp_w10; /* mul w9, w9, w10 */
        tmp_w9 = arg1 - tmp_w9; /* subs w9, w8, w9; flags updated */
        arg1 = tmp_sp + 128; /* add x8, sp, 0x80 */
        arg1 = *(u32 *)(arg1); /* ldr w8, [x8, w9, sxtw 2] */
        tmp_w9 = stack_72; /* ldr w9, [sp + var_48h] */
        tmp_w10 = 7; /* mov w10, 7 */
        tmp_w9 = tmp_w9 * tmp_w10; /* mul w9, w9, w10 */
        arg1 = arg1 + tmp_w9; /* add w8, w8, w9 */
        tmp_x10 = (i64)(i32)stack_72; /* ldrsw x10, [sp + var_48h] */
        tmp_x9 = tmp_sp + 108; /* add x9, sp, 0x6c */
        *(u8 *)(tmp_x9) = arg1; /* strb w8, [x9, x10] */
        /* branch to 0x1000006e8 */ /* b 0x1000006e8 */
        /* block 0x1000006e8 */
        arg1 = stack_72; /* ldr w8, [sp + var_48h] */
        arg1 = arg1 + 1; /* add w8, w8, 1 */
        stack_72 = arg1; /* str w8, [sp + var_48h] */
        /* branch to 0x10000069c */ /* b 0x10000069c */
    }
    /* if/else condition block: 0x1000006f8 */
    /* merge block: 0x1000007f0 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbnz w8 at 0x100000790 targeting 0x1000007a8; polarity inverted")) {
        /* block 0x100000794 */
        /* branch to 0x100000798 */ /* b 0x100000798 */
        /* block 0x100000798 */
        tmp_x0 = 0x100000000; /* adrp x0, 0x100000000 */
        tmp_x0 = tmp_x0 + 4036; /* add x0, x0, 0xfc4 */
        call_0x100000fac(tmp_x0); /* bl sym.imp.puts; args refined from same-block evidence */
        /* branch to 0x1000007f0 */ /* b 0x1000007f0 */
    } else {
        /* if/else condition block: 0x1000007a8 */
        /* merge block: 0x1000007ec */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: tbz w8 bit 0 at 0x1000007ac targeting 0x1000007d0; polarity inverted")) {
            /* block 0x1000007b0 */
            /* branch to 0x1000007b4 */ /* b 0x1000007b4 */
            /* block 0x1000007b4 */
            arg1 = stack_48; /* ldr w8, [sp + var_30h] */
            tmp_x9 = tmp_sp; /* mov x9, sp */
            *(u64 *)(tmp_x9) = arg1; /* str x8, [x9] */
            tmp_x0 = 0x100000000; /* adrp x0, 0x100000000 */
            tmp_x0 = tmp_x0 + 4041; /* add x0, x0, 0xfc9 */
            call_0x100000fa0(tmp_x0); /* bl sym.imp.printf; args refined from same-block evidence */
            /* branch to 0x1000007ec */ /* b 0x1000007ec */
        } else {
            /* block 0x1000007d0 */
            arg1 = stack_48; /* ldr w8, [sp + var_30h] */
            tmp_x9 = tmp_sp; /* mov x9, sp */
            *(u64 *)(tmp_x9) = arg1; /* str x8, [x9] */
            tmp_x0 = 0x100000000; /* adrp x0, 0x100000000 */
            tmp_x0 = tmp_x0 + 4054; /* add x0, x0, 0xfd6 */
            call_0x100000fa0(tmp_x0); /* bl sym.imp.printf; args refined from same-block evidence */
            /* branch to 0x1000007ec */ /* b 0x1000007ec */
        }
        /* block 0x1000007ec */
        /* branch to 0x1000007f0 */ /* b 0x1000007f0 */
    }
    /* block 0x1000007f0 */
    arg1 = stack_48; /* ldrb w8, [sp + var_30h] */
    stack_20 = arg1; /* str w8, [sp + var_14h] */
    tmp_x9 = stack_m24; /* ldur x9, [x29, -0x18] */
    arg1 = 0x100004000; /* adrp x8, reloc.__stack_chk_fail */
    arg1 = *(u64 *)(arg1 + 8); /* ldr x8, [x8, 8] */
    arg1 = *(u64 *)(arg1); /* ldr x8, [x8] */
    arg1 = arg1 - tmp_x9; /* subs x8, x8, x9; flags updated */
    /* conditional branch b.eq -> 0x100000818 */
    /* block 0x100000818 */
    tmp_w0 = stack_20; /* ldr w0, [sp + var_14h] */
    tmp_fp = stack_336; /* ldp x29, x30, [sp + var_150h] */
    tmp_lr = stack_344; /* paired load second register inferred offset +8 */
    tmp_x28 = stack_320; /* ldp x28, x27, [sp + var_140h] */
    tmp_x27 = stack_328; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 352; /* add sp, sp, 0x160 */
    return tmp_w0; /* return value from w0 before ret */
    /* block 0x100000810 */
    /* branch to 0x100000814 */ /* b 0x100000814 */
    /* block 0x100000814 */
    call_0x100000f94(); /* bl sym.imp.__stack_chk_fail */

}

uint64_t FUN_100000494(void)
{
    /* Entry: 0x100000494 */
    /* Body status: structured */
    /* 9 basic block(s), 45 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[32, 44, 84, 100], sizes=[4, 8] */
    /*   base=x9, kind=scalar, offsets=[4], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u64 tmp_fp = 0;
    u64 stack_32 = 0;
    u32 stack_44 = 0;
    u64 stack_84 = 0;
    u32 stack_100 = 0;

    /* Control flow structure: */
    /* block 0x100000494 */
    tmp_w8 = stack_84; /* ldr w8,[sp, #0x54] */
    tmp_w8 = tmp_w8 - 6; /* subs w8,w8,#0x6; flags updated */
    /* conditional branch b.ge -> 0x10000057c */
    /* block 0x1000004a0 */
    /* branch to 0x1000004a4 */ /* b 0x1000004a4 */
    /* block 0x1000004a4 */
    tmp_w8 = stack_84; /* ldr w8,[sp, #0x54] */
    tmp_w10 = 2; /* mov w10,#0x2 */
    tmp_w9 = ((i32)tmp_w8) / ((i32)tmp_w10); /* sdiv w9,w8,w10 */
    tmp_w9 = tmp_w9 * tmp_w10; /* mul w9,w9,w10 */
    tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
    /* cbnz tmp_w8 -> 0x1000004d4 */
    /* block 0x1000004d4 */
    tmp_w8 = stack_84; /* ldr w8,[sp, #0x54] */
    tmp_w9 = 17; /* mov w9,#0x11 */
    /* 0x1000004dc: unsupported instruction: mneg w8,w8,w9 */
    stack_44 = tmp_w8; /* str w8,[sp, #0x2c] */
    /* branch to 0x1000004e8 */ /* b 0x1000004e8 */
    /* block 0x1000004bc */
    /* branch to 0x1000004c0 */ /* b 0x1000004c0 */
    /* block 0x1000004c0 */
    tmp_w8 = stack_84; /* ldr w8,[sp, #0x54] */
    tmp_w9 = 13; /* mov w9,#0xd */
    tmp_w8 = tmp_w8 * tmp_w9; /* mul w8,w8,w9 */
    stack_44 = tmp_w8; /* str w8,[sp, #0x2c] */
    /* branch to 0x1000004e8 */ /* b 0x1000004e8 */
    /* block 0x1000004e8 */
    tmp_w8 = stack_44; /* ldr w8,[sp, #0x2c] */
    tmp_x9 = (i64)(i32)stack_84; /* ldrsw x9,[sp, #0x54] */
    tmp_x10 = tmp_x9 << 4; /* lsl x10,x9,#0x4 */
    tmp_x9 = tmp_fp - 120; /* sub x9,x29,#0x78 */
    *(u32 *)(tmp_x9 + tmp_x10) = tmp_w8; /* str w8,[x9, x10, LSL #0x0] */
    tmp_w8 = stack_84; /* ldr w8,[sp, #0x54] */
    tmp_w10 = 37; /* mov w10,#0x25 */
    tmp_w8 = tmp_w8 * tmp_w10; /* mul w8,w8,w10 */
    tmp_w10 = stack_100; /* ldr w10,[sp, #0x64] */
    tmp_w8 = tmp_w8 + tmp_w10; /* add w8,w8,w10 */
    tmp_x10 = (i64)(i32)stack_84; /* ldrsw x10,[sp, #0x54] */
    tmp_x9 = tmp_x9 + (tmp_x10 << 4); /* add x9,x9,x10, LSL #0x4 */
    *(u32 *)(tmp_x9 + 4) = tmp_w8; /* str w8,[x9, #0x4] */
    tmp_w8 = stack_84; /* ldr w8,[sp, #0x54] */
    tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
    tmp_w8 = tmp_w8 - 6; /* subs w8,w8,#0x6; flags updated */
    /* conditional branch b.ge -> 0x100000548 */
    /* block 0x10000052c */
    /* branch to 0x100000530 */ /* b 0x100000530 */
    /* block 0x100000530 */
    tmp_w8 = stack_84; /* ldr w8,[sp, #0x54] */
    tmp_w9 = tmp_w8 + 1; /* add w9,w8,#0x1 */
    tmp_x8 = tmp_fp - 120; /* sub x8,x29,#0x78 */
    tmp_x8 = tmp_x8 + (((i64)(i32)tmp_w9) << 4); /* add x8,x8,w9, SXTW  #0x4 */
    stack_32 = tmp_x8; /* str x8,[sp, #0x20] */
    /* branch to 0x100000554 */ /* b 0x100000554 */

    /* return value unknown */
    return 0;
}

int32_t main_0x100000548(void)
{
    /* Entry: 0x100000548 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 3 instruction(s) */

    /* Layout candidates: */
    /*   base=sp, kind=pointer_like, offsets=[32], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x8 = 0;
    u64 stack_32 = 0;

    /* Control flow structure: */
    /* block 0x100000548 */
    tmp_x8 = 0; /* mov x8,#0x0 */
    stack_32 = tmp_x8; /* str x8,[sp, #0x20] */
    /* branch to 0x100000554 */ /* b 0x100000554 */

    /* return value unknown */
    return 0;
}

uint64_t FUN_100000554(void)
{
    /* Entry: 0x100000554 */
    /* Body status: unstructured */
    /* 29 basic block(s), 133 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[24, 32, 52, 56, 60, 64, 68, 72, 76, 80, 84, 88, 100, 168, 176, 180], sizes=[1, 4, 8] */
    /*   base=x8, kind=pointer_like, offsets=[8], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[8], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u32 tmp_w3 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u32 tmp_w11 = 0;
    u64 tmp_fp = 0;
    u64 stack_24 = 0;
    u64 stack_32 = 0;
    u32 stack_52 = 0;
    u32 stack_56 = 0;
    u32 stack_60 = 0;
    u32 stack_64 = 0;
    u32 stack_68 = 0;
    u64 stack_72 = 0;
    u64 stack_76 = 0;
    u64 stack_80 = 0;
    u64 stack_84 = 0;
    u64 stack_88 = 0;
    u32 stack_100 = 0;
    u64 stack_168 = 0;
    u32 stack_176 = 0;
    u32 stack_180 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: fragmented_loop_body */
    {
        /* block 0x100000554 */
        tmp_x8 = stack_32; /* ldr x8,[sp, #0x20] */
        tmp_x10 = (i64)(i32)stack_84; /* ldrsw x10,[sp, #0x54] */
        tmp_x9 = tmp_fp - 120; /* sub x9,x29,#0x78 */
        tmp_x9 = tmp_x9 + (tmp_x10 << 4); /* add x9,x9,x10, LSL #0x4 */
        *(u64 *)(tmp_x9 + 8) = tmp_x8; /* str x8,[x9, #0x8] */
        /* branch to 0x10000056c */ /* b 0x10000056c */
        /* block 0x10000056c */
        tmp_w8 = stack_84; /* ldr w8,[sp, #0x54] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_84 = tmp_w8; /* str w8,[sp, #0x54] */
        /* branch to 0x100000494 */ /* b 0x100000494 */
        /* block 0x10000057c */
        tmp_x8 = tmp_fp - 120; /* sub x8,x29,#0x78 */
        stack_168 = tmp_x8; /* str x8,[sp, #0xa8] */
        tmp_w9 = stack_100; /* ldr w9,[sp, #0x64] */
        tmp_w8 = 53261; /* mov w8,#0xd00d */
        /* 0x10000058c: unsupported instruction: movk w8,#0xc001, LSL #16 */
        tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8,w8,w9 */
        stack_176 = tmp_w8; /* str w8,[sp, #0xb0] */
        tmp_w8 = stack_100; /* ldr w8,[sp, #0x64] */
        tmp_w9 = 3; /* mov w9,#0x3 */
        tmp_w8 = tmp_w8 * tmp_w9; /* mul w8,w8,w9 */
        stack_180 = tmp_w8; /* str w8,[sp, #0xb4] */
        stack_80 = 0; /* str wzr,[sp, #0x50] */
        /* branch to 0x1000005b0 */ /* b 0x1000005b0 */
        /* block 0x1000005b0 */
        tmp_w8 = stack_80; /* ldr w8,[sp, #0x50] */
        tmp_w8 = tmp_w8 - 32; /* subs w8,w8,#0x20; flags updated */
        /* conditional branch b.ge -> 0x100000604 */
        /* block 0x1000005bc */
        /* branch to 0x1000005c0 */ /* b 0x1000005c0 */
        /* block 0x1000005c0 */
        tmp_w8 = stack_80; /* ldr w8,[sp, #0x50] */
        tmp_w9 = 11; /* mov w9,#0xb */
        tmp_w8 = tmp_w8 * tmp_w9; /* mul w8,w8,w9 */
        tmp_x9 = tmp_sp + 168; /* add x9,sp,#0xa8 */
        tmp_w10 = stack_176; /* ldr w10,[sp, #0xb0] */
        tmp_w11 = stack_80; /* ldr w11,[sp, #0x50] */
        tmp_w11 = tmp_w11 & 7; /* and w11,w11,#0x7 */
        tmp_w10 = tmp_w10 >> tmp_w11; /* lsr w10,w10,w11 */
        tmp_w8 = tmp_w8 ^ tmp_w10; /* eor w8,w8,w10 */
        tmp_x9 = tmp_x9 + 16; /* add x9,x9,#0x10 */
        tmp_x10 = (i64)(i32)stack_80; /* ldrsw x10,[sp, #0x50] */
        *(u8 *)(tmp_x9 + tmp_x10) = tmp_w8; /* strb w8,[x9, x10, LSL ] */
        /* branch to 0x1000005f4 */ /* b 0x1000005f4 */
        /* block 0x1000005f4 */
        tmp_w8 = stack_80; /* ldr w8,[sp, #0x50] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_80 = tmp_w8; /* str w8,[sp, #0x50] */
        /* branch to 0x1000005b0 */ /* b 0x1000005b0 */
        /* block 0x100000604 */
        tmp_w8 = stack_100; /* ldr w8,[sp, #0x64] */
        tmp_w8 = tmp_w8 - 1; /* subs w8,w8,#0x1; flags updated */
        /* conditional branch b.le -> 0x100000644 */
        /* block 0x100000610 */
        /* branch to 0x100000614 */ /* b 0x100000614 */
        /* block 0x100000614 */
        tmp_x8 = stack_88; /* ldr x8,[sp, #0x58] */
        tmp_x8 = *(u64 *)(tmp_x8 + 8); /* ldr x8,[x8, #0x8] */
        /* cbz tmp_x8 -> 0x100000644 */
        /* block 0x100000620 */
        /* branch to 0x100000624 */ /* b 0x100000624 */
        /* block 0x100000624 */
        tmp_x8 = stack_88; /* ldr x8,[sp, #0x58] */
        tmp_x0 = *(u64 *)(tmp_x8 + 8); /* ldr x0,[x8, #0x8] */
        call_0x100000fb8(tmp_x0); /* bl 0x100000fb8; args refined from same-block evidence */
        /* block 0x100000630 */
        tmp_x9 = tmp_x0; /* mov x9,x0 */
        tmp_w8 = stack_176; /* ldr w8,[sp, #0xb0] */
        tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8,w8,w9 */
        stack_176 = tmp_w8; /* str w8,[sp, #0xb0] */
        /* branch to 0x100000644 */ /* b 0x100000644 */
        /* block 0x100000644 */
        stack_76 = 0; /* str wzr,[sp, #0x4c] */
        /* branch to 0x10000064c */ /* b 0x10000064c */
        /* block 0x10000064c */
        tmp_w8 = stack_76; /* ldr w8,[sp, #0x4c] */
        tmp_w8 = tmp_w8 - 10; /* subs w8,w8,#0xa; flags updated */
        /* conditional branch b.ge -> 0x100000694 */
        /* block 0x100000658 */
        /* branch to 0x10000065c */ /* b 0x10000065c */
        /* block 0x10000065c */
        tmp_w8 = stack_176; /* ldr w8,[sp, #0xb0] */
        tmp_w9 = stack_76; /* ldr w9,[sp, #0x4c] */
        tmp_w9 = tmp_w9 & 15; /* and w9,w9,#0xf */
        tmp_w9 = tmp_w8 >> tmp_w9; /* lsr w9,w8,w9 */
        tmp_w8 = 0xffffff9c; /* mov w8,#0xffffff9c */
        tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9, UXTB  */
        tmp_x10 = (i64)(i32)stack_76; /* ldrsw x10,[sp, #0x4c] */
        tmp_x9 = tmp_sp + 128; /* add x9,sp,#0x80 */
        *(u32 *)(tmp_x9 + (tmp_x10 << 2)) = tmp_w8; /* str w8,[x9, x10, LSL #0x2] */
        /* branch to 0x100000684 */ /* b 0x100000684 */
        /* block 0x100000684 */
        tmp_w8 = stack_76; /* ldr w8,[sp, #0x4c] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_76 = tmp_w8; /* str w8,[sp, #0x4c] */
        /* branch to 0x10000064c */ /* b 0x10000064c */
        /* block 0x100000694 */
        stack_72 = 0; /* str wzr,[sp, #0x48] */
        /* branch to 0x10000069c */ /* b 0x10000069c */
        /* block 0x10000069c */
        tmp_w8 = stack_72; /* ldr w8,[sp, #0x48] */
        tmp_w8 = tmp_w8 - 20; /* subs w8,w8,#0x14; flags updated */
        /* conditional branch b.ge -> 0x1000006f8 */
        /* block 0x1000006a8 */
        /* branch to 0x1000006ac */ /* b 0x1000006ac */
        /* block 0x1000006ac */
        tmp_w8 = stack_72; /* ldr w8,[sp, #0x48] */
        tmp_w10 = 10; /* mov w10,#0xa */
        tmp_w9 = ((i32)tmp_w8) / ((i32)tmp_w10); /* sdiv w9,w8,w10 */
        tmp_w9 = tmp_w9 * tmp_w10; /* mul w9,w9,w10 */
        tmp_w9 = tmp_w8 - tmp_w9; /* subs w9,w8,w9; flags updated */
        tmp_x8 = tmp_sp + 128; /* add x8,sp,#0x80 */
        tmp_w8 = *(u32 *)(tmp_x8 + (((i64)(i32)tmp_w9) << 2)); /* ldr w8,[x8, w9, SXTW #0x2] */
        tmp_w9 = stack_72; /* ldr w9,[sp, #0x48] */
        tmp_w10 = 7; /* mov w10,#0x7 */
        tmp_w9 = tmp_w9 * tmp_w10; /* mul w9,w9,w10 */
        tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
        tmp_x10 = (i64)(i32)stack_72; /* ldrsw x10,[sp, #0x48] */
        tmp_x9 = tmp_sp + 108; /* add x9,sp,#0x6c */
        *(u8 *)(tmp_x9 + tmp_x10) = tmp_w8; /* strb w8,[x9, x10, LSL ] */
        /* branch to 0x1000006e8 */ /* b 0x1000006e8 */
        /* block 0x1000006e8 */
        tmp_w8 = stack_72; /* ldr w8,[sp, #0x48] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_72 = tmp_w8; /* str w8,[sp, #0x48] */
        /* branch to 0x10000069c */ /* b 0x10000069c */
        /* block 0x1000006f8 */
        tmp_x8 = tmp_sp + 168; /* add x8,sp,#0xa8 */
        stack_24 = tmp_x8; /* str x8,[sp, #0x18] */
        tmp_x0 = stack_168; /* ldr x0,[sp, #0xa8] */
        tmp_w1 = 5; /* mov w1,#0x5 */
        call_0x10000082c(tmp_x0, tmp_w1); /* bl 0x10000082c; args refined from same-block evidence */
        /* block 0x10000070c */
        stack_68 = tmp_w0; /* str w0,[sp, #0x44] */
        tmp_w0 = 9; /* mov w0,#0x9 */
        call_0x1000008fc(tmp_w0); /* bl 0x1000008fc; args refined from same-block evidence */
        /* block 0x100000718 */
        tmp_x8 = tmp_x0; /* mov x8,x0 */
        tmp_x0 = stack_24; /* ldr x0,[sp, #0x18] */
        stack_64 = tmp_w8; /* str w8,[sp, #0x40] */
        tmp_w1 = 32; /* mov w1,#0x20 */
        call_0x100000978(tmp_x0, tmp_w1); /* bl 0x100000978; args refined from same-block evidence */
        /* block 0x10000072c */
        stack_60 = tmp_w0; /* str w0,[sp, #0x3c] */
        tmp_w3 = stack_176; /* ldrb w3,[sp, #0xb0] */
        tmp_x0 = 0x100000000; /* adrp x0,0x100000000 */
        tmp_x0 = tmp_x0 + 3164; /* add x0,x0,#0xc5c */
        tmp_x1 = tmp_sp + 128; /* add x1,sp,#0x80 */
        tmp_x2 = 10; /* mov x2,#0xa */
        call_0x100000b14(tmp_x0, tmp_x1, tmp_x2, tmp_w3); /* bl 0x100000b14; args refined from same-block evidence */
        /* block 0x100000748 */
        stack_56 = tmp_w0; /* str w0,[sp, #0x38] */
        tmp_x0 = tmp_sp + 108; /* add x0,sp,#0x6c */
        tmp_x1 = 20; /* mov x1,#0x14 */
        call_0x100000d94(tmp_x0, tmp_x1); /* bl 0x100000d94; args refined from same-block evidence */
        /* block 0x100000758 */
        stack_52 = tmp_w0; /* str w0,[sp, #0x34] */
        tmp_w8 = stack_68; /* ldr w8,[sp, #0x44] */
        tmp_w9 = stack_64; /* ldr w9,[sp, #0x40] */
        tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
    }
    /* unstructured region end */

    /* return value unknown */
    return 0;
}

uint64_t mixed_driver(void)
{
    /* Entry: 0x100000768 */
    /* Body status: structured */
    /* 15 basic block(s), 49 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[20, 48, 52, 56, 60, 180], sizes=[1, 4] */
    /*   base=x8, kind=array_like, offsets=[0, 8], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[0], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x27 = 0;
    u64 tmp_x28 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w8 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m24 = 0;
    u32 stack_20 = 0;
    u32 stack_48 = 0;
    u64 stack_320 = 0;
    u64 stack_328 = 0;
    u64 stack_336 = 0;
    u64 stack_344 = 0;

    /* Control flow structure: */
    /* if/else condition block: 0x100000768 */
    /* merge block: 0x1000007f0 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbnz w8 at 0x100000790 targeting 0x1000007a8; polarity inverted")) {
        /* block 0x100000794 */
        /* branch to 0x100000798 */ /* b 0x100000798 */
        /* block 0x100000798 */
        tmp_x0 = 0x100000000; /* adrp x0,0x100000000 */
        tmp_x0 = tmp_x0 + 4036; /* add x0,x0,#0xfc4 */
        call_0x100000fac(tmp_x0); /* bl 0x100000fac; args refined from same-block evidence */
        /* block 0x1000007a4 */
        /* branch to 0x1000007f0 */ /* b 0x1000007f0 */
    } else {
        /* if/else condition block: 0x1000007a8 */
        /* merge block: 0x1000007ec */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: tbz w8 bit #0 at 0x1000007ac targeting 0x1000007d0; polarity inverted")) {
            /* block 0x1000007b0 */
            /* branch to 0x1000007b4 */ /* b 0x1000007b4 */
            /* block 0x1000007b4 */
            tmp_w8 = stack_48; /* ldr w8,[sp, #0x30] */
            tmp_x9 = tmp_sp; /* mov x9,sp */
            *(u64 *)(tmp_x9) = tmp_x8; /* str x8,[x9] */
            tmp_x0 = 0x100000000; /* adrp x0,0x100000000 */
            tmp_x0 = tmp_x0 + 4041; /* add x0,x0,#0xfc9 */
            call_0x100000fa0(tmp_x0); /* bl 0x100000fa0; args refined from same-block evidence */
            /* block 0x1000007cc */
            /* branch to 0x1000007ec */ /* b 0x1000007ec */
        } else {
            /* block 0x1000007d0 */
            tmp_w8 = stack_48; /* ldr w8,[sp, #0x30] */
            tmp_x9 = tmp_sp; /* mov x9,sp */
            *(u64 *)(tmp_x9) = tmp_x8; /* str x8,[x9] */
            tmp_x0 = 0x100000000; /* adrp x0,0x100000000 */
            tmp_x0 = tmp_x0 + 4054; /* add x0,x0,#0xfd6 */
            call_0x100000fa0(tmp_x0); /* bl 0x100000fa0; args refined from same-block evidence */
            /* block 0x1000007e8 */
            /* branch to 0x1000007ec */ /* b 0x1000007ec */
        }
        /* block 0x1000007ec */
        /* branch to 0x1000007f0 */ /* b 0x1000007f0 */
    }
    /* block 0x1000007f0 */
    tmp_w8 = stack_48; /* ldrb w8,[sp, #0x30] */
    stack_20 = tmp_w8; /* str w8,[sp, #0x14] */
    tmp_x9 = stack_m24; /* ldur x9,[x29, #-0x18] */
    tmp_x8 = 0x100004000; /* adrp x8,0x100004000 */
    tmp_x8 = *(u64 *)(tmp_x8 + 8); /* ldr x8,[x8, #0x8] */
    tmp_x8 = *(u64 *)(tmp_x8); /* ldr x8,[x8] */
    tmp_x8 = tmp_x8 - tmp_x9; /* subs x8,x8,x9; flags updated */
    /* conditional branch b.eq -> 0x100000818 */
    /* block 0x100000818 */
    tmp_w0 = stack_20; /* ldr w0,[sp, #0x14] */
    tmp_fp = stack_336; /* ldp x29,x30,[sp, #0x150] */
    tmp_lr = stack_344; /* paired load second register inferred offset +8 */
    tmp_x28 = stack_320; /* ldp x28,x27,[sp, #0x140] */
    tmp_x27 = stack_328; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 352; /* add sp,sp,#0x160 */
    return tmp_w0; /* return value from w0 before ret */
    /* block 0x100000810 */
    /* branch to 0x100000814 */ /* b 0x100000814 */
    /* block 0x100000814 */
    call_0x100000f94(); /* bl 0x100000f94 */

}

uint64_t recursive_sum(uint64_t arg1, uint64_t arg2, uint64_t arg_30h)
{
    /* Entry: 0x10000082c */
    /* Body status: unstructured */
    /* 14 basic block(s), 52 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* ABI argument bindings: */
    /*   ? => param 0 (stack_save_restore) */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[4, 8, 12, 16], sizes=[4] */
    /*   base=x8, kind=array_like, offsets=[0, 4, 8], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u32 stack_m4 = 0;
    u64 stack_4 = 0;
    u64 stack_8 = 0;
    u32 stack_12 = 0;
    u64 stack_16 = 0;
    u64 stack_32 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: switch_candidate */
    {
        /* block 0x10000082c */
        tmp_sp = tmp_sp - 48; /* sub sp, sp, 0x30 */
        stack_32 = tmp_fp; /* stp x29, x30, [sp + var_20h] */
        stack_40 = tmp_lr; /* paired store second register inferred offset +8 */
        tmp_fp = tmp_sp + 32; /* add x29, sp, 0x20 */
        stack_16 = tmp_x0; /* str x0, [sp + var_10h] */
        stack_12 = tmp_w1; /* str w1, [sp + var_ch] */
        arg0 = stack_16; /* ldr x8, [sp + var_10h] */
        /* cbnz arg0 -> 0x100000854 */
        /* block 0x100000848 */
        /* branch to 0x10000084c */ /* b 0x10000084c */
        /* block 0x10000084c */
        stack_m4 = 0; /* stur wzr, [x29, -4] */
        /* branch to 0x1000008ec */ /* b 0x1000008ec */
        /* block 0x100000854 */
        arg0 = stack_12; /* ldr w8, [sp + var_ch] */
        arg0 = arg0 - 0; /* subs w8, w8, 0; flags updated */
        /* conditional branch b.gt -> 0x100000874 */
        /* block 0x100000860 */
        /* branch to 0x100000864 */ /* b 0x100000864 */
        /* block 0x100000864 */
        arg0 = stack_16; /* ldr x8, [sp + var_10h] */
        arg0 = *(u32 *)(arg0); /* ldr w8, [x8] */
        stack_m4 = arg0; /* stur w8, [x29, -4] */
        /* branch to 0x1000008ec */ /* b 0x1000008ec */
        /* block 0x100000874 */
        arg0 = stack_16; /* ldr x8, [sp + var_10h] */
        arg0 = *(u32 *)(arg0); /* ldr w8, [x8] */
        stack_8 = arg0; /* str w8, [sp + var_8h] */
        arg0 = stack_16; /* ldr x8, [sp + var_10h] */
        arg0 = *(u32 *)(arg0 + 4); /* ldr w8, [x8, 4] */
        /* tbz arg0 bit 2 -> 0x1000008a0 */
        /* block 0x10000088c */
        /* branch to 0x100000890 */ /* b 0x100000890 */
        /* block 0x100000890 */
        arg0 = stack_8; /* ldr w8, [sp + var_8h] */
        arg0 = arg0 + 7; /* add w8, w8, 7 */
        stack_8 = arg0; /* str w8, [sp + var_8h] */
        /* branch to 0x1000008a0 */ /* b 0x1000008a0 */
        /* block 0x1000008a0 */
        arg0 = stack_16; /* ldr x8, [sp + var_10h] */
        arg0 = *(u32 *)(arg0 + 4); /* ldr w8, [x8, 4] */
        /* tbnz arg0 bit 5 -> 0x1000008c0 */
        /* block 0x1000008ac */
        /* branch to 0x1000008b0 */ /* b 0x1000008b0 */
        /* block 0x1000008b0 */
        arg0 = stack_8; /* ldr w8, [sp + var_8h] */
        arg0 = arg0 - 3; /* subs w8, w8, 3; flags updated */
        stack_8 = arg0; /* str w8, [sp + var_8h] */
        /* branch to 0x1000008c0 */ /* b 0x1000008c0 */
        /* block 0x1000008c0 */
        arg0 = stack_8; /* ldr w8, [sp + var_8h] */
        stack_4 = arg0; /* str w8, [sp + var_4h] */
        arg0 = stack_16; /* ldr x8, [sp + var_10h] */
        tmp_x0 = *(u64 *)(arg0 + 8); /* ldr x0, [x8, 8] */
        arg0 = stack_12; /* ldr w8, [sp + var_ch] */
        tmp_w1 = arg0 - 1; /* subs w1, w8, 1; flags updated */
        call_0x10000082c(tmp_x0, tmp_w1); /* bl sym._recursive_sum; args refined from same-block evidence */
        arg0 = stack_4; /* ldr w8, [sp + var_4h] */
        arg0 = arg0 + tmp_w0; /* add w8, w8, w0 */
        stack_m4 = arg0; /* stur w8, [x29, -4] */
        /* branch to 0x1000008ec */ /* b 0x1000008ec */
        /* block 0x1000008ec */
        tmp_w0 = stack_m4; /* ldur w0, [x29, -4] */
        tmp_fp = stack_32; /* ldp x29, x30, [sp + var_20h] */
        tmp_lr = stack_40; /* paired load second register inferred offset +8 */
        tmp_sp = tmp_sp + 48; /* add sp, sp, 0x30 */
        return tmp_w0; /* return value from w0 before ret */
    }
    /* unstructured region end */

}

uint64_t cfg_pressure(void)
{
    /* Entry: 0x1000008b8 */
    /* Body status: structured */
    /* 3 basic block(s), 13 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[4, 8, 12, 16], sizes=[4, 8] */
    /*   base=x8, kind=pointer_like, offsets=[8], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u32 tmp_w8 = 0;
    u32 stack_m4 = 0;
    u32 stack_4 = 0;
    u32 stack_8 = 0;
    u32 stack_12 = 0;
    u64 stack_16 = 0;

    /* Control flow structure: */
    /* block 0x1000008b8 */
    stack_8 = tmp_w8; /* str w8,[sp, #0x8] */
    /* branch to 0x1000008c0 */ /* b 0x1000008c0 */
    /* block 0x1000008c0 */
    tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
    stack_4 = tmp_w8; /* str w8,[sp, #0x4] */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x0 = *(u64 *)(tmp_x8 + 8); /* ldr x0,[x8, #0x8] */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    tmp_w1 = tmp_w8 - 1; /* subs w1,w8,#0x1; flags updated */
    call_0x10000082c(tmp_x0, tmp_w1); /* bl 0x10000082c; args refined from same-block evidence */
    /* block 0x1000008dc */
    tmp_w8 = stack_4; /* ldr w8,[sp, #0x4] */
    tmp_w8 = tmp_w8 + tmp_w0; /* add w8,w8,w0 */
    stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
    /* branch to 0x1000008ec */ /* b 0x1000008ec */

    /* return value unknown */
    return 0;
}

uint64_t FUN_1000008ec(void)
{
    /* Entry: 0x1000008ec */
    /* Body status: partially_structured */
    /* 1 basic block(s), 4 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u32 stack_m4 = 0;
    u64 stack_32 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* block 0x1000008ec */
    tmp_w0 = stack_m4; /* ldur w0,[x29, #-0x4] */
    tmp_fp = stack_32; /* ldp x29,x30,[sp, #0x20] */
    tmp_lr = stack_40; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 48; /* add sp,sp,#0x30 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t even_path(uint64_t arg1, uint64_t arg_20h)
{
    /* Entry: 0x1000008fc */
    /* Body status: structured */
    /* 10 basic block(s), 31 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=scalar, offsets=[8], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w8 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u32 stack_m4 = 0;
    u32 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;

    /* Control flow structure: */
    /* loop kind: while_like */
    /* loop header: 0x1000008fc */
    /* loop exits: ['0x100000918', '0x100000930', '0x10000095c'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.gt at 0x100000914 after subs at 0x100000910; target 0x100000928")) {
        /* block 0x1000008fc */
        tmp_sp = tmp_sp - 32; /* sub sp,sp,#0x20 */
        stack_16 = tmp_fp; /* stp x29,x30,[sp, #0x10] */
        stack_24 = tmp_lr; /* paired store second register inferred offset +8 */
        tmp_fp = tmp_sp + 16; /* add x29,sp,#0x10 */
        stack_8 = tmp_w0; /* str w0,[sp, #0x8] */
        tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
        tmp_w8 = tmp_w8 - 0; /* subs w8,w8,#0x0; flags updated */
        /* conditional branch b.gt -> 0x100000928 */
        /* block 0x100000928 */
        tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
        /* tbz tmp_w8 bit 0 -> 0x100000950 */
        /* block 0x100000950 */
        tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
        tmp_w0 = tmp_w8 - 2; /* subs w0,w8,#0x2; flags updated */
        call_0x1000008fc(tmp_w0); /* bl 0x1000008fc; args refined from same-block evidence */
    }
    /* block 0x10000095c */
    tmp_w8 = tmp_w0 + 2; /* add w8,w0,#0x2 */
    stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
    /* branch to 0x100000968 */ /* b 0x100000968 */
    /* block 0x100000930 */
    /* branch to 0x100000934 */ /* b 0x100000934 */
    /* block 0x100000934 */
    tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
    tmp_w0 = tmp_w8 - 1; /* subs w0,w8,#0x1; flags updated */
    call_0x100000ed0(tmp_w0); /* bl 0x100000ed0; args refined from same-block evidence */
    /* block 0x100000940 */
    tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
    tmp_w8 = tmp_w0 + tmp_w8; /* add w8,w0,w8 */
    stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
    /* branch to 0x100000968 */ /* b 0x100000968 */
    /* block 0x100000918 */
    /* branch to 0x10000091c */ /* b 0x10000091c */
    /* block 0x10000091c */
    tmp_w8 = 1; /* mov w8,#0x1 */
    stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
    /* branch to 0x100000968 */ /* b 0x100000968 */
    /* block 0x100000968 */
    tmp_w0 = stack_m4; /* ldur w0,[x29, #-0x4] */
    tmp_fp = stack_16; /* ldp x29,x30,[sp, #0x10] */
    tmp_lr = stack_24; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 32; /* add sp,sp,#0x20 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t table_walk(uint64_t arg1, uint64_t arg2, uint64_t arg_40h)
{
    /* Entry: 0x100000978 */
    /* Body status: unstructured */
    /* 30 basic block(s), 103 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[8, 15, 16, 20, 24], sizes=[1, 2, 4] */
    /*   base=x8, kind=record_like, offsets=[0, 8], sizes=[1, 4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u32 stack_m4 = 0;
    u64 stack_m16 = 0;
    u32 stack_m20 = 0;
    u32 stack_8 = 0;
    u32 stack_15 = 0;
    u32 stack_16 = 0;
    u32 stack_20 = 0;
    u32 stack_24 = 0;
    u64 stack_48 = 0;
    u64 stack_56 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: switch_candidate */
    {
        /* block 0x100000978 */
        tmp_sp = tmp_sp - 64; /* sub sp,sp,#0x40 */
        stack_48 = tmp_fp; /* stp x29,x30,[sp, #0x30] */
        stack_56 = tmp_lr; /* paired store second register inferred offset +8 */
        tmp_fp = tmp_sp + 48; /* add x29,sp,#0x30 */
        stack_m16 = tmp_x0; /* stur x0,[x29, #-0x10] */
        stack_m20 = tmp_w1; /* stur w1,[x29, #-0x14] */
        tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
        /* cbnz tmp_x8 -> 0x1000009a4 */
        /* block 0x100000994 */
        /* branch to 0x100000998 */ /* b 0x100000998 */
        /* block 0x100000998 */
        tmp_w8 = 0xffffff9c; /* mov w8,#0xffffff9c */
        stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
        /* branch to 0x100000b04 */ /* b 0x100000b04 */
        /* block 0x1000009a4 */
        tmp_w8 = stack_m20; /* ldur w8,[x29, #-0x14] */
        /* tbz tmp_w8 bit 31 -> 0x1000009bc */
        /* block 0x1000009ac */
        /* branch to 0x1000009b0 */ /* b 0x1000009b0 */
        /* block 0x1000009b0 */
        tmp_w8 = 0xffffff38; /* mov w8,#0xffffff38 */
        stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
        /* branch to 0x100000b04 */ /* b 0x100000b04 */
        /* block 0x1000009bc */
        stack_24 = 0; /* str wzr,[sp, #0x18] */
        tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
        tmp_w8 = *(u32 *)(tmp_x8 + 8); /* ldr w8,[x8, #0x8] */
        stack_20 = tmp_w8; /* str w8,[sp, #0x14] */
        stack_16 = 0; /* str wzr,[sp, #0x10] */
        /* branch to 0x1000009d4 */ /* b 0x1000009d4 */
        /* block 0x1000009d4 */
        tmp_w9 = stack_16; /* ldr w9,[sp, #0x10] */
        tmp_w10 = stack_m20; /* ldur w10,[x29, #-0x14] */
        tmp_w8 = 0; /* mov w8,#0x0 */
        tmp_w9 = tmp_w9 - tmp_w10; /* subs w9,w9,w10; flags updated */
        stack_8 = tmp_w8; /* str w8,[sp, #0x8] */
        /* conditional branch b.ge -> 0x100000a04 */
        /* block 0x100000a30 */
        /* branch to 0x100000a34 */ /* b 0x100000a34 */
        /* block 0x100000a34 */
        tmp_w9 = stack_16; /* ldr w9,[sp, #0x10] */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
        stack_24 = tmp_w8; /* str w8,[sp, #0x18] */
        /* branch to 0x100000adc */ /* b 0x100000adc */
        /* block 0x100000a48 */
        tmp_w8 = stack_15; /* ldrb w8,[sp, #0xf] */
        /* tbz tmp_w8 bit 0 -> 0x100000a68 */
        /* block 0x100000a84 */
        /* branch to 0x100000a88 */ /* b 0x100000a88 */
        /* block 0x100000a88 */
        tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
        tmp_w9 = 3; /* mov w9,#0x3 */
        tmp_w9 = tmp_w8 * tmp_w9; /* mul w9,w8,w9 */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8,w8,w9 */
        stack_24 = tmp_w8; /* str w8,[sp, #0x18] */
        /* branch to 0x100000aa4 */ /* b 0x100000aa4 */
        /* block 0x100000aa4 */
        tmp_w8 = stack_20; /* ldr w8,[sp, #0x14] */
        tmp_w9 = stack_15; /* ldrb w9,[sp, #0xf] */
        tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8,w8,w9 */
        tmp_w9 = stack_16; /* ldr w9,[sp, #0x10] */
        tmp_w0 = tmp_w8 ^ tmp_w9; /* eor w0,w8,w9 */
        call_0x100000f50(tmp_w0); /* bl 0x100000f50; args refined from same-block evidence */
        /* block 0x100000abc */
        stack_20 = tmp_w0; /* str w0,[sp, #0x14] */
        tmp_w8 = stack_20; /* ldrh w8,[sp, #0x14] */
        tmp_w9 = 48879; /* mov w9,#0xbeef */
        tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
        /* conditional branch b.ne -> 0x100000ad8 */
        /* block 0x100000ad0 */
        /* branch to 0x100000ad4 */ /* b 0x100000ad4 */
        /* block 0x100000ad4 */
        /* branch to 0x100000aec */ /* b 0x100000aec */
        /* block 0x100000ad8 */
        /* branch to 0x100000adc */ /* b 0x100000adc */
        /* block 0x100000adc */
        tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_16 = tmp_w8; /* str w8,[sp, #0x10] */
        /* branch to 0x1000009d4 */ /* b 0x1000009d4 */
        /* block 0x100000aec */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w9 = stack_20; /* ldr w9,[sp, #0x14] */
        tmp_w9 = tmp_w9 & 1023; /* and w9,w9,#0x3ff */
        tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
        stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
        /* branch to 0x100000b04 */ /* b 0x100000b04 */
        /* block 0x100000b04 */
        tmp_w0 = stack_m4; /* ldur w0,[x29, #-0x4] */
        tmp_fp = stack_48; /* ldp x29,x30,[sp, #0x30] */
        tmp_lr = stack_56; /* paired load second register inferred offset +8 */
        tmp_sp = tmp_sp + 64; /* add sp,sp,#0x40 */
        return tmp_w0; /* return value from w0 before ret */
    }
    /* unstructured region end */

}

uint64_t apply_callback(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg4, uint64_t arg_50h)
{
    /* Entry: 0x100000b14 */
    /* Body status: unstructured */
    /* 22 basic block(s), 82 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[12, 16, 24, 28, 32], sizes=[4] */
    /*   base=x8, kind=scalar, offsets=[0], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u32 tmp_w3 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u32 stack_m4 = 0;
    u64 stack_m16 = 0;
    u64 stack_m24 = 0;
    u32 stack_12 = 0;
    u64 stack_16 = 0;
    u32 stack_24 = 0;
    u32 stack_28 = 0;
    u64 stack_32 = 0;
    u64 stack_64 = 0;
    u64 stack_72 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: switch_candidate */
    {
        /* block 0x100000b14 */
        tmp_sp = tmp_sp - 80; /* sub sp, sp, 0x50 */
        stack_64 = tmp_fp; /* stp x29, x30, [sp + var_40h] */
        stack_72 = tmp_lr; /* paired store second register inferred offset +8 */
        tmp_fp = tmp_sp + 64; /* add x29, sp, 0x40 */
        stack_m16 = tmp_x0; /* stur x0, [x29, -0x10] */
        stack_m24 = tmp_x1; /* stur x1, [x29, -0x18] */
        stack_32 = tmp_x2; /* str x2, [sp + var_20h] */
        stack_28 = tmp_w3; /* str w3, [sp + var_1ch] */
        tmp_x8 = stack_m16; /* ldur x8, [x29, -0x10] */
        /* cbz tmp_x8 -> 0x100000b48 */
        /* block 0x100000b38 */
        /* branch to 0x100000b3c */ /* b 0x100000b3c */
        /* block 0x100000b3c */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        /* cbnz tmp_x8 -> 0x100000b54 */
        /* block 0x100000b44 */
        /* branch to 0x100000b48 */ /* b 0x100000b48 */
        /* block 0x100000b48 */
        tmp_w8 = -1; /* mov w8, -1 */
        stack_m4 = tmp_w8; /* stur w8, [x29, -4] */
        /* branch to 0x100000c4c */ /* b 0x100000c4c */
        /* block 0x100000b54 */
        stack_24 = 0; /* str wzr, [sp + var_18h] */
        stack_16 = 0; /* str xzr, [sp + var_10h] */
        /* branch to 0x100000b60 */ /* b 0x100000b60 */
        /* block 0x100000b60 */
        tmp_x8 = stack_16; /* ldr x8, [sp + var_10h] */
        tmp_x9 = stack_32; /* ldr x9, [sp + var_20h] */
        tmp_x8 = tmp_x8 - tmp_x9; /* subs x8, x8, x9; flags updated */
        /* conditional branch b.hs -> 0x100000c40 */
        /* block 0x100000b94 */
        /* branch to 0x100000b98 */ /* b 0x100000b98 */
        /* block 0x100000b98 */
        tmp_x8 = stack_m16; /* ldur x8, [x29, -0x10] */
        tmp_w0 = stack_12; /* ldr w0, [sp + var_ch] */
        tmp_w1 = stack_28; /* ldr w1, [sp + var_1ch] */
        /* indirect call through tmp_x8 with args: tmp_w0, tmp_w1 */ /* blr x8 */
        tmp_w8 = stack_24; /* ldr w8, [sp + var_18h] */
        tmp_w8 = tmp_w8 + tmp_w0; /* add w8, w8, w0 */
        stack_24 = tmp_w8; /* str w8, [sp + var_18h] */
        /* branch to 0x100000be4 */ /* b 0x100000be4 */
        /* block 0x100000bb8 */
        tmp_x8 = stack_m16; /* ldur x8, [x29, -0x10] */
        tmp_w9 = stack_12; /* ldr w9, [sp + var_ch] */
        tmp_w0 = tmp_w9 + 1; /* add w0, w9, 1 */
        tmp_w9 = stack_28; /* ldr w9, [sp + var_1ch] */
        tmp_x10 = stack_16; /* ldr x10, [sp + var_10h] */
        tmp_w1 = tmp_w9 ^ tmp_w10; /* eor w1, w9, w10 */
        /* indirect call through tmp_x8 with args: tmp_w0, tmp_w1 */ /* blr x8 */
        tmp_w8 = stack_24; /* ldr w8, [sp + var_18h] */
        tmp_w8 = tmp_w8 - tmp_w0; /* subs w8, w8, w0; flags updated */
        stack_24 = tmp_w8; /* str w8, [sp + var_18h] */
        /* branch to 0x100000be4 */ /* b 0x100000be4 */
        /* block 0x100000be4 */
        tmp_w8 = stack_24; /* ldr w8, [sp + var_18h] */
        tmp_w9 = 10000; /* mov w9, 0x2710 */
        tmp_w8 = tmp_w8 - tmp_w9; /* subs w8, w8, w9; flags updated */
        /* conditional branch b.le -> 0x100000c04 */
        /* block 0x100000bf4 */
        /* branch to 0x100000bf8 */ /* b 0x100000bf8 */
        /* block 0x100000bf8 */
        tmp_w8 = stack_24; /* ldr w8, [sp + var_18h] */
        stack_m4 = tmp_w8; /* stur w8, [x29, -4] */
        /* branch to 0x100000c4c */ /* b 0x100000c4c */
        /* block 0x100000c04 */
        tmp_w8 = stack_24; /* ldr w8, [sp + var_18h] */
        tmp_w9 = -10000; /* mov w9, -0x2710 */
        tmp_w8 = tmp_w8 - tmp_w9; /* subs w8, w8, w9; flags updated */
        /* conditional branch b.ge -> 0x100000c2c */
        /* block 0x100000c14 */
        /* branch to 0x100000c18 */ /* b 0x100000c18 */
        /* block 0x100000c18 */
        tmp_w8 = stack_24; /* ldr w8, [sp + var_18h] */
        tmp_w9 = 2; /* mov w9, 2 */
        tmp_w8 = ((i32)tmp_w8) / ((i32)tmp_w9); /* sdiv w8, w8, w9 */
        stack_m4 = tmp_w8; /* stur w8, [x29, -4] */
        /* branch to 0x100000c4c */ /* b 0x100000c4c */
        /* block 0x100000c2c */
        /* branch to 0x100000c30 */ /* b 0x100000c30 */
        /* block 0x100000c30 */
        tmp_x8 = stack_16; /* ldr x8, [sp + var_10h] */
        tmp_x8 = tmp_x8 + 1; /* add x8, x8, 1 */
        stack_16 = tmp_x8; /* str x8, [sp + var_10h] */
        /* branch to 0x100000b60 */ /* b 0x100000b60 */
        /* block 0x100000c40 */
        tmp_w8 = stack_24; /* ldr w8, [sp + var_18h] */
        stack_m4 = tmp_w8; /* stur w8, [x29, -4] */
        /* branch to 0x100000c4c */ /* b 0x100000c4c */
        /* block 0x100000c4c */
        tmp_w0 = stack_m4; /* ldur w0, [x29, -4] */
        tmp_fp = stack_64; /* ldp x29, x30, [sp + var_40h] */
        tmp_lr = stack_72; /* paired load second register inferred offset +8 */
        tmp_sp = tmp_sp + 80; /* add sp, sp, 0x50 */
        return tmp_w0; /* return value from w0 before ret */
    }
    /* unstructured region end */

}

uint64_t indirect_pressure(void)
{
    /* Entry: 0x100000b7c */
    /* Body status: unstructured */
    /* 15 basic block(s), 52 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[12, 16, 24, 28], sizes=[4, 8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u32 stack_m4 = 0;
    u64 stack_m16 = 0;
    u32 stack_12 = 0;
    u64 stack_16 = 0;
    u32 stack_24 = 0;
    u32 stack_28 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: fragmented_loop_body */
    {
        /* block 0x100000b7c */
        tmp_w8 = *(u32 *)(tmp_x8 + (tmp_x9 << 2)); /* ldr w8,[x8, x9, LSL #0x2] */
        stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
        tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
        tmp_w9 = stack_28; /* ldr w9,[sp, #0x1c] */
        tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
        /* conditional branch b.ls -> 0x100000bb8 */
        /* block 0x100000b94 */
        /* branch to 0x100000b98 */ /* b 0x100000b98 */
        /* block 0x100000b98 */
        tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
        tmp_w0 = stack_12; /* ldr w0,[sp, #0xc] */
        tmp_w1 = stack_28; /* ldr w1,[sp, #0x1c] */
        /* indirect call through tmp_x8 with args: tmp_w0, tmp_w1 */ /* blr x8 */
        /* block 0x100000ba8 */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w8 = tmp_w8 + tmp_w0; /* add w8,w8,w0 */
        stack_24 = tmp_w8; /* str w8,[sp, #0x18] */
        /* branch to 0x100000be4 */ /* b 0x100000be4 */
        /* block 0x100000bb8 */
        tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
        tmp_w9 = stack_12; /* ldr w9,[sp, #0xc] */
        tmp_w0 = tmp_w9 + 1; /* add w0,w9,#0x1 */
        tmp_w9 = stack_28; /* ldr w9,[sp, #0x1c] */
        tmp_x10 = stack_16; /* ldr x10,[sp, #0x10] */
        tmp_w1 = tmp_w9 ^ tmp_w10; /* eor w1,w9,w10 */
        /* indirect call through tmp_x8 with args: tmp_w0, tmp_w1 */ /* blr x8 */
        /* block 0x100000bd4 */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w8 = tmp_w8 - tmp_w0; /* subs w8,w8,w0; flags updated */
        stack_24 = tmp_w8; /* str w8,[sp, #0x18] */
        /* branch to 0x100000be4 */ /* b 0x100000be4 */
        /* block 0x100000be4 */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w9 = 10000; /* mov w9,#0x2710 */
        tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
        /* conditional branch b.le -> 0x100000c04 */
        /* block 0x100000bf4 */
        /* branch to 0x100000bf8 */ /* b 0x100000bf8 */
        /* block 0x100000bf8 */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
        /* branch to 0x100000c4c */ /* b 0x100000c4c */
        /* block 0x100000c04 */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w9 = 0xffffd8f0; /* mov w9,#0xffffd8f0 */
        tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
        /* conditional branch b.ge -> 0x100000c2c */
        /* block 0x100000c14 */
        /* branch to 0x100000c18 */ /* b 0x100000c18 */
        /* block 0x100000c18 */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w9 = 2; /* mov w9,#0x2 */
        tmp_w8 = ((i32)tmp_w8) / ((i32)tmp_w9); /* sdiv w8,w8,w9 */
        stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
        /* branch to 0x100000c4c */ /* b 0x100000c4c */
        /* block 0x100000c2c */
        /* branch to 0x100000c30 */ /* b 0x100000c30 */
        /* block 0x100000c30 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x8 = tmp_x8 + 1; /* add x8,x8,#0x1 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x100000b60 */ /* b 0x100000b60 */
        /* block 0x100000c40 */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
        /* branch to 0x100000c4c */ /* b 0x100000c4c */
    }
    /* unstructured region end */

    /* return value unknown */
    return 0;
}

uint64_t FUN_100000c4c(void)
{
    /* Entry: 0x100000c4c */
    /* Body status: partially_structured */
    /* 1 basic block(s), 4 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u32 stack_m4 = 0;
    u64 stack_64 = 0;
    u64 stack_72 = 0;

    /* Control flow structure: */
    /* block 0x100000c4c */
    tmp_w0 = stack_m4; /* ldur w0,[x29, #-0x4] */
    tmp_fp = stack_64; /* ldp x29,x30,[sp, #0x40] */
    tmp_lr = stack_72; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 80; /* add sp,sp,#0x50 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t classify_value(uint64_t arg1, uint64_t arg2, uint64_t arg_10h)
{
    /* Entry: 0x100000c5c */
    /* Body status: structured */
    /* 26 basic block(s), 78 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[0, 4, 8, 12], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 stack_0 = 0;
    u32 stack_4 = 0;
    u32 stack_8 = 0;
    u32 stack_12 = 0;

    /* Control flow structure: */
    /* block 0x100000c5c */
    tmp_sp = tmp_sp - 16; /* sub sp, sp, 0x10 */
    stack_12 = tmp_w0; /* str w0, [sp + var_ch] */
    stack_8 = tmp_w1; /* str w1, [sp + var_8h] */
    stack_4 = 0; /* str wzr, [sp + var_4h] */
    tmp_w8 = stack_12; /* ldr w8, [sp + var_ch] */
    tmp_w8 = tmp_w8 & 7; /* and w8, w8, 7 */
    stack_0 = tmp_w8; /* str w8, [sp] */
    /* cbz tmp_w8 -> 0x100000cb4 */
    /* block 0x100000cb4 */
    tmp_w8 = stack_12; /* ldr w8, [sp + var_ch] */
    tmp_w8 = tmp_w8 + 10; /* add w8, w8, 0xa */
    stack_4 = tmp_w8; /* str w8, [sp + var_4h] */
    /* branch to 0x100000d10 */ /* b 0x100000d10 */
    /* block 0x100000c7c */
    /* branch to 0x100000c80 */ /* b 0x100000c80 */
    /* block 0x100000c80 */
    tmp_w8 = stack_0; /* ldr w8, [sp] */
    tmp_w8 = tmp_w8 - 1; /* subs w8, w8, 1; flags updated */
    /* conditional branch b.eq -> 0x100000cc4 */
    /* block 0x100000cc4 */
    tmp_w8 = stack_12; /* ldr w8, [sp + var_ch] */
    tmp_w8 = tmp_w8 - 11; /* subs w8, w8, 0xb; flags updated */
    stack_4 = tmp_w8; /* str w8, [sp + var_4h] */
    /* branch to 0x100000d10 */ /* b 0x100000d10 */
    /* block 0x100000c8c */
    /* branch to 0x100000c90 */ /* b 0x100000c90 */
    /* block 0x100000c90 */
    tmp_w8 = stack_0; /* ldr w8, [sp] */
    tmp_w8 = tmp_w8 - 2; /* subs w8, w8, 2; flags updated */
    tmp_w8 = tmp_w8 - 1; /* subs w8, w8, 1; flags updated */
    /* conditional branch b.ls -> 0x100000cd4 */
    /* block 0x100000cd4 */
    tmp_w8 = stack_12; /* ldr w8, [sp + var_ch] */
    tmp_w9 = 85; /* mov w9, 0x55 */
    tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8, w8, w9 */
    stack_4 = tmp_w8; /* str w8, [sp + var_4h] */
    /* branch to 0x100000d10 */ /* b 0x100000d10 */
    /* block 0x100000ca0 */
    /* branch to 0x100000ca4 */ /* b 0x100000ca4 */
    /* block 0x100000ca4 */
    tmp_w8 = stack_0; /* ldr w8, [sp] */
    tmp_w8 = tmp_w8 - 4; /* subs w8, w8, 4; flags updated */
    /* conditional branch b.eq -> 0x100000ce8 */
    /* block 0x100000ce8 */
    tmp_w9 = stack_12; /* ldr w9, [sp + var_ch] */
    tmp_w8 = 0; /* mov w8, 0 */
    tmp_w8 = tmp_w8 - tmp_w9; /* subs w8, w8, w9; flags updated */
    stack_4 = tmp_w8; /* str w8, [sp + var_4h] */
    /* branch to 0x100000d10 */ /* b 0x100000d10 */
    /* block 0x100000cb0 */
    /* branch to 0x100000cfc */ /* b 0x100000cfc */
    /* block 0x100000cfc */
    tmp_w8 = stack_12; /* ldr w8, [sp + var_ch] */
    tmp_w9 = 3; /* mov w9, 3 */
    tmp_w8 = tmp_w8 * tmp_w9; /* mul w8, w8, w9 */
    stack_4 = tmp_w8; /* str w8, [sp + var_4h] */
    /* branch to 0x100000d10 */ /* b 0x100000d10 */
    /* if condition block: 0x100000d10 */
    /* merge block: 0x100000d2c */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbnz w8 at 0x100000d14 targeting 0x100000d2c")) {
        /* block 0x100000d18 */
        /* branch to 0x100000d1c */ /* b 0x100000d1c */
        /* block 0x100000d1c */
        tmp_w8 = stack_4; /* ldr w8, [sp + var_4h] */
        tmp_w8 = tmp_w8 + 100; /* add w8, w8, 0x64 */
        stack_4 = tmp_w8; /* str w8, [sp + var_4h] */
        /* branch to 0x100000d2c */ /* b 0x100000d2c */
    }
    /* block 0x100000d2c */
    tmp_w8 = stack_8; /* ldr w8, [sp + var_8h] */
    /* cbz tmp_w8 -> 0x100000d48 */
    /* block 0x100000d34 */
    /* branch to 0x100000d38 */ /* b 0x100000d38 */
    /* block 0x100000d38 */
    tmp_w8 = stack_4; /* ldr w8, [sp + var_4h] */
    tmp_w8 = tmp_w8 - 9; /* subs w8, w8, 9; flags updated */
    stack_4 = tmp_w8; /* str w8, [sp + var_4h] */
    /* branch to 0x100000d48 */ /* b 0x100000d48 */
    /* if condition block: 0x100000d48 */
    /* merge block: 0x100000d6c */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.hs at 0x100000d54 after subs at 0x100000d50; target 0x100000d6c")) {
        /* block 0x100000d58 */
        /* branch to 0x100000d5c */ /* b 0x100000d5c */
        /* block 0x100000d5c */
        tmp_w8 = stack_4; /* ldr w8, [sp + var_4h] */
        tmp_w8 = tmp_w8 + 5; /* add w8, w8, 5 */
        stack_4 = tmp_w8; /* str w8, [sp + var_4h] */
        /* branch to 0x100000d6c */ /* b 0x100000d6c */
    }
    /* block 0x100000d6c */
    tmp_w8 = stack_8; /* ldr w8, [sp + var_8h] */
    /* tbz tmp_w8 bit 31 -> 0x100000d88 */
    /* block 0x100000d74 */
    /* branch to 0x100000d78 */ /* b 0x100000d78 */
    /* block 0x100000d78 */
    tmp_w8 = stack_4; /* ldr w8, [sp + var_4h] */
    tmp_w8 = tmp_w8 ^ 127; /* eor w8, w8, 0x7f */
    stack_4 = tmp_w8; /* str w8, [sp + var_4h] */
    /* branch to 0x100000d88 */ /* b 0x100000d88 */
    /* block 0x100000d88 */
    tmp_w0 = stack_4; /* ldr w0, [sp + var_4h] */
    tmp_sp = tmp_sp + 16; /* add sp, sp, 0x10 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t byte_halfword_pressure(void)
{
    /* Entry: 0x100000d00 */
    /* Body status: structured */
    /* 14 basic block(s), 37 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[4, 8, 12], sizes=[1, 4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 stack_4 = 0;
    u32 stack_8 = 0;
    u32 stack_12 = 0;

    /* Control flow structure: */
    /* block 0x100000d00 */
    tmp_w9 = 3; /* mov w9,#0x3 */
    tmp_w8 = tmp_w8 * tmp_w9; /* mul w8,w8,w9 */
    stack_4 = tmp_w8; /* str w8,[sp, #0x4] */
    /* branch to 0x100000d10 */ /* b 0x100000d10 */
    /* block 0x100000d10 */
    tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
    /* cbnz tmp_w8 -> 0x100000d2c */
    /* block 0x100000d18 */
    /* branch to 0x100000d1c */ /* b 0x100000d1c */
    /* block 0x100000d1c */
    tmp_w8 = stack_4; /* ldr w8,[sp, #0x4] */
    tmp_w8 = tmp_w8 + 100; /* add w8,w8,#0x64 */
    stack_4 = tmp_w8; /* str w8,[sp, #0x4] */
    /* branch to 0x100000d2c */ /* b 0x100000d2c */
    /* if condition block: 0x100000d2c */
    /* merge block: 0x100000d48 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbz w8 at 0x100000d30 targeting 0x100000d48")) {
        /* block 0x100000d34 */
        /* branch to 0x100000d38 */ /* b 0x100000d38 */
        /* block 0x100000d38 */
        tmp_w8 = stack_4; /* ldr w8,[sp, #0x4] */
        tmp_w8 = tmp_w8 - 9; /* subs w8,w8,#0x9; flags updated */
        stack_4 = tmp_w8; /* str w8,[sp, #0x4] */
        /* branch to 0x100000d48 */ /* b 0x100000d48 */
    }
    /* block 0x100000d48 */
    tmp_w8 = stack_8; /* ldrb w8,[sp, #0x8] */
    tmp_w9 = stack_12; /* ldr w9,[sp, #0xc] */
    tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
    /* conditional branch b.cs -> 0x100000d6c */
    /* block 0x100000d58 */
    /* branch to 0x100000d5c */ /* b 0x100000d5c */
    /* block 0x100000d5c */
    tmp_w8 = stack_4; /* ldr w8,[sp, #0x4] */
    tmp_w8 = tmp_w8 + 5; /* add w8,w8,#0x5 */
    stack_4 = tmp_w8; /* str w8,[sp, #0x4] */
    /* branch to 0x100000d6c */ /* b 0x100000d6c */
    /* if condition block: 0x100000d6c */
    /* merge block: 0x100000d88 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: tbz w8 bit #0 at 0x100000d70 targeting 0x100000d88")) {
        /* block 0x100000d74 */
        /* branch to 0x100000d78 */ /* b 0x100000d78 */
        /* block 0x100000d78 */
        tmp_w8 = stack_4; /* ldr w8,[sp, #0x4] */
        tmp_w8 = tmp_w8 ^ 127; /* eor w8,w8,#0x7f */
        stack_4 = tmp_w8; /* str w8,[sp, #0x4] */
        /* branch to 0x100000d88 */ /* b 0x100000d88 */
    }
    /* block 0x100000d88 */
    tmp_w0 = stack_4; /* ldr w0,[sp, #0x4] */
    tmp_sp = tmp_sp + 16; /* add sp,sp,#0x10 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t pointer_churn(int32_t arg1, uint64_t arg2, uint64_t arg_40h)
{
    /* Entry: 0x100000d94 */
    /* Body status: structured */
    /* 21 basic block(s), 79 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* ABI argument bindings: */
    /*   ? => param 0 (stack_save_restore) */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[8, 15, 16, 24, 36, 40, 48, 60], sizes=[1, 4, 8] */
    /*   base=x8, kind=array_like, offsets=[0, 1], sizes=[1] */
    /*   base=x9, kind=array_like, offsets=[2, 3], sizes=[1] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x9 = 0;
    u32 tmp_w0 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;
    u64 stack_36 = 0;
    u64 stack_40 = 0;
    u64 stack_48 = 0;
    u32 stack_60 = 0;

    /* Control flow structure: */
    /* if/else condition block: 0x100000d94 */
    /* merge block: 0x100000ec4 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbnz x8 at 0x100000da4 targeting 0x100000db8; polarity inverted")) {
        /* block 0x100000da8 */
        /* branch to 0x100000dac */ /* b 0x100000dac */
        /* block 0x100000dac */
        arg0 = 0xfffffff7; /* mov w8,#0xfffffff7 */
        stack_60 = arg0; /* str w8,[sp, #0x3c] */
        /* branch to 0x100000ec4 */ /* b 0x100000ec4 */
    } else {
        /* block 0x100000db8 */
        stack_36 = 0; /* str wzr,[sp, #0x24] */
        arg0 = stack_48; /* ldr x8,[sp, #0x30] */
        stack_24 = arg0; /* str x8,[sp, #0x18] */
        arg0 = stack_48; /* ldr x8,[sp, #0x30] */
        tmp_x9 = stack_40; /* ldr x9,[sp, #0x28] */
        arg0 = arg0 + tmp_x9; /* add x8,x8,x9 */
        stack_16 = arg0; /* str x8,[sp, #0x10] */
        /* branch to 0x100000dd8 */ /* b 0x100000dd8 */
        /* loop kind: while_like */
        /* loop header: 0x100000dd8 */
        /* loop exits: ['0x100000eb8'] */
        while (HEPHAESTUS_UNKNOWN_COND("condition unknown: loop header 0x100000dd8")) {
            /* if condition block: 0x100000dd8 */
            /* merge block: 0x100000ea8 */
            if (HEPHAESTUS_UNKNOWN_COND("condition unknown: block 0x100000dd8")) {
                /* if condition block: 0x100000e44 */
                /* merge block: 0x100000ea4 */
                if (HEPHAESTUS_UNKNOWN_COND("condition unknown: block 0x100000e44")) {
                    /* block 0x100000e90 */
                    /* branch to 0x100000e94 */ /* b 0x100000e94 */
                    /* block 0x100000e94 */
                    arg0 = stack_36; /* ldr w8,[sp, #0x24] */
                    arg0 = arg0 + 100; /* add w8,w8,#0x64 */
                    stack_36 = arg0; /* str w8,[sp, #0x24] */
                    /* branch to 0x100000ea4 */ /* b 0x100000ea4 */
                }
                /* block 0x100000ea4 */
                /* branch to 0x100000ea8 */ /* b 0x100000ea8 */
            }
            /* block 0x100000ea8 */
            arg0 = stack_24; /* ldr x8,[sp, #0x18] */
            arg0 = arg0 + 1; /* add x8,x8,#0x1 */
            stack_24 = arg0; /* str x8,[sp, #0x18] */
            /* branch to 0x100000dd8 */ /* b 0x100000dd8 */
        }
        /* block 0x100000eb8 */
        arg0 = stack_36; /* ldr w8,[sp, #0x24] */
        stack_60 = arg0; /* str w8,[sp, #0x3c] */
        /* branch to 0x100000ec4 */ /* b 0x100000ec4 */
    }
    /* block 0x100000ec4 */
    tmp_w0 = stack_60; /* ldr w0,[sp, #0x3c] */
    tmp_sp = tmp_sp + 64; /* add sp,sp,#0x40 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t odd_path(uint64_t arg1, uint64_t arg_20h)
{
    /* Entry: 0x100000ed0 */
    /* Body status: structured */
    /* 10 basic block(s), 32 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=scalar, offsets=[8], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w8 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u32 stack_m4 = 0;
    u32 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;

    /* Control flow structure: */
    /* loop kind: while_like */
    /* loop header: 0x100000ed0 */
    /* loop exits: ['0x100000eec', '0x100000f08', '0x100000f34'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.gt at 0x100000ee8 after subs at 0x100000ee4; target 0x100000f00")) {
        /* block 0x100000ed0 */
        tmp_sp = tmp_sp - 32; /* sub sp,sp,#0x20 */
        stack_16 = tmp_fp; /* stp x29,x30,[sp, #0x10] */
        stack_24 = tmp_lr; /* paired store second register inferred offset +8 */
        tmp_fp = tmp_sp + 16; /* add x29,sp,#0x10 */
        stack_8 = tmp_w0; /* str w0,[sp, #0x8] */
        tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
        tmp_w8 = tmp_w8 - 1; /* subs w8,w8,#0x1; flags updated */
        /* conditional branch b.gt -> 0x100000f00 */
        /* block 0x100000f00 */
        tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
        /* tbz tmp_w8 bit 1 -> 0x100000f28 */
        /* block 0x100000f28 */
        tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
        tmp_w0 = tmp_w8 - 2; /* subs w0,w8,#0x2; flags updated */
        call_0x100000ed0(tmp_w0); /* bl 0x100000ed0; args refined from same-block evidence */
    }
    /* block 0x100000f34 */
    tmp_w8 = tmp_w0 + 1; /* add w8,w0,#0x1 */
    stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
    /* branch to 0x100000f40 */ /* b 0x100000f40 */
    /* block 0x100000f08 */
    /* branch to 0x100000f0c */ /* b 0x100000f0c */
    /* block 0x100000f0c */
    tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
    tmp_w0 = tmp_w8 - 1; /* subs w0,w8,#0x1; flags updated */
    call_0x1000008fc(tmp_w0); /* bl 0x1000008fc; args refined from same-block evidence */
    /* block 0x100000f18 */
    tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
    tmp_w8 = tmp_w0 - tmp_w8; /* subs w8,w0,w8; flags updated */
    stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
    /* branch to 0x100000f40 */ /* b 0x100000f40 */
    /* block 0x100000eec */
    /* branch to 0x100000ef0 */ /* b 0x100000ef0 */
    /* block 0x100000ef0 */
    tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
    tmp_w8 = tmp_w8 + 3; /* add w8,w8,#0x3 */
    stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
    /* branch to 0x100000f40 */ /* b 0x100000f40 */
    /* block 0x100000f40 */
    tmp_w0 = stack_m4; /* ldur w0,[x29, #-0x4] */
    tmp_fp = stack_16; /* ldp x29,x30,[sp, #0x10] */
    tmp_lr = stack_24; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 32; /* add sp,sp,#0x20 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t scramble(uint64_t arg1, int32_t arg_10h)
{
    /* Entry: 0x100000f50 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 17 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=scalar, offsets=[12], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 stack_12 = 0;

    /* Control flow structure: */
    /* block 0x100000f50 */
    tmp_sp = tmp_sp - 16; /* sub sp,sp,#0x10 */
    stack_12 = tmp_w0; /* str w0,[sp, #0xc] */
    tmp_w9 = stack_12; /* ldr w9,[sp, #0xc] */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    tmp_w8 = tmp_w8 ^ (tmp_w9 << 13); /* eor w8,w8,w9, LSL #0xd */
    stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
    tmp_w9 = stack_12; /* ldr w9,[sp, #0xc] */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    tmp_w8 = tmp_w8 ^ (tmp_w9 >> 17); /* eor w8,w8,w9, LSR #0x11 */
    stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
    tmp_w9 = stack_12; /* ldr w9,[sp, #0xc] */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    tmp_w8 = tmp_w8 ^ (tmp_w9 << 5); /* eor w8,w8,w9, LSL #0x5 */
    stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
    tmp_w0 = stack_12; /* ldr w0,[sp, #0xc] */
    tmp_sp = tmp_sp + 16; /* add sp,sp,#0x10 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t stack_chk_fail(void)
{
    /* Entry: 0x100000f94 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 3 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[0], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x16 = 0;

    /* Control flow structure: */
    /* block 0x100000f94 */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.__stack_chk_fail */
    tmp_x16 = *(u64 *)(tmp_x16); /* ldr x16, [x16] */
    /* branch to tmp_x16 */ /* br x16 */

    /* return value unknown */
    return 0;
}

int32_t printf(void * format)
{
    /* Entry: 0x100000fa0 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 3 instruction(s) */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[16], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x16 = 0;

    /* Control flow structure: */
    /* block 0x100000fa0 */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.__stack_chk_fail */
    tmp_x16 = *(u64 *)(tmp_x16 + 16); /* ldr x16, [x16, 0x10] */
    /* branch to tmp_x16 */ /* br x16 */

    /* return value unknown */
    return 0;
}

int32_t puts(void * s)
{
    /* Entry: 0x100000fac */
    /* Body status: partially_structured */
    /* 1 basic block(s), 3 instruction(s) */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[24], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x16 = 0;

    /* Control flow structure: */
    /* block 0x100000fac */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.__stack_chk_fail */
    tmp_x16 = *(u64 *)(tmp_x16 + 24); /* ldr x16, [x16, 0x18] */
    /* branch to tmp_x16 */ /* br x16 */

    /* return value unknown */
    return 0;
}

uint64_t strlen(void * s)
{
    /* Entry: 0x100000fb8 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 5 instruction(s) */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[32], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x16 = 0;

    /* Control flow structure: */
    /* block 0x100000fb8 */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.__stack_chk_fail */
    tmp_x16 = *(u64 *)(tmp_x16 + 32); /* ldr x16, [x16, 0x20] */
    /* branch to tmp_x16 */ /* br x16 */
    /* 0x100000fc4: unsupported instruction: sqshlu v26.2d, v11.2d, 0x32 */
    /* 0x100000fc8: unsupported instruction: invalid */

    /* return value unknown */
    return 0;
}

