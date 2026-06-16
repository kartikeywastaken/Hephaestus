/*
 * recovered.c — Phase 5.7.2 Conservative ARM64 Coverage Cleanup
 * Schema version: 5.7.2
 * Generated: 2026-06-16T18:42:50Z
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

int32_t main(int32_t argc, char ** argv);
uint64_t mixed_driver(void);
uint64_t mixed_driver(uint64_t arg1, uint64_t arg_30h);
uint64_t FUN_100000788(void);
uint64_t cfg_pressure(void);
uint64_t FUN_100000898(void);
uint64_t FUN_1000008a8(void);
uint64_t cfg_pressure(int32_t arg1, uint64_t arg2, int32_t arg_50h);
uint64_t FUN_1000008e4(void);
uint64_t indirect_pressure(void);
uint64_t FUN_100000b48(void);
uint64_t FUN_100000b58(void);
uint64_t indirect_pressure(uint64_t arg1, int32_t arg_40h);
uint64_t FUN_100000b9c(void);
uint64_t FUN_100000ccc(void);
uint64_t FUN_100000cdc(void);
uint64_t byte_halfword_pressure(uint64_t arg1);
uint64_t stack_layout_pressure(int32_t arg1);
uint64_t FUN_100001020(void);
uint64_t abi_pressure(void);
uint64_t FUN_1000010cc(void);
uint64_t rotmix(void);
uint64_t FUN_100001268(void);
uint64_t FUN_100001278(void);
uint64_t op_add(void);
uint64_t abi_pressure(uint64_t arg1, int32_t arg2, uint64_t arg3, int32_t arg4, uint64_t arg5, int32_t arg6, uint64_t arg7, uint64_t arg8, uint64_t arg_60h);
uint64_t op_xor(void);
uint64_t op_mul(void);
uint64_t op_shift(void);
uint64_t op_div(void);
uint64_t op_logic(void);
uint64_t tri_a(void);
uint64_t rotmix(uint64_t arg1, uint64_t arg_10h);
uint64_t op_add(uint64_t arg1, uint64_t arg2, uint64_t arg_20h);
uint64_t tri_b(void);
uint64_t op_xor(uint64_t arg1, uint64_t arg2, uint64_t arg_20h);
uint64_t op_mul(uint64_t arg1, uint64_t arg2, uint64_t arg_20h);
uint64_t op_shift(uint64_t arg1, uint64_t arg2, uint64_t arg_20h);
uint64_t tri_c(void);
uint64_t op_div(uint64_t arg1, uint64_t arg2, uint64_t arg_20h);
uint64_t op_logic(uint64_t arg1, uint64_t arg2, uint64_t arg_20h);
uint64_t tri_a(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_40h);
uint64_t tri_b(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_30h);
uint64_t tri_c(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_40h);
uint64_t stack_chk_fail(void);
int32_t printf(void * format);

/* Conservative call target helpers */
u64 call_0x100000768();
u64 call_0x1000008b8();
u64 call_0x100000b7c();
u64 call_0x100000d00();
u64 call_0x100000f50();
u64 call_0x1000012dc();
u64 call_0x1000014a8();
u64 call_0x100001538();
u64 call_0x10000157c();
u64 call_0x1000015c0();
u64 call_0x10000160c();
u64 call_0x100001664();
u64 call_0x1000016cc();
u64 call_0x100001720();
u64 call_0x1000017e8();
u64 call_0x1000018d0();
u64 call_0x100001ab8();
u64 call_0x100001ac4();

/* ================================================== */
/*                 Function Definitions                */
/* ================================================== */

int32_t main(int32_t argc, char ** argv)
{
    /* Entry: 0x100000548 */
    /* Body status: structured */
    /* 30 basic block(s), 129 instruction(s) */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[16, 28, 32, 36, 40, 48], sizes=[4, 8] */
    /*   base=x9, kind=record_like, offsets=[0, 80], sizes=[4, 8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u64 stack_m16 = 0;
    u64 stack_m24 = 0;
    u64 stack_m32 = 0;
    u64 stack_m36 = 0;
    u64 stack_16 = 0;
    u32 stack_28 = 0;
    u64 stack_32 = 0;
    u32 stack_36 = 0;
    u64 stack_40 = 0;
    u64 stack_48 = 0;

    /* Control flow structure: */
    /* if condition block: 0x100000548 */
    /* merge block: 0x100000660 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbz x8 at 0x100000570 targeting 0x100000660")) {
        /* block 0x100000574 */
        /* branch to 0x100000578 */ /* b 0x100000578 */
        /* block 0x100000578 */
        stack_m36 = 0; /* stur wzr,[x29, #-0x24] */
        /* branch to 0x100000580 */ /* b 0x100000580 */
        /* loop kind: while_like */
        /* loop header: 0x100000580 */
        /* loop exits: ['0x10000065c'] */
        while (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbz x8 at 0x100000594 targeting 0x1000005b0")) {
            /* if condition block: 0x100000580 */
            /* merge block: 0x1000005b0 */
            if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbz x8 at 0x100000594 targeting 0x1000005b0")) {
                /* block 0x100000598 */
                /* branch to 0x10000059c */ /* b 0x10000059c */
                /* block 0x10000059c */
                tmp_w8 = stack_m36; /* ldur w8,[x29, #-0x24] */
                tmp_w8 = tmp_w8 - 8; /* subs w8,w8,#0x8; flags updated */
                /* 0x1000005a4: unsupported instruction: cset w8,lt */
                stack_28 = tmp_w8; /* str w8,[sp, #0x1c] */
                /* branch to 0x1000005b0 */ /* b 0x1000005b0 */
            }
            /* block 0x1000005b0 */
            tmp_w8 = stack_28; /* ldr w8,[sp, #0x1c] */
            /* tbz tmp_w8 bit 0 -> 0x10000065c */
            /* block 0x1000005b8 */
            /* branch to 0x1000005bc */ /* b 0x1000005bc */
            /* block 0x1000005bc */
            tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
            tmp_x9 = (i64)(i32)stack_m36; /* ldursw x9,[x29, #-0x24] */
            tmp_x8 = *(u64 *)(tmp_x8 + (tmp_x9 << 3)); /* ldr x8,[x8, x9, LSL #0x3] */
            stack_48 = tmp_x8; /* str x8,[sp, #0x30] */
            stack_40 = 0; /* str xzr,[sp, #0x28] */
            stack_36 = 0; /* str wzr,[sp, #0x24] */
            /* branch to 0x1000005d8 */ /* b 0x1000005d8 */
            /* loop kind: while_like */
            /* loop header: 0x1000005d8 */
            /* loop exits: ['0x100000638'] */
            while (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbz w8 at 0x1000005e4 targeting 0x100000638; loop polarity inverted")) {
                /* if/else condition block: 0x1000005d8 */
                /* merge block: 0x100000628 */
                if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbz w8 at 0x1000005e4 targeting 0x100000638")) {
                    /* block 0x10000061c */
                    /* branch to 0x100000620 */ /* b 0x100000620 */
                    /* block 0x100000620 */
                    /* branch to 0x100000628 */ /* b 0x100000628 */
                } else {
                    /* block 0x100000624 */
                    /* branch to 0x100000628 */ /* b 0x100000628 */
                }
                /* block 0x100000628 */
                tmp_w8 = stack_36; /* ldr w8,[sp, #0x24] */
                tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
                stack_36 = tmp_w8; /* str w8,[sp, #0x24] */
                /* branch to 0x1000005d8 */ /* b 0x1000005d8 */
            }
            /* block 0x100000638 */
            tmp_x9 = stack_40; /* ldr x9,[sp, #0x28] */
            tmp_x8 = stack_m32; /* ldur x8,[x29, #-0x20] */
            tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
            stack_m32 = tmp_x8; /* stur x8,[x29, #-0x20] */
            /* branch to 0x10000064c */ /* b 0x10000064c */
            /* block 0x10000064c */
            tmp_w8 = stack_m36; /* ldur w8,[x29, #-0x24] */
            tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
            stack_m36 = tmp_w8; /* stur w8,[x29, #-0x24] */
            /* branch to 0x100000580 */ /* b 0x100000580 */
        }
        /* block 0x10000065c */
        /* branch to 0x100000660 */ /* b 0x100000660 */
    }
    /* block 0x100000660 */
    stack_32 = 0; /* str wzr,[sp, #0x20] */
    /* branch to 0x100000668 */ /* b 0x100000668 */
    /* loop kind: while_like */
    /* loop header: 0x100000668 */
    /* loop exits: ['0x100000710'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000670 after subs at 0x10000066c; target 0x100000710; loop polarity inverted")) {
        /* block 0x100000668 */
        tmp_w8 = stack_32; /* ldr w8,[sp, #0x20] */
        tmp_w8 = tmp_w8 - 18; /* subs w8,w8,#0x12; flags updated */
        /* conditional branch b.ge -> 0x100000710 */
        /* block 0x100000674 */
        /* branch to 0x100000678 */ /* b 0x100000678 */
        /* block 0x100000678 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = stack_m32; /* ldur x9,[x29, #-0x20] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x9 = (i64)(i32)stack_32; /* ldrsw x9,[sp, #0x20] */
        tmp_x0 = tmp_x8 + tmp_x9; /* add x0,x8,x9 */
        call_0x100000768(tmp_x0); /* bl 0x100000768; args refined from same-block evidence */
        /* block 0x100000690 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        tmp_x0 = stack_m24; /* ldur x0,[x29, #-0x18] */
        tmp_x8 = stack_m32; /* ldur x8,[x29, #-0x20] */
        tmp_x9 = (i64)(i32)stack_32; /* ldrsw x9,[sp, #0x20] */
        tmp_x1 = tmp_x8 ^ tmp_x9; /* eor x1,x8,x9 */
        call_0x1000008b8(tmp_x0, tmp_x1); /* bl 0x1000008b8; args refined from same-block evidence */
        /* block 0x1000006b0 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = (i64)(i32)stack_32; /* ldrsw x9,[sp, #0x20] */
        tmp_x10 = 9; /* mov x10,#0x9 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x0 = tmp_x8 + tmp_x9; /* add x0,x8,x9 */
        call_0x100000b7c(tmp_x0); /* bl 0x100000b7c; args refined from same-block evidence */
        /* block 0x1000006d4 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = (i64)(i32)stack_32; /* ldrsw x9,[sp, #0x20] */
        tmp_x0 = tmp_x8 ^ tmp_x9; /* eor x0,x8,x9 */
        call_0x100000d00(tmp_x0); /* bl 0x100000d00; args refined from same-block evidence */
        /* block 0x1000006f0 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000700 */ /* b 0x100000700 */
        /* block 0x100000700 */
        tmp_w8 = stack_32; /* ldr w8,[sp, #0x20] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_32 = tmp_w8; /* str w8,[sp, #0x20] */
        /* branch to 0x100000668 */ /* b 0x100000668 */
    }
    /* block 0x100000710 */
    tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    stack_16 = tmp_x9; /* str x9,[sp, #0x10] */
    tmp_x9 = *(u64 *)(tmp_x9 + 80); /* ldr x9,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_w9 = *(u32 *)(tmp_x9); /* ldr w9,[x9] */
    tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
    tmp_x9 = tmp_sp; /* mov x9,sp */
    *(u64 *)(tmp_x9) = tmp_x8; /* str x8,[x9] */
    tmp_x0 = 0x100001000; /* adrp x0,0x100001000 */
    tmp_x0 = tmp_x0 + 2768; /* add x0,x0,#0xad0 */
    call_0x100001ac4(tmp_x0); /* bl 0x100001ac4; args refined from same-block evidence */
    /* block 0x100000744 */
    tmp_x9 = stack_16; /* ldr x9,[sp, #0x10] */
    tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */

    /* return value unknown */
    return 0;
}

uint64_t mixed_driver(void)
{
    /* Entry: 0x10000074c */
    /* Body status: partially_structured */
    /* 1 basic block(s), 7 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_96 = 0;
    u64 stack_104 = 0;

    /* Control flow structure: */
    /* block 0x10000074c */
    tmp_x9 = *(u64 *)(tmp_x9 + 80); /* ldr x9,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
    tmp_x8 = tmp_x8 & 255; /* and x8,x8,#0xff */
    tmp_x0 = tmp_x8; /* mov x0,x8 */
    tmp_fp = stack_96; /* ldp x29,x30,[sp, #0x60] */
    tmp_lr = stack_104; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 112; /* add sp,sp,#0x70 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t mixed_driver(uint64_t arg1, uint64_t arg_30h)
{
    /* Entry: 0x100000768 */
    /* Body status: structured */
    /* 12 basic block(s), 84 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[12, 16], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u32 tmp_w8 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m8 = 0;
    u32 stack_12 = 0;
    u64 stack_16 = 0;
    u64 stack_32 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* block 0x100000768 */
    tmp_sp = tmp_sp - 48; /* sub sp, sp, 0x30 */
    stack_32 = tmp_fp; /* stp x29, x30, [sp + var_20h] */
    stack_40 = tmp_lr; /* paired store second register inferred offset +8 */
    tmp_fp = tmp_sp + 32; /* add x29, sp, 0x20 */
    stack_m8 = tmp_x0; /* stur x0, [x29, -8] */
    tmp_x8 = stack_m8; /* ldur x8, [x29, -8] */
    stack_16 = tmp_x8; /* str x8, [sp + var_10h] */
    stack_12 = 0; /* str wzr, [sp + var_ch] */
    /* branch to 0x100000788 */ /* b 0x100000788 */
    /* loop kind: while_like */
    /* loop header: 0x100000788 */
    /* loop exits: ['0x10000088c', '0x1000008a8'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000790 after subs at 0x10000078c; target 0x1000008a8; loop polarity inverted")) {
        /* if/else condition block: 0x100000788 */
        /* merge block: 0x100000898 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000790 after subs at 0x10000078c; target 0x1000008a8")) {
            /* block 0x100000874 */
            /* branch to 0x100000878 */ /* b 0x100000878 */
            /* block 0x100000878 */
            /* branch to 0x100000898 */ /* b 0x100000898 */
        } else {
            /* block 0x10000087c */
            tmp_x8 = stack_16; /* ldr x8, [sp + var_10h] */
            tmp_x8 = tmp_x8 & 4095; /* and x8, x8, 0xfff */
            tmp_x8 = tmp_x8 - 1911; /* subs x8, x8, 0x777; flags updated */
            /* conditional branch b.ne -> 0x100000894 */
            /* block 0x100000894 */
            /* branch to 0x100000898 */ /* b 0x100000898 */
        }
        /* block 0x100000898 */
        tmp_w8 = stack_12; /* ldr w8, [sp + var_ch] */
        tmp_w8 = tmp_w8 + 1; /* add w8, w8, 1 */
        stack_12 = tmp_w8; /* str w8, [sp + var_ch] */
        /* branch to 0x100000788 */ /* b 0x100000788 */
    }
    /* block 0x10000088c */
    /* branch to 0x100000890 */ /* b 0x100000890 */
    /* block 0x100000890 */
    /* branch to 0x1000008a8 */ /* b 0x1000008a8 */
    /* block 0x1000008a8 */
    tmp_x0 = stack_16; /* ldr x0, [sp + var_10h] */
    tmp_fp = stack_32; /* ldp x29, x30, [sp + var_20h] */
    tmp_lr = stack_40; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 48; /* add sp, sp, 0x30 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t FUN_100000788(void)
{
    /* Entry: 0x100000788 */
    /* Body status: structured */
    /* 11 basic block(s), 62 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[12, 16], sizes=[4, 8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x3 = 0;
    u64 tmp_x4 = 0;
    u64 tmp_x5 = 0;
    u64 tmp_x6 = 0;
    u64 tmp_x7 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u64 stack_m8 = 0;
    u64 stack_12 = 0;
    u64 stack_16 = 0;

    /* Control flow structure: */
    /* block 0x100000788 */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    tmp_w8 = tmp_w8 - 32; /* subs w8,w8,#0x20; flags updated */
    /* conditional branch b.ge -> 0x1000008a8 */
    /* block 0x100000794 */
    /* branch to 0x100000798 */ /* b 0x100000798 */
    /* block 0x100000798 */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
    tmp_x0 = tmp_x8 + tmp_x9; /* add x0,x8,x9 */
    tmp_x8 = stack_m8; /* ldur x8,[x29, #-0x8] */
    tmp_w9 = stack_12; /* ldr w9,[sp, #0xc] */
    tmp_w10 = 17; /* mov w10,#0x11 */
    tmp_w10 = tmp_w9 * tmp_w10; /* mul w10,w9,w10 */
    tmp_x9 = tmp_x10; /* mov x9,x10 */
    tmp_x9 = (i64)(i32)tmp_w9; /* sxtw x9,w9 */
    tmp_x1 = tmp_x8 ^ tmp_x9; /* eor x1,x8,x9 */
    call_0x1000008b8(tmp_x0, tmp_x1); /* bl 0x1000008b8; args refined from same-block evidence */
    /* block 0x1000007c4 */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
    stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
    tmp_x0 = tmp_x8 ^ tmp_x9; /* eor x0,x8,x9 */
    call_0x100000f50(tmp_x0); /* bl 0x100000f50; args refined from same-block evidence */
    /* block 0x1000007e0 */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
    stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
    tmp_x10 = 3; /* mov x10,#0x3 */
    tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
    tmp_x0 = tmp_x8 + tmp_x9; /* add x0,x8,x9 */
    call_0x100000b7c(tmp_x0); /* bl 0x100000b7c; args refined from same-block evidence */
    /* block 0x100000804 */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
    stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
    tmp_x0 = stack_16; /* ldr x0,[sp, #0x10] */
    tmp_x1 = stack_m8; /* ldur x1,[x29, #-0x8] */
    tmp_x2 = (i64)(i32)stack_12; /* ldrsw x2,[sp, #0xc] */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x3 = tmp_x8 >> 1; /* lsr x3,x8,#0x1 */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x4 = tmp_x8 << 1; /* lsl x4,x8,#0x1 */
    tmp_x5 = 11; /* mov x5,#0xb */
    tmp_x6 = 22; /* mov x6,#0x16 */
    tmp_x7 = 33; /* mov x7,#0x21 */
    call_0x1000012dc(tmp_x0, tmp_x1, tmp_x2, tmp_x3, tmp_x4, tmp_x5, tmp_x6, tmp_x7); /* bl 0x1000012dc; args refined from same-block evidence */
    /* block 0x10000083c */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
    stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
    tmp_x0 = tmp_x8 + tmp_x9; /* add x0,x8,x9 */
    call_0x100000d00(tmp_x0); /* bl 0x100000d00; args refined from same-block evidence */
    /* block 0x100000858 */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
    stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x8 = tmp_x8 & 31; /* and x8,x8,#0x1f */
    tmp_x8 = tmp_x8 - 18; /* subs x8,x8,#0x12; flags updated */
    /* conditional branch b.ne -> 0x10000087c */
    /* block 0x10000087c */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    /* block 0x100000874 */
    /* branch to 0x100000878 */ /* b 0x100000878 */
    /* block 0x100000878 */
    /* branch to 0x100000898 */ /* b 0x100000898 */

    /* return value unknown */
    return 0;
}

uint64_t cfg_pressure(void)
{
    /* Entry: 0x100000880 */
    /* Body status: structured */
    /* 4 basic block(s), 6 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Control flow structure: */
    /* if/else condition block: 0x100000880 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ne at 0x100000888 after subs at 0x100000884; target 0x100000894; polarity inverted")) {
        /* block 0x10000088c */
        /* branch to 0x100000890 */ /* b 0x100000890 */
        /* block 0x100000890 */
        /* branch to 0x1000008a8 */ /* b 0x1000008a8 */
    } else {
        /* block 0x100000894 */
        /* branch to 0x100000898 */ /* b 0x100000898 */
    }

    /* return value unknown */
    return 0;
}

uint64_t FUN_100000898(void)
{
    /* Entry: 0x100000898 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 4 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=scalar, offsets=[12], sizes=[4] */

    /* Conservative pseudo declarations: */
    u32 tmp_w8 = 0;
    u32 stack_12 = 0;

    /* Control flow structure: */
    /* block 0x100000898 */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
    stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
    /* branch to 0x100000788 */ /* b 0x100000788 */

    /* return value unknown */
    return 0;
}

uint64_t FUN_1000008a8(void)
{
    /* Entry: 0x1000008a8 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 4 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=pointer_like, offsets=[16], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_16 = 0;
    u64 stack_32 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* block 0x1000008a8 */
    tmp_x0 = stack_16; /* ldr x0,[sp, #0x10] */
    tmp_fp = stack_32; /* ldp x29,x30,[sp, #0x20] */
    tmp_lr = stack_40; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 48; /* add sp,sp,#0x30 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t cfg_pressure(int32_t arg1, uint64_t arg2, int32_t arg_50h)
{
    /* Entry: 0x1000008b8 */
    /* Body status: unstructured */
    /* 46 basic block(s), 177 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 16, 24, 32], sizes=[4] */
    /*   base=x9, kind=scalar, offsets=[80], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x3 = 0;
    u64 tmp_x4 = 0;
    u64 tmp_x5 = 0;
    u64 tmp_x6 = 0;
    u64 tmp_x7 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m8 = 0;
    u64 stack_m16 = 0;
    u64 stack_m24 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;
    u64 stack_32 = 0;
    u64 stack_64 = 0;
    u64 stack_72 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: multi_exit_loop */
    {
        /* block 0x1000008b8 */
        tmp_sp = tmp_sp - 80; /* sub sp, sp, 0x50 */
        stack_64 = tmp_fp; /* stp x29, x30, [sp + var_40h] */
        stack_72 = tmp_lr; /* paired store second register inferred offset +8 */
        tmp_fp = tmp_sp + 64; /* add x29, sp, 0x40 */
        stack_m8 = tmp_x0; /* stur x0, [x29, -8] */
        stack_m16 = tmp_x1; /* stur x1, [x29, -0x10] */
        tmp_x8 = stack_m8; /* ldur x8, [x29, -8] */
        tmp_x9 = stack_m16; /* ldur x9, [x29, -0x10] */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8, x8, x9 */
        stack_m24 = tmp_x8; /* stur x8, [x29, -0x18] */
        stack_32 = 0; /* str xzr, [sp + var_20h] */
        /* branch to 0x1000008e4 */ /* b 0x1000008e4 */
        /* block 0x1000008e4 */
        tmp_x8 = stack_32; /* ldr x8, [sp + var_20h] */
        tmp_x8 = tmp_x8 - 80; /* subs x8, x8, 0x50; flags updated */
        /* conditional branch b.hs -> 0x100000b58 */
        /* block 0x1000008f0 */
        /* branch to 0x1000008f4 */ /* b 0x1000008f4 */
        /* block 0x1000008f4 */
        tmp_x8 = stack_32; /* ldr x8, [sp + var_20h] */
        tmp_x9 = 50855; /* mov x9, 0xc6a7 */
        /* 0x1000008fc: unsupported instruction: movk x9, 0x4e67, lsl 16 */
        tmp_x9 = tmp_x8 * tmp_x9; /* mul x9, x8, x9 */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8, x8, x9 */
        stack_m24 = tmp_x8; /* stur x8, [x29, -0x18] */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x8 = tmp_x8 & 15; /* and x8, x8, 0xf */
        tmp_x8 = tmp_x8 - 9; /* subs x8, x8, 9; flags updated */
        /* conditional branch b.ne -> 0x100000928 */
        /* block 0x100000920 */
        /* branch to 0x100000924 */ /* b 0x100000924 */
        /* block 0x100000924 */
        /* branch to 0x100000b48 */ /* b 0x100000b48 */
        /* block 0x100000928 */
        stack_24 = 0; /* str xzr, [sp + var_18h] */
        /* branch to 0x100000930 */ /* b 0x100000930 */
        /* block 0x100000930 */
        tmp_x8 = stack_24; /* ldr x8, [sp + var_18h] */
        tmp_x8 = tmp_x8 - 32; /* subs x8, x8, 0x20; flags updated */
        /* conditional branch b.hs -> 0x100000b2c */
        /* block 0x10000093c */
        /* branch to 0x100000940 */ /* b 0x100000940 */
        /* block 0x100000940 */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x9 = stack_32; /* ldr x9, [sp + var_20h] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8, x8, x9 */
        tmp_x9 = stack_24; /* ldr x9, [sp + var_18h] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8, x8, x9 */
        tmp_x8 = tmp_x8 & 7; /* and x8, x8, 7 */
        stack_16 = tmp_x8; /* str x8, [sp + var_10h] */
        tmp_x8 = stack_16; /* ldr x8, [sp + var_10h] */
        stack_8 = tmp_x8; /* str x8, [sp + var_8h] */
        /* cbz tmp_x8 -> 0x1000009cc */
        /* block 0x100000968 */
        /* branch to 0x10000096c */ /* b 0x10000096c */
        /* block 0x10000096c */
        tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
        tmp_x8 = tmp_x8 - 1; /* subs x8, x8, 1; flags updated */
        /* conditional branch b.eq -> 0x1000009ec */
        /* block 0x100000978 */
        /* branch to 0x10000097c */ /* b 0x10000097c */
        /* block 0x10000097c */
        tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
        tmp_x8 = tmp_x8 - 2; /* subs x8, x8, 2; flags updated */
        /* conditional branch b.eq -> 0x100000a0c */
        /* block 0x100000988 */
        /* branch to 0x10000098c */ /* b 0x10000098c */
        /* block 0x10000098c */
        tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
        tmp_x8 = tmp_x8 - 3; /* subs x8, x8, 3; flags updated */
        /* conditional branch b.eq -> 0x100000a4c */
        /* block 0x100000998 */
        /* branch to 0x10000099c */ /* b 0x10000099c */
        /* block 0x10000099c */
        tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
        tmp_x8 = tmp_x8 - 4; /* subs x8, x8, 4; flags updated */
        /* conditional branch b.eq -> 0x100000a6c */
        /* block 0x1000009a8 */
        /* branch to 0x1000009ac */ /* b 0x1000009ac */
        /* block 0x1000009ac */
        tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
        tmp_x8 = tmp_x8 - 5; /* subs x8, x8, 5; flags updated */
        /* conditional branch b.eq -> 0x100000abc */
        /* block 0x1000009b8 */
        /* branch to 0x1000009bc */ /* b 0x1000009bc */
        /* block 0x1000009bc */
        tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
        tmp_x8 = tmp_x8 - 6; /* subs x8, x8, 6; flags updated */
        /* conditional branch b.eq -> 0x100000ac0 */
        /* block 0x1000009c8 */
        /* branch to 0x100000ae0 */ /* b 0x100000ae0 */
        /* block 0x1000009cc */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x9 = stack_24; /* ldr x9, [sp + var_18h] */
        tmp_x0 = tmp_x8 + tmp_x9; /* add x0, x8, x9 */
        call_0x100000f50(tmp_x0); /* bl sym._stack_layout_pressure; args refined from same-block evidence */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8, x8, x0 */
        stack_m24 = tmp_x8; /* stur x8, [x29, -0x18] */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x1000009ec */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x9 = stack_24; /* ldr x9, [sp + var_18h] */
        tmp_x0 = tmp_x8 ^ tmp_x9; /* eor x0, x8, x9 */
        call_0x100000b7c(tmp_x0); /* bl sym._indirect_pressure; args refined from same-block evidence */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8, x8, x0 */
        stack_m24 = tmp_x8; /* stur x8, [x29, -0x18] */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x100000a0c */
        tmp_x0 = stack_m24; /* ldur x0, [x29, -0x18] */
        tmp_x1 = stack_m8; /* ldur x1, [x29, -8] */
        tmp_x2 = stack_m16; /* ldur x2, [x29, -0x10] */
        tmp_x3 = stack_32; /* ldr x3, [sp + var_20h] */
        tmp_x4 = stack_24; /* ldr x4, [sp + var_18h] */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x5 = tmp_x8 >> 3; /* lsr x5, x8, 3 */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x6 = tmp_x8 << 2; /* lsl x6, x8, 2 */
        tmp_x7 = 64206; /* mov x7, 0xface */
        /* 0x100000a34: unsupported instruction: movk x7, 0xfeed, lsl 16 */
        call_0x1000012dc(tmp_x0, tmp_x1, tmp_x2, tmp_x3, tmp_x4, tmp_x5, tmp_x6, tmp_x7); /* bl sym._abi_pressure; args refined from same-block evidence */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8, x8, x0 */
        stack_m24 = tmp_x8; /* stur x8, [x29, -0x18] */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x100000a4c */
        tmp_x9 = stack_m24; /* ldur x9, [x29, -0x18] */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x8 = tmp_x8 >> 5; /* lsr x8, x8, 5 */
        tmp_x8 = tmp_x8 ^ (tmp_x9 << 0); /* eor x8, x8, x9, lsl 3 */
        tmp_x9 = stack_24; /* ldr x9, [sp + var_18h] */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8, x8, x9 */
        stack_m24 = tmp_x8; /* stur x8, [x29, -0x18] */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x100000a6c */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        /* tbz tmp_w8 bit 0 -> 0x100000a98 */
        /* block 0x100000a74 */
        /* branch to 0x100000a78 */ /* b 0x100000a78 */
        /* block 0x100000a78 */
        tmp_x0 = stack_m24; /* ldur x0, [x29, -0x18] */
        tmp_x1 = stack_m8; /* ldur x1, [x29, -8] */
        tmp_x2 = stack_m16; /* ldur x2, [x29, -0x10] */
        call_0x100001720(tmp_x0, tmp_x1, tmp_x2); /* bl sym._tri_a; args refined from same-block evidence */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8, x8, x0 */
        stack_m24 = tmp_x8; /* stur x8, [x29, -0x18] */
        /* branch to 0x100000ab8 */ /* b 0x100000ab8 */
        /* block 0x100000a98 */
        tmp_x0 = stack_m24; /* ldur x0, [x29, -0x18] */
        tmp_x1 = stack_m16; /* ldur x1, [x29, -0x10] */
        tmp_x2 = stack_m8; /* ldur x2, [x29, -8] */
        call_0x1000017e8(tmp_x0, tmp_x1, tmp_x2); /* bl sym._tri_b; args refined from same-block evidence */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8, x8, x0 */
        stack_m24 = tmp_x8; /* stur x8, [x29, -0x18] */
        /* branch to 0x100000ab8 */ /* b 0x100000ab8 */
        /* block 0x100000ab8 */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x100000abc */
        /* branch to 0x100000b1c */ /* b 0x100000b1c */
        /* block 0x100000ac0 */
        tmp_x0 = stack_m24; /* ldur x0, [x29, -0x18] */
        tmp_x1 = stack_32; /* ldr x1, [sp + var_20h] */
        tmp_x2 = stack_24; /* ldr x2, [sp + var_18h] */
        call_0x1000018d0(tmp_x0, tmp_x1, tmp_x2); /* bl sym._tri_c; args refined from same-block evidence */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8, x8, x0 */
        stack_m24 = tmp_x8; /* stur x8, [x29, -0x18] */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x100000ae0 */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x9 = 30864; /* mov x9, 0x7890 */
        /* 0x100000ae8: unsupported instruction: movk x9, 0x3456, lsl 16 */
        /* 0x100000aec: unsupported instruction: movk x9, 0xef12, lsl 32 */
        /* 0x100000af0: unsupported instruction: movk x9, 0xabcd, lsl 48 */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8, x8, x9 */
        stack_m24 = tmp_x8; /* stur x8, [x29, -0x18] */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x100000b00 */
        tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
        tmp_x8 = tmp_x8 & 1023; /* and x8, x8, 0x3ff */
        tmp_x8 = tmp_x8 - 341; /* subs x8, x8, 0x155; flags updated */
        /* conditional branch b.ne -> 0x100000b18 */
        /* block 0x100000b10 */
        /* branch to 0x100000b14 */ /* b 0x100000b14 */
        /* block 0x100000b14 */
        /* branch to 0x100000b2c */ /* b 0x100000b2c */
        /* block 0x100000b18 */
        /* branch to 0x100000b1c */ /* b 0x100000b1c */
        /* block 0x100000b1c */
        tmp_x8 = stack_24; /* ldr x8, [sp + var_18h] */
        tmp_x8 = tmp_x8 + 1; /* add x8, x8, 1 */
        stack_24 = tmp_x8; /* str x8, [sp + var_18h] */
        /* branch to 0x100000930 */ /* b 0x100000930 */
        /* block 0x100000b2c */
        tmp_w8 = stack_m24; /* ldurh w8, [x29, -0x18] */
        tmp_x9 = 48879; /* mov x9, 0xbeef */
        tmp_x8 = tmp_x8 - tmp_x9; /* subs x8, x8, x9; flags updated */
        /* conditional branch b.ne -> 0x100000b44 */
        /* block 0x100000b3c */
        /* branch to 0x100000b40 */ /* b 0x100000b40 */
        /* block 0x100000b40 */
        /* branch to 0x100000b58 */ /* b 0x100000b58 */
        /* block 0x100000b44 */
        /* branch to 0x100000b48 */ /* b 0x100000b48 */
        /* block 0x100000b48 */
        tmp_x8 = stack_32; /* ldr x8, [sp + var_20h] */
        tmp_x8 = tmp_x8 + 1; /* add x8, x8, 1 */
        stack_32 = tmp_x8; /* str x8, [sp + var_20h] */
        /* branch to 0x1000008e4 */ /* b 0x1000008e4 */
        /* block 0x100000b58 */
        tmp_x10 = stack_m24; /* ldur x10, [x29, -0x18] */
        tmp_x9 = 0x100008000; /* adrp x9, 0x100008000 */
        tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8, [x9, 0x50] */
        tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8, x8, x10 */
        *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8, [x9, 0x50] */
        tmp_x0 = stack_m24; /* ldur x0, [x29, -0x18] */
        tmp_fp = stack_64; /* ldp x29, x30, [sp + var_40h] */
        tmp_lr = stack_72; /* paired load second register inferred offset +8 */
        tmp_sp = tmp_sp + 80; /* add sp, sp, 0x50 */
        return tmp_x0; /* return value from x0 before ret */
    }
    /* unstructured region end */

}

uint64_t FUN_1000008e4(void)
{
    /* Entry: 0x1000008e4 */
    /* Body status: unstructured */
    /* 48 basic block(s), 152 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 16, 24, 32], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x3 = 0;
    u64 tmp_x4 = 0;
    u64 tmp_x5 = 0;
    u64 tmp_x6 = 0;
    u64 tmp_x7 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u32 tmp_w8 = 0;
    u64 stack_m8 = 0;
    u64 stack_m16 = 0;
    u64 stack_m24 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;
    u64 stack_32 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: multi_exit_loop */
    {
        /* block 0x1000008e4 */
        tmp_x8 = stack_32; /* ldr x8,[sp, #0x20] */
        tmp_x8 = tmp_x8 - 80; /* subs x8,x8,#0x50; flags updated */
        /* conditional branch b.cs -> 0x100000b58 */
        /* block 0x1000008f0 */
        /* branch to 0x1000008f4 */ /* b 0x1000008f4 */
        /* block 0x1000008f4 */
        tmp_x8 = stack_32; /* ldr x8,[sp, #0x20] */
        tmp_x9 = 50855; /* mov x9,#0xc6a7 */
        /* 0x1000008fc: unsupported instruction: movk x9,#0x4e67, LSL #16 */
        tmp_x9 = tmp_x8 * tmp_x9; /* mul x9,x8,x9 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 & 15; /* and x8,x8,#0xf */
        tmp_x8 = tmp_x8 - 9; /* subs x8,x8,#0x9; flags updated */
        /* conditional branch b.ne -> 0x100000928 */
        /* block 0x100000920 */
        /* branch to 0x100000924 */ /* b 0x100000924 */
        /* block 0x100000924 */
        /* branch to 0x100000b48 */ /* b 0x100000b48 */
        /* block 0x100000928 */
        stack_24 = 0; /* str xzr,[sp, #0x18] */
        /* branch to 0x100000930 */ /* b 0x100000930 */
        /* block 0x100000930 */
        tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
        tmp_x8 = tmp_x8 - 32; /* subs x8,x8,#0x20; flags updated */
        /* conditional branch b.cs -> 0x100000b2c */
        /* block 0x10000093c */
        /* branch to 0x100000940 */ /* b 0x100000940 */
        /* block 0x100000940 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = stack_32; /* ldr x9,[sp, #0x20] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x8 = tmp_x8 & 7; /* and x8,x8,#0x7 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
        /* cbz tmp_x8 -> 0x1000009cc */
        /* block 0x100000968 */
        /* branch to 0x10000096c */ /* b 0x10000096c */
        /* block 0x10000096c */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 - 1; /* subs x8,x8,#0x1; flags updated */
        /* conditional branch b.eq -> 0x1000009ec */
        /* block 0x100000978 */
        /* branch to 0x10000097c */ /* b 0x10000097c */
        /* block 0x10000097c */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 - 2; /* subs x8,x8,#0x2; flags updated */
        /* conditional branch b.eq -> 0x100000a0c */
        /* block 0x100000988 */
        /* branch to 0x10000098c */ /* b 0x10000098c */
        /* block 0x10000098c */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 - 3; /* subs x8,x8,#0x3; flags updated */
        /* conditional branch b.eq -> 0x100000a4c */
        /* block 0x100000998 */
        /* branch to 0x10000099c */ /* b 0x10000099c */
        /* block 0x10000099c */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 - 4; /* subs x8,x8,#0x4; flags updated */
        /* conditional branch b.eq -> 0x100000a6c */
        /* block 0x1000009a8 */
        /* branch to 0x1000009ac */ /* b 0x1000009ac */
        /* block 0x1000009ac */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 - 5; /* subs x8,x8,#0x5; flags updated */
        /* conditional branch b.eq -> 0x100000abc */
        /* block 0x1000009b8 */
        /* branch to 0x1000009bc */ /* b 0x1000009bc */
        /* block 0x1000009bc */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 - 6; /* subs x8,x8,#0x6; flags updated */
        /* conditional branch b.eq -> 0x100000ac0 */
        /* block 0x1000009c8 */
        /* branch to 0x100000ae0 */ /* b 0x100000ae0 */
        /* block 0x1000009cc */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
        tmp_x0 = tmp_x8 + tmp_x9; /* add x0,x8,x9 */
        call_0x100000f50(tmp_x0); /* bl 0x100000f50; args refined from same-block evidence */
        /* block 0x1000009dc */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x1000009ec */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
        tmp_x0 = tmp_x8 ^ tmp_x9; /* eor x0,x8,x9 */
        call_0x100000b7c(tmp_x0); /* bl 0x100000b7c; args refined from same-block evidence */
        /* block 0x1000009fc */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x100000a0c */
        tmp_x0 = stack_m24; /* ldur x0,[x29, #-0x18] */
        tmp_x1 = stack_m8; /* ldur x1,[x29, #-0x8] */
        tmp_x2 = stack_m16; /* ldur x2,[x29, #-0x10] */
        tmp_x3 = stack_32; /* ldr x3,[sp, #0x20] */
        tmp_x4 = stack_24; /* ldr x4,[sp, #0x18] */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x5 = tmp_x8 >> 3; /* lsr x5,x8,#0x3 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x6 = tmp_x8 << 2; /* lsl x6,x8,#0x2 */
        tmp_x7 = 64206; /* mov x7,#0xface */
        /* 0x100000a34: unsupported instruction: movk x7,#0xfeed, LSL #16 */
        call_0x1000012dc(tmp_x0, tmp_x1, tmp_x2, tmp_x3, tmp_x4, tmp_x5, tmp_x6, tmp_x7); /* bl 0x1000012dc; args refined from same-block evidence */
        /* block 0x100000a3c */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x100000a4c */
        tmp_x9 = stack_m24; /* ldur x9,[x29, #-0x18] */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 >> 5; /* lsr x8,x8,#0x5 */
        tmp_x8 = tmp_x8 ^ (tmp_x9 << 3); /* eor x8,x8,x9, LSL #0x3 */
        tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x100000a6c */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        /* tbz tmp_w8 bit 0 -> 0x100000a98 */
        /* block 0x100000a74 */
        /* branch to 0x100000a78 */ /* b 0x100000a78 */
        /* block 0x100000a78 */
        tmp_x0 = stack_m24; /* ldur x0,[x29, #-0x18] */
        tmp_x1 = stack_m8; /* ldur x1,[x29, #-0x8] */
        tmp_x2 = stack_m16; /* ldur x2,[x29, #-0x10] */
        call_0x100001720(tmp_x0, tmp_x1, tmp_x2); /* bl 0x100001720; args refined from same-block evidence */
        /* block 0x100000a88 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000ab8 */ /* b 0x100000ab8 */
        /* block 0x100000a98 */
        tmp_x0 = stack_m24; /* ldur x0,[x29, #-0x18] */
        tmp_x1 = stack_m16; /* ldur x1,[x29, #-0x10] */
        tmp_x2 = stack_m8; /* ldur x2,[x29, #-0x8] */
        call_0x1000017e8(tmp_x0, tmp_x1, tmp_x2); /* bl 0x1000017e8; args refined from same-block evidence */
        /* block 0x100000aa8 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000ab8 */ /* b 0x100000ab8 */
        /* block 0x100000ab8 */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x100000abc */
        /* branch to 0x100000b1c */ /* b 0x100000b1c */
        /* block 0x100000ac0 */
        tmp_x0 = stack_m24; /* ldur x0,[x29, #-0x18] */
        tmp_x1 = stack_32; /* ldr x1,[sp, #0x20] */
        tmp_x2 = stack_24; /* ldr x2,[sp, #0x18] */
        call_0x1000018d0(tmp_x0, tmp_x1, tmp_x2); /* bl 0x1000018d0; args refined from same-block evidence */
        /* block 0x100000ad0 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x100000ae0 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = 30864; /* mov x9,#0x7890 */
        /* 0x100000ae8: unsupported instruction: movk x9,#0x3456, LSL #16 */
        /* 0x100000aec: unsupported instruction: movk x9,#0xef12, LSL #32 */
        /* 0x100000af0: unsupported instruction: movk x9,#0xabcd, LSL #48 */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000b00 */ /* b 0x100000b00 */
        /* block 0x100000b00 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 & 1023; /* and x8,x8,#0x3ff */
        tmp_x8 = tmp_x8 - 341; /* subs x8,x8,#0x155; flags updated */
        /* conditional branch b.ne -> 0x100000b18 */
        /* block 0x100000b10 */
        /* branch to 0x100000b14 */ /* b 0x100000b14 */
        /* block 0x100000b14 */
        /* branch to 0x100000b2c */ /* b 0x100000b2c */
        /* block 0x100000b18 */
        /* branch to 0x100000b1c */ /* b 0x100000b1c */
        /* block 0x100000b1c */
        tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
        tmp_x8 = tmp_x8 + 1; /* add x8,x8,#0x1 */
        stack_24 = tmp_x8; /* str x8,[sp, #0x18] */
        /* branch to 0x100000930 */ /* b 0x100000930 */
        /* block 0x100000b2c */
        tmp_w8 = stack_m24; /* ldurh w8,[x29, #-0x18] */
        tmp_x9 = 48879; /* mov x9,#0xbeef */
        tmp_x8 = tmp_x8 - tmp_x9; /* subs x8,x8,x9; flags updated */
        /* conditional branch b.ne -> 0x100000b44 */
        /* block 0x100000b3c */
        /* branch to 0x100000b40 */ /* b 0x100000b40 */
        /* block 0x100000b40 */
        /* branch to 0x100000b58 */ /* b 0x100000b58 */
    }
    /* unstructured region end */

    /* return value unknown */
    return 0;
}

uint64_t indirect_pressure(void)
{
    /* Entry: unknown */
    /* Body status: partially_structured */
    /* 1 basic block(s), 1 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Control flow structure: */
    /* block 0x100000cc8 */
    /* branch to 0x100000ccc */ /* b 0x100000ccc */

    /* return value unknown */
    return 0;
}

uint64_t FUN_100000b48(void)
{
    /* Entry: 0x100000b48 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 4 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=pointer_like, offsets=[32], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x8 = 0;
    u64 stack_32 = 0;

    /* Control flow structure: */
    /* block 0x100000b48 */
    tmp_x8 = stack_32; /* ldr x8,[sp, #0x20] */
    tmp_x8 = tmp_x8 + 1; /* add x8,x8,#0x1 */
    stack_32 = tmp_x8; /* str x8,[sp, #0x20] */
    /* branch to 0x1000008e4 */ /* b 0x1000008e4 */

    /* return value unknown */
    return 0;
}

uint64_t FUN_100000b58(void)
{
    /* Entry: 0x100000b58 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 9 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m24 = 0;
    u64 stack_64 = 0;
    u64 stack_72 = 0;

    /* Control flow structure: */
    /* block 0x100000b58 */
    tmp_x10 = stack_m24; /* ldur x10,[x29, #-0x18] */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
    tmp_x0 = stack_m24; /* ldur x0,[x29, #-0x18] */
    tmp_fp = stack_64; /* ldp x29,x30,[sp, #0x40] */
    tmp_lr = stack_72; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 80; /* add sp,sp,#0x50 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t indirect_pressure(uint64_t arg1, int32_t arg_40h)
{
    /* Entry: 0x100000b7c */
    /* Body status: structured */
    /* 12 basic block(s), 97 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[0, 8, 16, 24], sizes=[4] */
    /*   base=x8, kind=scalar, offsets=[0], sizes=[4] */
    /*   base=x9, kind=scalar, offsets=[80], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m8 = 0;
    u64 stack_m16 = 0;
    u64 stack_0 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;
    u64 stack_48 = 0;
    u64 stack_56 = 0;

    /* Control flow structure: */
    /* block 0x100000b7c */
    tmp_sp = tmp_sp - 64; /* sub sp, sp, 0x40 */
    stack_48 = tmp_fp; /* stp x29, x30, [sp + var_30h] */
    stack_56 = tmp_lr; /* paired store second register inferred offset +8 */
    tmp_fp = tmp_sp + 48; /* add x29, sp, 0x30 */
    stack_m8 = tmp_x0; /* stur x0, [x29, -8] */
    tmp_x8 = stack_m8; /* ldur x8, [x29, -8] */
    stack_m16 = tmp_x8; /* stur x8, [x29, -0x10] */
    stack_24 = 0; /* str xzr, [sp + var_18h] */
    /* branch to 0x100000b9c */ /* b 0x100000b9c */
    /* loop kind: while_like */
    /* loop header: 0x100000b9c */
    /* loop exits: ['0x100000c08', '0x100000cdc'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.hs at 0x100000ba4 after subs at 0x100000ba0; target 0x100000cdc; loop polarity inverted")) {
        /* block 0x100000b9c */
        tmp_x8 = stack_24; /* ldr x8, [sp + var_18h] */
        tmp_x8 = tmp_x8 - 96; /* subs x8, x8, 0x60; flags updated */
        /* conditional branch b.hs -> 0x100000cdc */
        /* block 0x100000ba8 */
        /* branch to 0x100000bac */ /* b 0x100000bac */
        /* block 0x100000bac */
        tmp_x8 = stack_m16; /* ldur x8, [x29, -0x10] */
        tmp_x9 = stack_24; /* ldr x9, [sp + var_18h] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8, x8, x9 */
        tmp_x10 = 6; /* mov x10, 6 */
        tmp_x9 = tmp_x8 / tmp_x10; /* udiv x9, x8, x10 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9, x9, x10 */
        tmp_x9 = tmp_x8 - tmp_x9; /* subs x9, x8, x9; flags updated */
        tmp_x8 = 0x100008000; /* adrp x8, 0x100008000 */
        tmp_x8 = tmp_x8 + 8; /* add x8, x8, 8 */
        tmp_x8 = *(u64 *)(tmp_x8); /* ldr x8, [x8, x9, lsl 3] */
        stack_16 = tmp_x8; /* str x8, [sp + var_10h] */
        tmp_x8 = stack_16; /* ldr x8, [sp + var_10h] */
        tmp_x0 = stack_m16; /* ldur x0, [x29, -0x10] */
        tmp_x9 = stack_24; /* ldr x9, [sp + var_18h] */
        tmp_x10 = stack_m8; /* ldur x10, [x29, -8] */
        tmp_x1 = tmp_x9 + tmp_x10; /* add x1, x9, x10 */
        /* indirect call through tmp_x8 with args: tmp_x0, tmp_x1, tmp_x2 */ /* blr x8 */
        tmp_x8 = stack_m16; /* ldur x8, [x29, -0x10] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8, x8, x0 */
        stack_m16 = tmp_x8; /* stur x8, [x29, -0x10] */
        tmp_w8 = stack_m16; /* ldurb w8, [x29, -0x10] */
        tmp_x8 = tmp_x8 - 66; /* subs x8, x8, 0x42; flags updated */
        /* conditional branch b.ne -> 0x100000c10 */
        /* if/else condition block: 0x100000c10 */
        /* merge block: 0x100000ccc */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ne at 0x100000c1c after subs at 0x100000c18; target 0x100000c28; polarity inverted")) {
            /* block 0x100000c20 */
            /* branch to 0x100000c24 */ /* b 0x100000c24 */
            /* block 0x100000c24 */
            /* branch to 0x100000ccc */ /* b 0x100000ccc */
        } else {
            /* block 0x100000c28 */
            tmp_x8 = stack_m16; /* ldur x8, [x29, -0x10] */
            tmp_x10 = 3; /* mov x10, 3 */
            tmp_x8 = tmp_x8 >> 3; /* lsr x8, x8, 3 */
            tmp_x9 = tmp_x8 / tmp_x10; /* udiv x9, x8, x10 */
            tmp_x9 = tmp_x9 * tmp_x10; /* mul x9, x9, x10 */
            tmp_x9 = tmp_x8 - tmp_x9; /* subs x9, x8, x9; flags updated */
            tmp_x8 = 0x100008000; /* adrp x8, 0x100008000 */
            tmp_x8 = tmp_x8 + 56; /* add x8, x8, 0x38 */
            tmp_x8 = *(u64 *)(tmp_x8); /* ldr x8, [x8, x9, lsl 3] */
            stack_8 = tmp_x8; /* str x8, [sp + var_8h] */
            tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
            tmp_x0 = stack_m16; /* ldur x0, [x29, -0x10] */
            tmp_x1 = stack_m8; /* ldur x1, [x29, -8] */
            tmp_x2 = stack_24; /* ldr x2, [sp + var_18h] */
            /* indirect call through tmp_x8 with args: tmp_x0, tmp_x1, tmp_x2 */ /* blr x8 */
            tmp_x8 = stack_m16; /* ldur x8, [x29, -0x10] */
            tmp_x8 = tmp_x8 + tmp_x0; /* add x8, x8, x0 */
            stack_m16 = tmp_x8; /* stur x8, [x29, -0x10] */
            tmp_x9 = stack_m16; /* ldur x9, [x29, -0x10] */
            tmp_x8 = stack_24; /* ldr x8, [sp + var_18h] */
            tmp_x8 = tmp_x8 + (tmp_x9 >> 0); /* add x8, x8, x9, lsr 5 */
            tmp_x10 = 6; /* mov x10, 6 */
            tmp_x9 = tmp_x8 / tmp_x10; /* udiv x9, x8, x10 */
            tmp_x9 = tmp_x9 * tmp_x10; /* mul x9, x9, x10 */
            tmp_x9 = tmp_x8 - tmp_x9; /* subs x9, x8, x9; flags updated */
            tmp_x8 = 0x100008000; /* adrp x8, 0x100008000 */
            tmp_x8 = tmp_x8 + 8; /* add x8, x8, 8 */
            tmp_x8 = *(u64 *)(tmp_x8); /* ldr x8, [x8, x9, lsl 3] */
            stack_0 = tmp_x8; /* str x8, [sp] */
            tmp_x8 = stack_0; /* ldr x8, [sp] */
            tmp_x9 = stack_m16; /* ldur x9, [x29, -0x10] */
            tmp_x10 = stack_m8; /* ldur x10, [x29, -8] */
            tmp_x0 = tmp_x9 ^ tmp_x10; /* eor x0, x9, x10 */
            tmp_x9 = stack_m16; /* ldur x9, [x29, -0x10] */
            tmp_x10 = stack_24; /* ldr x10, [sp + var_18h] */
            tmp_x1 = tmp_x9 + tmp_x10; /* add x1, x9, x10 */
            /* indirect call through tmp_x8 with args: tmp_x0, tmp_x1, tmp_x2 */ /* blr x8 */
            tmp_x8 = stack_m16; /* ldur x8, [x29, -0x10] */
            tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8, x8, x0 */
            stack_m16 = tmp_x8; /* stur x8, [x29, -0x10] */
            /* branch to 0x100000ccc */ /* b 0x100000ccc */
        }
        /* block 0x100000ccc */
        tmp_x8 = stack_24; /* ldr x8, [sp + var_18h] */
        tmp_x8 = tmp_x8 + 1; /* add x8, x8, 1 */
        stack_24 = tmp_x8; /* str x8, [sp + var_18h] */
        /* branch to 0x100000b9c */ /* b 0x100000b9c */
    }
    /* block 0x100000c08 */
    /* branch to 0x100000c0c */ /* b 0x100000c0c */
    /* block 0x100000c0c */
    /* branch to 0x100000cdc */ /* b 0x100000cdc */
    /* block 0x100000cdc */
    tmp_x10 = stack_m16; /* ldur x10, [x29, -0x10] */
    tmp_x9 = 0x100008000; /* adrp x9, 0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8, [x9, 0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8, x8, x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8, [x9, 0x50] */
    tmp_x0 = stack_m16; /* ldur x0, [x29, -0x10] */
    tmp_fp = stack_48; /* ldp x29, x30, [sp + var_30h] */
    tmp_lr = stack_56; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 64; /* add sp, sp, 0x40 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t FUN_100000b9c(void)
{
    /* Entry: 0x100000b9c */
    /* Body status: structured */
    /* 12 basic block(s), 75 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[0, 8, 16, 24], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u64 stack_m8 = 0;
    u64 stack_m16 = 0;
    u64 stack_0 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;

    /* Control flow structure: */
    /* block 0x100000b9c */
    tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
    tmp_x8 = tmp_x8 - 96; /* subs x8,x8,#0x60; flags updated */
    /* conditional branch b.cs -> 0x100000cdc */
    /* block 0x100000ba8 */
    /* branch to 0x100000bac */ /* b 0x100000bac */
    /* block 0x100000bac */
    tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
    tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    tmp_x10 = 6; /* mov x10,#0x6 */
    tmp_x9 = tmp_x8 / tmp_x10; /* udiv x9,x8,x10 */
    tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
    tmp_x9 = tmp_x8 - tmp_x9; /* subs x9,x8,x9; flags updated */
    tmp_x8 = 0x100008000; /* adrp x8,0x100008000 */
    tmp_x8 = tmp_x8 + 8; /* add x8,x8,#0x8 */
    tmp_x8 = *(u64 *)(tmp_x8 + (tmp_x9 << 3)); /* ldr x8,[x8, x9, LSL #0x3] */
    stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x0 = stack_m16; /* ldur x0,[x29, #-0x10] */
    tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
    tmp_x10 = stack_m8; /* ldur x10,[x29, #-0x8] */
    tmp_x1 = tmp_x9 + tmp_x10; /* add x1,x9,x10 */
    /* indirect call through tmp_x8 with args: tmp_x0, tmp_x1 */ /* blr x8 */
    /* block 0x100000bf0 */
    tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
    stack_m16 = tmp_x8; /* stur x8,[x29, #-0x10] */
    tmp_w8 = stack_m16; /* ldurb w8,[x29, #-0x10] */
    tmp_x8 = tmp_x8 - 66; /* subs x8,x8,#0x42; flags updated */
    /* conditional branch b.ne -> 0x100000c10 */
    /* if/else condition block: 0x100000c10 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ne at 0x100000c1c after subs at 0x100000c18; target 0x100000c28; polarity inverted")) {
        /* block 0x100000c20 */
        /* branch to 0x100000c24 */ /* b 0x100000c24 */
        /* block 0x100000c24 */
        /* branch to 0x100000ccc */ /* b 0x100000ccc */
    } else {
        /* block 0x100000c28 */
        tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
        tmp_x10 = 3; /* mov x10,#0x3 */
        tmp_x8 = tmp_x8 >> 3; /* lsr x8,x8,#0x3 */
        tmp_x9 = tmp_x8 / tmp_x10; /* udiv x9,x8,x10 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x9 = tmp_x8 - tmp_x9; /* subs x9,x8,x9; flags updated */
        tmp_x8 = 0x100008000; /* adrp x8,0x100008000 */
        tmp_x8 = tmp_x8 + 56; /* add x8,x8,#0x38 */
        tmp_x8 = *(u64 *)(tmp_x8 + (tmp_x9 << 3)); /* ldr x8,[x8, x9, LSL #0x3] */
        stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x0 = stack_m16; /* ldur x0,[x29, #-0x10] */
        tmp_x1 = stack_m8; /* ldur x1,[x29, #-0x8] */
        tmp_x2 = stack_24; /* ldr x2,[sp, #0x18] */
        /* indirect call through tmp_x8 with args: tmp_x0, tmp_x1 */ /* blr x8 */
        /* block 0x100000c64 */
        tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
        stack_m16 = tmp_x8; /* stur x8,[x29, #-0x10] */
        tmp_x9 = stack_m16; /* ldur x9,[x29, #-0x10] */
        tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
        tmp_x8 = tmp_x8 + (tmp_x9 >> 5); /* add x8,x8,x9, LSR #0x5 */
        tmp_x10 = 6; /* mov x10,#0x6 */
        tmp_x9 = tmp_x8 / tmp_x10; /* udiv x9,x8,x10 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x9 = tmp_x8 - tmp_x9; /* subs x9,x8,x9; flags updated */
        tmp_x8 = 0x100008000; /* adrp x8,0x100008000 */
        tmp_x8 = tmp_x8 + 8; /* add x8,x8,#0x8 */
        tmp_x8 = *(u64 *)(tmp_x8 + (tmp_x9 << 3)); /* ldr x8,[x8, x9, LSL #0x3] */
        stack_0 = tmp_x8; /* str x8,[sp] */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x9 = stack_m16; /* ldur x9,[x29, #-0x10] */
        tmp_x10 = stack_m8; /* ldur x10,[x29, #-0x8] */
        tmp_x0 = tmp_x9 ^ tmp_x10; /* eor x0,x9,x10 */
        tmp_x9 = stack_m16; /* ldur x9,[x29, #-0x10] */
        tmp_x10 = stack_24; /* ldr x10,[sp, #0x18] */
        tmp_x1 = tmp_x9 + tmp_x10; /* add x1,x9,x10 */
        /* indirect call through tmp_x8 with args: tmp_x0, tmp_x1 */ /* blr x8 */
        /* block 0x100000cbc */
        tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
        stack_m16 = tmp_x8; /* stur x8,[x29, #-0x10] */
    }
    /* block 0x100000c08 */
    /* branch to 0x100000c0c */ /* b 0x100000c0c */
    /* block 0x100000c0c */
    /* branch to 0x100000cdc */ /* b 0x100000cdc */

    /* return value unknown */
    return 0;
}

uint64_t FUN_100000ccc(void)
{
    /* Entry: 0x100000ccc */
    /* Body status: partially_structured */
    /* 1 basic block(s), 4 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=pointer_like, offsets=[24], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x8 = 0;
    u64 stack_24 = 0;

    /* Control flow structure: */
    /* block 0x100000ccc */
    tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
    tmp_x8 = tmp_x8 + 1; /* add x8,x8,#0x1 */
    stack_24 = tmp_x8; /* str x8,[sp, #0x18] */
    /* branch to 0x100000b9c */ /* b 0x100000b9c */

    /* return value unknown */
    return 0;
}

uint64_t FUN_100000cdc(void)
{
    /* Entry: 0x100000cdc */
    /* Body status: partially_structured */
    /* 1 basic block(s), 9 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m16 = 0;
    u64 stack_48 = 0;
    u64 stack_56 = 0;

    /* Control flow structure: */
    /* block 0x100000cdc */
    tmp_x10 = stack_m16; /* ldur x10,[x29, #-0x10] */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
    tmp_x0 = stack_m16; /* ldur x0,[x29, #-0x10] */
    tmp_fp = stack_48; /* ldp x29,x30,[sp, #0x30] */
    tmp_lr = stack_56; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 64; /* add sp,sp,#0x40 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t byte_halfword_pressure(uint64_t arg1)
{
    /* Entry: 0x100000d00 */
    /* Body status: structured */
    /* 25 basic block(s), 148 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[0, 8, 10, 11, 12, 16, 20, 24, 28, 32, 40], sizes=[1, 2, 4, 8] */
    /*   base=x8, kind=record_like, offsets=[0, 8], sizes=[1, 2, 8] */
    /*   base=x9, kind=record_like, offsets=[0, 80], sizes=[1, 8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 tmp_x27 = 0;
    u64 tmp_x28 = 0;
    u32 tmp_w8 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m24 = 0;
    u64 stack_m32 = 0;
    u64 stack_0 = 0;
    u64 stack_16 = 0;
    u32 stack_20 = 0;
    u64 stack_24 = 0;
    u64 stack_28 = 0;
    u64 stack_32 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* block 0x100000d00 */
    stack_m32 = tmp_x28; /* stp x28,x27,[sp, #-0x20]! */
    stack_m24 = tmp_x27; /* paired store second register inferred offset +8 */
    stack_16 = tmp_fp; /* stp x29,x30,[sp, #0x10] */
    stack_24 = tmp_lr; /* paired store second register inferred offset +8 */
    tmp_fp = tmp_sp + 16; /* add x29,sp,#0x10 */
    tmp_sp = tmp_sp - 576; /* sub sp,sp,#0x240 */
    tmp_x8 = 0x100004000; /* adrp x8,0x100004000 */
    tmp_x8 = *(u64 *)(tmp_x8 + 8); /* ldr x8,[x8, #0x8] */
    tmp_x8 = *(u64 *)(tmp_x8); /* ldr x8,[x8] */
    stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
    stack_40 = tmp_x0; /* str x0,[sp, #0x28] */
    tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
    stack_32 = tmp_x8; /* str x8,[sp, #0x20] */
    stack_28 = 0; /* str wzr,[sp, #0x1c] */
    /* branch to 0x100000d34 */ /* b 0x100000d34 */
    /* loop kind: while_like */
    /* loop header: 0x100000d34 */
    /* loop exits: ['0x100000d7c'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000d3c after subs at 0x100000d38; target 0x100000d7c; loop polarity inverted")) {
        /* block 0x100000d34 */
        tmp_w8 = stack_28; /* ldr w8,[sp, #0x1c] */
        tmp_w8 = tmp_w8 - 257; /* subs w8,w8,#0x101; flags updated */
        /* conditional branch b.ge -> 0x100000d7c */
        /* block 0x100000d40 */
        /* branch to 0x100000d44 */ /* b 0x100000d44 */
        /* block 0x100000d44 */
        tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
        tmp_x9 = (i64)(i32)stack_28; /* ldrsw x9,[sp, #0x1c] */
        tmp_x10 = 13; /* mov x10,#0xd */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x8 = tmp_x8 & 255; /* and x8,x8,#0xff */
        tmp_x10 = (i64)(i32)stack_28; /* ldrsw x10,[sp, #0x1c] */
        tmp_x9 = tmp_sp + 311; /* add x9,sp,#0x137 */
        *(u8 *)(tmp_x9 + tmp_x10) = tmp_w8; /* strb w8,[x9, x10, LSL ] */
        /* branch to 0x100000d6c */ /* b 0x100000d6c */
        /* block 0x100000d6c */
        tmp_w8 = stack_28; /* ldr w8,[sp, #0x1c] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_28 = tmp_w8; /* str w8,[sp, #0x1c] */
        /* branch to 0x100000d34 */ /* b 0x100000d34 */
    }
    /* block 0x100000d7c */
    stack_24 = 0; /* str wzr,[sp, #0x18] */
    /* branch to 0x100000d84 */ /* b 0x100000d84 */
    /* loop kind: while_like */
    /* loop header: 0x100000d84 */
    /* loop exits: ['0x100000dcc'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000d8c after subs at 0x100000d88; target 0x100000dcc; loop polarity inverted")) {
        /* block 0x100000d84 */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w8 = tmp_w8 - 129; /* subs w8,w8,#0x81; flags updated */
        /* conditional branch b.ge -> 0x100000dcc */
        /* block 0x100000d90 */
        /* branch to 0x100000d94 */ /* b 0x100000d94 */
        /* block 0x100000d94 */
        tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
        tmp_x9 = (i64)(i32)stack_24; /* ldrsw x9,[sp, #0x18] */
        tmp_x10 = 97; /* mov x10,#0x61 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        tmp_x8 = tmp_x8 & 65535; /* and x8,x8,#0xffff */
        tmp_x10 = (i64)(i32)stack_24; /* ldrsw x10,[sp, #0x18] */
        tmp_x9 = tmp_sp + 52; /* add x9,sp,#0x34 */
        *(u16 *)(tmp_x9 + (tmp_x10 << 1)) = tmp_w8; /* strh w8,[x9, x10, LSL #0x1] */
        /* branch to 0x100000dbc */ /* b 0x100000dbc */
        /* block 0x100000dbc */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_24 = tmp_w8; /* str w8,[sp, #0x18] */
        /* branch to 0x100000d84 */ /* b 0x100000d84 */
    }
    /* block 0x100000dcc */
    stack_20 = 0; /* str wzr,[sp, #0x14] */
    /* branch to 0x100000dd4 */ /* b 0x100000dd4 */
    /* loop kind: while_like */
    /* loop header: 0x100000dd4 */
    /* loop exits: ['0x100000ee4', '0x100000f00'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000ddc after subs at 0x100000dd8; target 0x100000f00; loop polarity inverted")) {
        /* if/else condition block: 0x100000dd4 */
        /* merge block: 0x100000ef0 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000ddc after subs at 0x100000dd8; target 0x100000f00")) {
            /* block 0x100000ecc */
            /* branch to 0x100000ed0 */ /* b 0x100000ed0 */
            /* block 0x100000ed0 */
            /* branch to 0x100000ef0 */ /* b 0x100000ef0 */
        } else {
            /* block 0x100000ed4 */
            tmp_x8 = stack_32; /* ldr x8,[sp, #0x20] */
            tmp_x8 = tmp_x8 & 4095; /* and x8,x8,#0xfff */
            tmp_x8 = tmp_x8 - 2748; /* subs x8,x8,#0xabc; flags updated */
            /* conditional branch b.ne -> 0x100000eec */
            /* block 0x100000eec */
            /* branch to 0x100000ef0 */ /* b 0x100000ef0 */
        }
        /* block 0x100000ef0 */
        tmp_w8 = stack_20; /* ldr w8,[sp, #0x14] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_20 = tmp_w8; /* str w8,[sp, #0x14] */
        /* branch to 0x100000dd4 */ /* b 0x100000dd4 */
    }
    /* block 0x100000ee4 */
    /* branch to 0x100000ee8 */ /* b 0x100000ee8 */
    /* block 0x100000ee8 */
    /* branch to 0x100000f00 */ /* b 0x100000f00 */
    /* if/else condition block: 0x100000f00 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.eq at 0x100000f30 after subs at 0x100000f2c; target 0x100000f3c; polarity inverted")) {
        /* block 0x100000f34 */
        /* branch to 0x100000f38 */ /* b 0x100000f38 */
        /* block 0x100000f38 */
        call_0x100001ab8(); /* bl 0x100001ab8 */
    } else {
        /* block 0x100000f3c */
        tmp_x0 = stack_0; /* ldr x0,[sp] */
        tmp_sp = tmp_sp + 576; /* add sp,sp,#0x240 */
        tmp_fp = stack_16; /* ldp x29,x30,[sp, #0x10] */
        tmp_lr = stack_24; /* paired load second register inferred offset +8 */
        /* unsupported paired load: ldp x28,x27,[sp], #0x20 */
        return tmp_x0; /* return value from x0 before ret */
    }

}

uint64_t stack_layout_pressure(int32_t arg1)
{
    /* Entry: 0x100000f50 */
    /* Body status: structured */
    /* 40 basic block(s), 227 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[8, 16, 20, 24, 28, 32, 36, 40, 48], sizes=[4] */
    /*   base=x8, kind=array_like, offsets=[0, 8], sizes=[4] */
    /*   base=x9, kind=array_like, offsets=[0, 80], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 tmp_x27 = 0;
    u64 tmp_x28 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m24 = 0;
    u64 stack_m32 = 0;
    u64 stack_0 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u32 stack_20 = 0;
    u64 stack_24 = 0;
    u64 stack_28 = 0;
    u64 stack_32 = 0;
    u64 stack_36 = 0;
    u64 stack_40 = 0;
    u64 stack_48 = 0;

    /* Control flow structure: */
    /* block 0x100000f50 */
    stack_m32 = tmp_x28; /* stp x28, x27, [sp, -0x20]! */
    stack_m24 = tmp_x27; /* paired store second register inferred offset +8 */
    stack_16 = tmp_fp; /* stp x29, x30, [sp + var_10h_2] */
    stack_24 = tmp_lr; /* paired store second register inferred offset +8 */
    tmp_fp = tmp_sp + 16; /* add x29, sp, 0x10 */
    tmp_sp = tmp_sp - 960; /* sub sp, sp, 0x3c0 */
    tmp_x8 = 0x100004000; /* adrp x8, reloc.__stack_chk_fail */
    tmp_x8 = *(u64 *)(tmp_x8 + 8); /* ldr x8, [x8, 8] */
    tmp_x8 = *(u64 *)(tmp_x8); /* ldr x8, [x8] */
    stack_m24 = tmp_x8; /* stur x8, [x29, -0x18] */
    stack_48 = tmp_x0; /* str x0, [sp + var_30h] */
    tmp_x8 = stack_48; /* ldr x8, [sp + var_30h] */
    stack_40 = tmp_x8; /* str x8, [sp + var_28h] */
    stack_36 = 0; /* str wzr, [sp + var_24h] */
    /* branch to 0x100000f84 */ /* b 0x100000f84 */
    /* loop kind: while_like */
    /* loop header: 0x100000f84 */
    /* loop exits: ['0x100000fcc'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000f8c after subs at 0x100000f88; target 0x100000fcc; loop polarity inverted")) {
        /* block 0x100000f84 */
        tmp_w8 = stack_36; /* ldr w8, [sp + var_24h] */
        tmp_w8 = tmp_w8 - 40; /* subs w8, w8, 0x28; flags updated */
        /* conditional branch b.ge -> 0x100000fcc */
        /* block 0x100000f90 */
        /* branch to 0x100000f94 */ /* b 0x100000f94 */
        /* block 0x100000f94 */
        tmp_x8 = stack_40; /* ldr x8, [sp + var_28h] */
        tmp_x9 = (i64)(i32)stack_36; /* ldrsw x9, [sp + var_24h] */
        tmp_x10 = 17; /* mov x10, 0x11 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9, x9, x10 */
        tmp_x0 = tmp_x8 + tmp_x9; /* add x0, x8, x9 */
        call_0x1000014a8(tmp_x0); /* bl sym._rotmix; args refined from same-block evidence */
        tmp_x9 = (i64)(i32)stack_36; /* ldrsw x9, [sp + var_24h] */
        tmp_x8 = tmp_sp + 632; /* add x8, sp, 0x278 */
        *(u64 *)(tmp_x8) = tmp_x0; /* str x0, [x8, x9, lsl 3] */
        /* branch to 0x100000fbc */ /* b 0x100000fbc */
        /* block 0x100000fbc */
        tmp_w8 = stack_36; /* ldr w8, [sp + var_24h] */
        tmp_w8 = tmp_w8 + 1; /* add w8, w8, 1 */
        stack_36 = tmp_w8; /* str w8, [sp + var_24h] */
        /* branch to 0x100000f84 */ /* b 0x100000f84 */
    }
    /* block 0x100000fcc */
    stack_32 = 0; /* str wzr, [sp + var_20h] */
    /* branch to 0x100000fd4 */ /* b 0x100000fd4 */
    /* loop kind: while_like */
    /* loop header: 0x100000fd4 */
    /* loop exits: ['0x100001018'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000fdc after subs at 0x100000fd8; target 0x100001018; loop polarity inverted")) {
        /* block 0x100000fd4 */
        tmp_w8 = stack_32; /* ldr w8, [sp + var_20h] */
        tmp_w8 = tmp_w8 - 80; /* subs w8, w8, 0x50; flags updated */
        /* conditional branch b.ge -> 0x100001018 */
        /* block 0x100000fe0 */
        /* branch to 0x100000fe4 */ /* b 0x100000fe4 */
        /* block 0x100000fe4 */
        tmp_x8 = stack_40; /* ldr x8, [sp + var_28h] */
        tmp_x9 = (i64)(i32)stack_32; /* ldrsw x9, [sp + var_20h] */
        tmp_x10 = 33; /* mov x10, 0x21 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9, x9, x10 */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8, x8, x9 */
        tmp_x10 = (i64)(i32)stack_32; /* ldrsw x10, [sp + var_20h] */
        tmp_x9 = tmp_sp + 312; /* add x9, sp, 0x138 */
        *(u32 *)(tmp_x9) = tmp_w8; /* str w8, [x9, x10, lsl 2] */
        /* branch to 0x100001008 */ /* b 0x100001008 */
        /* block 0x100001008 */
        tmp_w8 = stack_32; /* ldr w8, [sp + var_20h] */
        tmp_w8 = tmp_w8 + 1; /* add w8, w8, 1 */
        stack_32 = tmp_w8; /* str w8, [sp + var_20h] */
        /* branch to 0x100000fd4 */ /* b 0x100000fd4 */
    }
    /* block 0x100001018 */
    stack_28 = 0; /* str wzr, [sp + var_1ch] */
    /* branch to 0x100001020 */ /* b 0x100001020 */
    /* loop kind: while_like */
    /* loop header: 0x100001020 */
    /* loop exits: ['0x100001064'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100001028 after subs at 0x100001024; target 0x100001064; loop polarity inverted")) {
        /* block 0x100001020 */
        tmp_w8 = stack_28; /* ldr w8, [sp + var_1ch] */
        tmp_w8 = tmp_w8 - 64; /* subs w8, w8, 0x40; flags updated */
        /* conditional branch b.ge -> 0x100001064 */
        /* block 0x10000102c */
        /* branch to 0x100001030 */ /* b 0x100001030 */
        /* block 0x100001030 */
        tmp_x8 = stack_40; /* ldr x8, [sp + var_28h] */
        tmp_x9 = (i64)(i32)stack_28; /* ldrsw x9, [sp + var_1ch] */
        tmp_x10 = 11; /* mov x10, 0xb */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9, x9, x10 */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8, x8, x9 */
        tmp_x10 = (i64)(i32)stack_28; /* ldrsw x10, [sp + var_1ch] */
        tmp_x9 = tmp_sp + 184; /* add x9, sp, 0xb8 */
        *(u16 *)(tmp_x9) = tmp_w8; /* strh w8, [x9, x10, lsl 1] */
        /* branch to 0x100001054 */ /* b 0x100001054 */
        /* block 0x100001054 */
        tmp_w8 = stack_28; /* ldr w8, [sp + var_1ch] */
        tmp_w8 = tmp_w8 + 1; /* add w8, w8, 1 */
        stack_28 = tmp_w8; /* str w8, [sp + var_1ch] */
        /* branch to 0x100001020 */ /* b 0x100001020 */
    }
    /* block 0x100001064 */
    stack_24 = 0; /* str wzr, [sp + var_18h] */
    /* branch to 0x10000106c */ /* b 0x10000106c */
    /* loop kind: while_like */
    /* loop header: 0x10000106c */
    /* loop exits: ['0x1000010ac'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100001074 after subs at 0x100001070; target 0x1000010ac; loop polarity inverted")) {
        /* block 0x10000106c */
        tmp_w8 = stack_24; /* ldr w8, [sp + var_18h] */
        tmp_w8 = tmp_w8 - 128; /* subs w8, w8, 0x80; flags updated */
        /* conditional branch b.ge -> 0x1000010ac */
        /* block 0x100001078 */
        /* branch to 0x10000107c */ /* b 0x10000107c */
        /* block 0x10000107c */
        tmp_x8 = stack_40; /* ldr x8, [sp + var_28h] */
        tmp_w9 = stack_24; /* ldr w9, [sp + var_18h] */
        tmp_w9 = tmp_w9 & 7; /* and w9, w9, 7 */
        tmp_x8 = tmp_x8 >> tmp_x9; /* lsr x8, x8, x9 */
        tmp_x10 = (i64)(i32)stack_24; /* ldrsw x10, [sp + var_18h] */
        tmp_x9 = tmp_sp + 56; /* add x9, sp, 0x38 */
        *(u8 *)(tmp_x9) = tmp_w8; /* strb w8, [x9, x10] */
        /* branch to 0x10000109c */ /* b 0x10000109c */
        /* block 0x10000109c */
        tmp_w8 = stack_24; /* ldr w8, [sp + var_18h] */
        tmp_w8 = tmp_w8 + 1; /* add w8, w8, 1 */
        stack_24 = tmp_w8; /* str w8, [sp + var_18h] */
        /* branch to 0x10000106c */ /* b 0x10000106c */
    }
    /* block 0x1000010ac */
    stack_20 = 0; /* str wzr, [sp + var_14h] */
    /* branch to 0x1000010b4 */ /* b 0x1000010b4 */
    /* loop kind: while_like */
    /* loop header: 0x1000010b4 */
    /* loop exits: ['0x10000128c'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000010bc after subs at 0x1000010b8; target 0x10000128c; loop polarity inverted")) {
        /* if condition block: 0x1000010b4 */
        /* merge block: 0x100001278 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000010bc after subs at 0x1000010b8; target 0x10000128c")) {
            /* block 0x1000011d0 */
            /* branch to 0x1000011d4 */ /* b 0x1000011d4 */
            /* block 0x1000011d4 */
            /* branch to 0x100001278 */ /* b 0x100001278 */
        }
        /* block 0x100001278 */
        /* branch to 0x10000127c */ /* b 0x10000127c */
        /* block 0x10000127c */
        tmp_w8 = stack_20; /* ldr w8, [sp + var_14h] */
        tmp_w8 = tmp_w8 + 1; /* add w8, w8, 1 */
        stack_20 = tmp_w8; /* str w8, [sp + var_14h] */
        /* branch to 0x1000010b4 */ /* b 0x1000010b4 */
    }
    /* if/else condition block: 0x10000128c */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.eq at 0x1000012bc after subs at 0x1000012b8; target 0x1000012c8; polarity inverted")) {
        /* block 0x1000012c0 */
        /* branch to 0x1000012c4 */ /* b 0x1000012c4 */
        /* block 0x1000012c4 */
        call_0x100001ab8(); /* bl sym.imp.__stack_chk_fail */
    } else {
        /* block 0x1000012c8 */
        tmp_x0 = stack_8; /* ldr x0, [sp + var_8h] */
        tmp_sp = tmp_sp + 960; /* add sp, sp, 0x3c0 */
        tmp_fp = stack_16; /* ldp x29, x30, [sp + var_10h_2] */
        tmp_lr = stack_24; /* paired load second register inferred offset +8 */
        tmp_x28 = stack_0; /* ldp x28, x27, [sp], 0x20 */
        tmp_x27 = stack_8; /* paired load second register inferred offset +8 */
        return tmp_x0; /* return value from x0 before ret */
    }

}

uint64_t FUN_100001020(void)
{
    /* Entry: 0x100001020 */
    /* Body status: structured */
    /* 3 basic block(s), 13 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[28, 40], sizes=[4, 8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u64 stack_28 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* block 0x100001020 */
    tmp_w8 = stack_28; /* ldr w8,[sp, #0x1c] */
    tmp_w8 = tmp_w8 - 64; /* subs w8,w8,#0x40; flags updated */
    /* conditional branch b.ge -> 0x100001064 */
    /* block 0x10000102c */
    /* branch to 0x100001030 */ /* b 0x100001030 */
    /* block 0x100001030 */
    tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
    tmp_x9 = (i64)(i32)stack_28; /* ldrsw x9,[sp, #0x1c] */
    tmp_x10 = 11; /* mov x10,#0xb */
    tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    tmp_x10 = (i64)(i32)stack_28; /* ldrsw x10,[sp, #0x1c] */
    tmp_x9 = tmp_sp + 184; /* add x9,sp,#0xb8 */
    *(u16 *)(tmp_x9 + (tmp_x10 << 1)) = tmp_w8; /* strh w8,[x9, x10, LSL #0x1] */
    /* branch to 0x100001054 */ /* b 0x100001054 */

    /* return value unknown */
    return 0;
}

uint64_t abi_pressure(void)
{
    /* Entry: 0x100001054 */
    /* Body status: unstructured */
    /* 10 basic block(s), 30 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[16, 20, 24, 28, 40], sizes=[4, 8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u64 stack_16 = 0;
    u32 stack_20 = 0;
    u64 stack_24 = 0;
    u32 stack_28 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: fragmented_loop_body */
    {
        /* block 0x100001054 */
        tmp_w8 = stack_28; /* ldr w8,[sp, #0x1c] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_28 = tmp_w8; /* str w8,[sp, #0x1c] */
        /* branch to 0x100001020 */ /* b 0x100001020 */
        /* block 0x100001064 */
        stack_24 = 0; /* str wzr,[sp, #0x18] */
        /* branch to 0x10000106c */ /* b 0x10000106c */
        /* block 0x10000106c */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w8 = tmp_w8 - 128; /* subs w8,w8,#0x80; flags updated */
        /* conditional branch b.ge -> 0x1000010ac */
        /* block 0x100001078 */
        /* branch to 0x10000107c */ /* b 0x10000107c */
        /* block 0x10000107c */
        tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
        tmp_w9 = stack_24; /* ldr w9,[sp, #0x18] */
        tmp_w9 = tmp_w9 & 7; /* and w9,w9,#0x7 */
        tmp_x8 = tmp_x8 >> tmp_x9; /* lsr x8,x8,x9 */
        tmp_x10 = (i64)(i32)stack_24; /* ldrsw x10,[sp, #0x18] */
        tmp_x9 = tmp_sp + 56; /* add x9,sp,#0x38 */
        *(u8 *)(tmp_x9 + tmp_x10) = tmp_w8; /* strb w8,[x9, x10, LSL ] */
        /* branch to 0x10000109c */ /* b 0x10000109c */
        /* block 0x10000109c */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_24 = tmp_w8; /* str w8,[sp, #0x18] */
        /* branch to 0x10000106c */ /* b 0x10000106c */
        /* block 0x1000010ac */
        stack_20 = 0; /* str wzr,[sp, #0x14] */
        /* branch to 0x1000010b4 */ /* b 0x1000010b4 */
        /* block 0x1000010b4 */
        tmp_w8 = stack_20; /* ldr w8,[sp, #0x14] */
        tmp_w8 = tmp_w8 - 12; /* subs w8,w8,#0xc; flags updated */
        /* conditional branch b.ge -> 0x10000128c */
        /* block 0x1000010c0 */
        /* branch to 0x1000010c4 */ /* b 0x1000010c4 */
        /* block 0x1000010c4 */
        stack_16 = 0; /* str wzr,[sp, #0x10] */
        /* branch to 0x1000010cc */ /* b 0x1000010cc */
    }
    /* unstructured region end */

    /* return value unknown */
    return 0;
}

uint64_t FUN_1000010cc(void)
{
    /* Entry: 0x1000010cc */
    /* Body status: structured */
    /* 9 basic block(s), 85 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[16, 20, 40, 48], sizes=[4, 8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x3 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u64 stack_16 = 0;
    u32 stack_20 = 0;
    u64 stack_40 = 0;
    u64 stack_48 = 0;

    /* Control flow structure: */
    /* block 0x1000010cc */
    tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
    tmp_w8 = tmp_w8 - 40; /* subs w8,w8,#0x28; flags updated */
    /* conditional branch b.ge -> 0x100001278 */
    /* block 0x1000010d8 */
    /* branch to 0x1000010dc */ /* b 0x1000010dc */
    /* block 0x1000010dc */
    tmp_x9 = (i64)(i32)stack_16; /* ldrsw x9,[sp, #0x10] */
    tmp_x8 = tmp_sp + 632; /* add x8,sp,#0x278 */
    tmp_x9 = *(u64 *)(tmp_x8 + (tmp_x9 << 3)); /* ldr x9,[x8, x9, LSL #0x3] */
    tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
    tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
    stack_40 = tmp_x8; /* str x8,[sp, #0x28] */
    tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
    tmp_w9 = 3; /* mov w9,#0x3 */
    tmp_w8 = tmp_w8 * tmp_w9; /* mul w8,w8,w9 */
    tmp_w9 = stack_20; /* ldr w9,[sp, #0x14] */
    tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
    tmp_w10 = 80; /* mov w10,#0x50 */
    tmp_w9 = ((i32)tmp_w8) / ((i32)tmp_w10); /* sdiv w9,w8,w10 */
    tmp_w9 = tmp_w9 * tmp_w10; /* mul w9,w9,w10 */
    tmp_w9 = tmp_w8 - tmp_w9; /* subs w9,w8,w9; flags updated */
    tmp_x8 = tmp_sp + 312; /* add x8,sp,#0x138 */
    tmp_w8 = *(u32 *)(tmp_x8 + (((i64)(i32)tmp_w9) << 2)); /* ldr w8,[x8, w9, SXTW #0x2] */
    tmp_x9 = tmp_x8; /* mov x9,x8 */
    tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    stack_40 = tmp_x8; /* str x8,[sp, #0x28] */
    tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
    tmp_w9 = 5; /* mov w9,#0x5 */
    tmp_w8 = tmp_w8 * tmp_w9; /* mul w8,w8,w9 */
    tmp_w9 = stack_20; /* ldr w9,[sp, #0x14] */
    tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
    tmp_w10 = 64; /* mov w10,#0x40 */
    tmp_w9 = ((i32)tmp_w8) / ((i32)tmp_w10); /* sdiv w9,w8,w10 */
    tmp_w9 = tmp_w9 * tmp_w10; /* mul w9,w9,w10 */
    tmp_w9 = tmp_w8 - tmp_w9; /* subs w9,w8,w9; flags updated */
    tmp_x8 = tmp_sp + 184; /* add x8,sp,#0xb8 */
    tmp_w8 = *(u16 *)(tmp_x8 + (((i64)(i32)tmp_w9) << 1)); /* ldrh w8,[x8, w9, SXTW #0x1] */
    tmp_x9 = tmp_x8; /* mov x9,x8 */
    tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
    tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
    stack_40 = tmp_x8; /* str x8,[sp, #0x28] */
    tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
    tmp_w9 = 7; /* mov w9,#0x7 */
    tmp_w8 = tmp_w8 * tmp_w9; /* mul w8,w8,w9 */
    tmp_w9 = stack_20; /* ldr w9,[sp, #0x14] */
    tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
    tmp_w10 = 128; /* mov w10,#0x80 */
    tmp_w9 = ((i32)tmp_w8) / ((i32)tmp_w10); /* sdiv w9,w8,w10 */
    tmp_w9 = tmp_w9 * tmp_w10; /* mul w9,w9,w10 */
    tmp_w9 = tmp_w8 - tmp_w9; /* subs w9,w8,w9; flags updated */
    tmp_x8 = tmp_sp + 56; /* add x8,sp,#0x38 */
    tmp_w8 = *(u8 *)(tmp_x8 + ((i64)(i32)tmp_w9)); /* ldrb w8,[x8, w9, SXTW ] */
    tmp_x9 = tmp_x8; /* mov x9,x8 */
    tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    stack_40 = tmp_x8; /* str x8,[sp, #0x28] */
    tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
    tmp_x8 = tmp_x8 & 3; /* and x8,x8,#0x3 */
    tmp_x8 = tmp_x8 - 1; /* subs x8,x8,#0x1; flags updated */
    /* conditional branch b.ne -> 0x1000011c0 */
    /* if/else condition block: 0x1000011c0 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ne at 0x1000011cc after subs at 0x1000011c8; target 0x1000011d8; polarity inverted")) {
        /* block 0x1000011d0 */
        /* branch to 0x1000011d4 */ /* b 0x1000011d4 */
        /* block 0x1000011d4 */
        /* branch to 0x100001278 */ /* b 0x100001278 */
    } else {
        /* block 0x1000011d8 */
        tmp_x0 = stack_40; /* ldr x0,[sp, #0x28] */
        tmp_x1 = stack_48; /* ldr x1,[sp, #0x30] */
        tmp_x9 = (i64)(i32)stack_16; /* ldrsw x9,[sp, #0x10] */
        tmp_x8 = tmp_sp + 632; /* add x8,sp,#0x278 */
        tmp_x2 = *(u64 *)(tmp_x8 + (tmp_x9 << 3)); /* ldr x2,[x8, x9, LSL #0x3] */
        tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
        tmp_w10 = 80; /* mov w10,#0x50 */
        tmp_w9 = ((i32)tmp_w8) / ((i32)tmp_w10); /* sdiv w9,w8,w10 */
        tmp_w9 = tmp_w9 * tmp_w10; /* mul w9,w9,w10 */
        tmp_w9 = tmp_w8 - tmp_w9; /* subs w9,w8,w9; flags updated */
        tmp_x8 = tmp_sp + 312; /* add x8,sp,#0x138 */
        tmp_w8 = *(u32 *)(tmp_x8 + (((i64)(i32)tmp_w9) << 2)); /* ldr w8,[x8, w9, SXTW #0x2] */
        tmp_x3 = tmp_x8; /* mov x3,x8 */
        tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
        tmp_w10 = 64; /* mov w10,#0x40 */
        tmp_w9 = ((i32)tmp_w8) / ((i32)tmp_w10); /* sdiv w9,w8,w10 */
        tmp_w9 = tmp_w9 * tmp_w10; /* mul w9,w9,w10 */
        tmp_w9 = tmp_w8 - tmp_w9; /* subs w9,w8,w9; flags updated */
    }
    /* block 0x1000011b8 */
    /* branch to 0x1000011bc */ /* b 0x1000011bc */
    /* block 0x1000011bc */
    /* branch to 0x100001268 */ /* b 0x100001268 */

    /* return value unknown */
    return 0;
}

uint64_t rotmix(void)
{
    /* Entry: 0x100001220 */
    /* Body status: structured */
    /* 2 basic block(s), 18 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[16, 20, 40], sizes=[4, 8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x3 = 0;
    u64 tmp_x4 = 0;
    u64 tmp_x5 = 0;
    u64 tmp_x6 = 0;
    u64 tmp_x7 = 0;
    u64 tmp_x8 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u64 stack_16 = 0;
    u64 stack_20 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* block 0x100001220 */
    tmp_x8 = tmp_sp + 184; /* add x8,sp,#0xb8 */
    tmp_w8 = *(u16 *)(tmp_x8 + (((i64)(i32)tmp_w9) << 1)); /* ldrh w8,[x8, w9, SXTW #0x1] */
    tmp_x4 = tmp_x8; /* mov x4,x8 */
    tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
    tmp_w10 = 128; /* mov w10,#0x80 */
    tmp_w9 = ((i32)tmp_w8) / ((i32)tmp_w10); /* sdiv w9,w8,w10 */
    tmp_w9 = tmp_w9 * tmp_w10; /* mul w9,w9,w10 */
    tmp_w9 = tmp_w8 - tmp_w9; /* subs w9,w8,w9; flags updated */
    tmp_x8 = tmp_sp + 56; /* add x8,sp,#0x38 */
    tmp_w8 = *(u8 *)(tmp_x8 + ((i64)(i32)tmp_w9)); /* ldrb w8,[x8, w9, SXTW ] */
    tmp_x5 = tmp_x8; /* mov x5,x8 */
    tmp_x6 = (i64)(i32)stack_20; /* ldrsw x6,[sp, #0x14] */
    tmp_x7 = (i64)(i32)stack_16; /* ldrsw x7,[sp, #0x10] */
    call_0x1000012dc(tmp_x0, tmp_x1, tmp_x2, tmp_x3, tmp_x4, tmp_x5, tmp_x6, tmp_x7); /* bl 0x1000012dc; args refined from same-block evidence */
    /* block 0x100001258 */
    tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
    stack_40 = tmp_x8; /* str x8,[sp, #0x28] */
    /* branch to 0x100001268 */ /* b 0x100001268 */

    /* return value unknown */
    return 0;
}

uint64_t FUN_100001268(void)
{
    /* Entry: 0x100001268 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 4 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=scalar, offsets=[16], sizes=[4] */

    /* Conservative pseudo declarations: */
    u32 tmp_w8 = 0;
    u32 stack_16 = 0;

    /* Control flow structure: */
    /* block 0x100001268 */
    tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
    tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
    stack_16 = tmp_w8; /* str w8,[sp, #0x10] */
    /* branch to 0x1000010cc */ /* b 0x1000010cc */

    /* return value unknown */
    return 0;
}

uint64_t FUN_100001278(void)
{
    /* Entry: 0x100001278 */
    /* Body status: unstructured */
    /* 3 basic block(s), 14 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[8, 20, 40], sizes=[4, 8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u64 stack_m24 = 0;
    u64 stack_8 = 0;
    u32 stack_20 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: fragmented_loop_body */
    {
        /* block 0x100001278 */
        /* branch to 0x10000127c */ /* b 0x10000127c */
        /* block 0x10000127c */
        tmp_w8 = stack_20; /* ldr w8,[sp, #0x14] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_20 = tmp_w8; /* str w8,[sp, #0x14] */
        /* branch to 0x1000010b4 */ /* b 0x1000010b4 */
        /* block 0x10000128c */
        tmp_x10 = stack_40; /* ldr x10,[sp, #0x28] */
        tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
        tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
        tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
        *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
        tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
        stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
        tmp_x9 = stack_m24; /* ldur x9,[x29, #-0x18] */
        tmp_x8 = 0x100004000; /* adrp x8,0x100004000 */
    }
    /* unstructured region end */

    /* return value unknown */
    return 0;
}

uint64_t op_add(void)
{
    /* Entry: 0x1000012b0 */
    /* Body status: structured */
    /* 4 basic block(s), 11 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=pointer_like, offsets=[8], sizes=[8] */
    /*   base=x8, kind=array_like, offsets=[0, 8], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;

    /* Control flow structure: */
    /* if/else condition block: 0x1000012b0 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.eq at 0x1000012bc after subs at 0x1000012b8; target 0x1000012c8; polarity inverted")) {
        /* block 0x1000012c0 */
        /* branch to 0x1000012c4 */ /* b 0x1000012c4 */
        /* block 0x1000012c4 */
        call_0x100001ab8(); /* bl 0x100001ab8 */
    } else {
        /* block 0x1000012c8 */
        tmp_x0 = stack_8; /* ldr x0,[sp, #0x8] */
        tmp_sp = tmp_sp + 960; /* add sp,sp,#0x3c0 */
        tmp_fp = stack_16; /* ldp x29,x30,[sp, #0x10] */
        tmp_lr = stack_24; /* paired load second register inferred offset +8 */
        /* unsupported paired load: ldp x28,x27,[sp], #0x20 */
        return tmp_x0; /* return value from x0 before ret */
    }

}

uint64_t abi_pressure(uint64_t arg1, int32_t arg2, uint64_t arg3, int32_t arg4, uint64_t arg5, int32_t arg6, uint64_t arg7, uint64_t arg8, uint64_t arg_60h)
{
    /* Entry: 0x1000012dc */
    /* Body status: structured */
    /* 12 basic block(s), 115 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[0, 8, 16, 24, 32, 40], sizes=[4] */
    /*   base=x9, kind=scalar, offsets=[80], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x3 = 0;
    u64 tmp_x4 = 0;
    u64 tmp_x5 = 0;
    u64 tmp_x6 = 0;
    u64 tmp_x7 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m8 = 0;
    u64 stack_m16 = 0;
    u64 stack_m24 = 0;
    u64 stack_m32 = 0;
    u64 stack_0 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;
    u64 stack_32 = 0;
    u64 stack_40 = 0;
    u64 stack_80 = 0;
    u64 stack_88 = 0;

    /* Control flow structure: */
    /* block 0x1000012dc */
    tmp_sp = tmp_sp - 96; /* sub sp, sp, 0x60 */
    stack_80 = tmp_fp; /* stp x29, x30, [sp + var_50h] */
    stack_88 = tmp_lr; /* paired store second register inferred offset +8 */
    tmp_fp = tmp_sp + 80; /* add x29, sp, 0x50 */
    stack_m8 = tmp_x0; /* stur x0, [x29, -8] */
    stack_m16 = tmp_x1; /* stur x1, [x29, -0x10] */
    stack_m24 = tmp_x2; /* stur x2, [x29, -0x18] */
    stack_m32 = tmp_x3; /* stur x3, [x29, -0x20] */
    stack_40 = tmp_x4; /* str x4, [sp + var_28h] */
    stack_32 = tmp_x5; /* str x5, [sp + var_20h] */
    stack_24 = tmp_x6; /* str x6, [sp + var_18h] */
    stack_16 = tmp_x7; /* str x7, [sp + var_10h] */
    tmp_x8 = stack_m8; /* ldur x8, [x29, -8] */
    tmp_x9 = stack_m16; /* ldur x9, [x29, -0x10] */
    tmp_x8 = tmp_x8 ^ (tmp_x9 << 0); /* eor x8, x8, x9, lsl 1 */
    tmp_x9 = stack_m24; /* ldur x9, [x29, -0x18] */
    tmp_x8 = tmp_x8 ^ (tmp_x9 >> 0); /* eor x8, x8, x9, lsr 1 */
    tmp_x9 = stack_m32; /* ldur x9, [x29, -0x20] */
    tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8, x8, x9 */
    stack_8 = tmp_x8; /* str x8, [sp + var_8h] */
    tmp_x0 = stack_40; /* ldr x0, [sp + var_28h] */
    tmp_x1 = stack_32; /* ldr x1, [sp + var_20h] */
    call_0x100001538(tmp_x0, tmp_x1); /* bl sym._op_add; args refined from same-block evidence */
    tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
    tmp_x8 = tmp_x8 + tmp_x0; /* add x8, x8, x0 */
    stack_8 = tmp_x8; /* str x8, [sp + var_8h] */
    tmp_x0 = stack_24; /* ldr x0, [sp + var_18h] */
    tmp_x1 = stack_16; /* ldr x1, [sp + var_10h] */
    call_0x10000157c(tmp_x0, tmp_x1); /* bl sym._op_xor; args refined from same-block evidence */
    tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8, x8, x0 */
    stack_8 = tmp_x8; /* str x8, [sp + var_8h] */
    tmp_x0 = stack_8; /* ldr x0, [sp + var_8h] */
    tmp_x1 = stack_m8; /* ldur x1, [x29, -8] */
    call_0x1000015c0(tmp_x0, tmp_x1); /* bl sym._op_mul; args refined from same-block evidence */
    tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
    tmp_x8 = tmp_x8 + tmp_x0; /* add x8, x8, x0 */
    stack_8 = tmp_x8; /* str x8, [sp + var_8h] */
    tmp_x0 = stack_m16; /* ldur x0, [x29, -0x10] */
    tmp_x1 = stack_8; /* ldr x1, [sp + var_8h] */
    call_0x10000160c(tmp_x0, tmp_x1); /* bl sym._op_shift; args refined from same-block evidence */
    tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8, x8, x0 */
    stack_8 = tmp_x8; /* str x8, [sp + var_8h] */
    tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
    tmp_x0 = tmp_x8 + 17; /* add x0, x8, 0x11 */
    tmp_x8 = stack_m24; /* ldur x8, [x29, -0x18] */
    tmp_x1 = tmp_x8 | 1; /* orr x1, x8, 1 */
    call_0x100001664(tmp_x0, tmp_x1); /* bl sym._op_div; args refined from same-block evidence */
    tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
    tmp_x8 = tmp_x8 + tmp_x0; /* add x8, x8, x0 */
    stack_8 = tmp_x8; /* str x8, [sp + var_8h] */
    tmp_x0 = stack_m32; /* ldur x0, [x29, -0x20] */
    tmp_x1 = stack_40; /* ldr x1, [sp + var_28h] */
    call_0x1000016cc(tmp_x0, tmp_x1); /* bl sym._op_logic; args refined from same-block evidence */
    tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8, x8, x0 */
    stack_8 = tmp_x8; /* str x8, [sp + var_8h] */
    stack_0 = 0; /* str xzr, [sp] */
    /* branch to 0x1000013c8 */ /* b 0x1000013c8 */
    /* loop kind: while_like */
    /* loop header: 0x1000013c8 */
    /* loop exits: ['0x100001468', '0x100001484'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.hs at 0x1000013d0 after subs at 0x1000013cc; target 0x100001484; loop polarity inverted")) {
        /* if/else condition block: 0x1000013c8 */
        /* merge block: 0x100001474 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.hs at 0x1000013d0 after subs at 0x1000013cc; target 0x100001484")) {
            /* block 0x100001450 */
            /* branch to 0x100001454 */ /* b 0x100001454 */
            /* block 0x100001454 */
            /* branch to 0x100001474 */ /* b 0x100001474 */
        } else {
            /* block 0x100001458 */
            tmp_x8 = stack_8; /* ldr x8, [sp + var_8h] */
            tmp_x8 = tmp_x8 & 127; /* and x8, x8, 0x7f */
            tmp_x8 = tmp_x8 - 99; /* subs x8, x8, 0x63; flags updated */
            /* conditional branch b.ne -> 0x100001470 */
            /* block 0x100001470 */
            /* branch to 0x100001474 */ /* b 0x100001474 */
        }
        /* block 0x100001474 */
        tmp_x8 = stack_0; /* ldr x8, [sp] */
        tmp_x8 = tmp_x8 + 1; /* add x8, x8, 1 */
        stack_0 = tmp_x8; /* str x8, [sp] */
        /* branch to 0x1000013c8 */ /* b 0x1000013c8 */
    }
    /* block 0x100001468 */
    /* branch to 0x10000146c */ /* b 0x10000146c */
    /* block 0x10000146c */
    /* branch to 0x100001484 */ /* b 0x100001484 */
    /* block 0x100001484 */
    tmp_x10 = stack_8; /* ldr x10, [sp + var_8h] */
    tmp_x9 = 0x100008000; /* adrp x9, 0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8, [x9, 0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8, x8, x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8, [x9, 0x50] */
    tmp_x0 = stack_8; /* ldr x0, [sp + var_8h] */
    tmp_fp = stack_80; /* ldp x29, x30, [sp + var_50h] */
    tmp_lr = stack_88; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 96; /* add sp, sp, 0x60 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t op_xor(void)
{
    /* Entry: 0x1000012f4 */
    /* Body status: structured */
    /* 2 basic block(s), 17 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 16, 24, 32, 40], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x3 = 0;
    u64 tmp_x4 = 0;
    u64 tmp_x5 = 0;
    u64 tmp_x6 = 0;
    u64 tmp_x7 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 stack_m8 = 0;
    u64 stack_m16 = 0;
    u64 stack_m24 = 0;
    u64 stack_m32 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;
    u64 stack_32 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* block 0x1000012f4 */
    stack_m32 = tmp_x3; /* stur x3,[x29, #-0x20] */
    stack_40 = tmp_x4; /* str x4,[sp, #0x28] */
    stack_32 = tmp_x5; /* str x5,[sp, #0x20] */
    stack_24 = tmp_x6; /* str x6,[sp, #0x18] */
    stack_16 = tmp_x7; /* str x7,[sp, #0x10] */
    tmp_x8 = stack_m8; /* ldur x8,[x29, #-0x8] */
    tmp_x9 = stack_m16; /* ldur x9,[x29, #-0x10] */
    tmp_x8 = tmp_x8 ^ (tmp_x9 << 1); /* eor x8,x8,x9, LSL #0x1 */
    tmp_x9 = stack_m24; /* ldur x9,[x29, #-0x18] */
    tmp_x8 = tmp_x8 ^ (tmp_x9 >> 1); /* eor x8,x8,x9, LSR #0x1 */
    tmp_x9 = stack_m32; /* ldur x9,[x29, #-0x20] */
    tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x0 = stack_40; /* ldr x0,[sp, #0x28] */
    tmp_x1 = stack_32; /* ldr x1,[sp, #0x20] */
    call_0x100001538(tmp_x0, tmp_x1); /* bl 0x100001538; args refined from same-block evidence */
    /* block 0x100001334 */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */

    /* return value unknown */
    return 0;
}

uint64_t op_mul(void)
{
    /* Entry: 0x100001338 */
    /* Body status: structured */
    /* 4 basic block(s), 19 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 16, 24], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x8 = 0;
    u64 stack_m8 = 0;
    u64 stack_m16 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;

    /* Control flow structure: */
    /* block 0x100001338 */
    tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x0 = stack_24; /* ldr x0,[sp, #0x18] */
    tmp_x1 = stack_16; /* ldr x1,[sp, #0x10] */
    call_0x10000157c(tmp_x0, tmp_x1); /* bl 0x10000157c; args refined from same-block evidence */
    /* block 0x10000134c */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x0 = stack_8; /* ldr x0,[sp, #0x8] */
    tmp_x1 = stack_m8; /* ldur x1,[x29, #-0x8] */
    call_0x1000015c0(tmp_x0, tmp_x1); /* bl 0x1000015c0; args refined from same-block evidence */
    /* block 0x100001364 */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x0 = stack_m16; /* ldur x0,[x29, #-0x10] */
    tmp_x1 = stack_8; /* ldr x1,[sp, #0x8] */
    call_0x10000160c(tmp_x0, tmp_x1); /* bl 0x10000160c; args refined from same-block evidence */
    /* block 0x10000137c */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */

    /* return value unknown */
    return 0;
}

uint64_t op_shift(void)
{
    /* Entry: 0x100001384 */
    /* Body status: structured */
    /* 6 basic block(s), 22 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[0, 8, 40], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x8 = 0;
    u64 stack_m8 = 0;
    u64 stack_m24 = 0;
    u64 stack_m32 = 0;
    u64 stack_0 = 0;
    u64 stack_8 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* block 0x100001384 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x0 = tmp_x8 + 17; /* add x0,x8,#0x11 */
    tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
    tmp_x1 = tmp_x8 | 1; /* orr x1,x8,#0x1 */
    call_0x100001664(tmp_x0, tmp_x1); /* bl 0x100001664; args refined from same-block evidence */
    /* block 0x10000139c */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x0 = stack_m32; /* ldur x0,[x29, #-0x20] */
    tmp_x1 = stack_40; /* ldr x1,[sp, #0x28] */
    call_0x1000016cc(tmp_x0, tmp_x1); /* bl 0x1000016cc; args refined from same-block evidence */
    /* block 0x1000013b4 */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    stack_0 = 0; /* str xzr,[sp] */
    /* branch to 0x1000013c8 */ /* b 0x1000013c8 */
    /* block 0x1000013c8 */
    tmp_x8 = stack_0; /* ldr x8,[sp] */
    tmp_x8 = tmp_x8 - 24; /* subs x8,x8,#0x18; flags updated */
    /* conditional branch b.cs -> 0x100001484 */
    /* block 0x1000013d4 */
    /* branch to 0x1000013d8 */ /* b 0x1000013d8 */
    /* block 0x1000013d8 */
    tmp_x8 = stack_m8; /* ldur x8,[x29, #-0x8] */

    /* return value unknown */
    return 0;
}

uint64_t op_div(void)
{
    /* Entry: 0x1000013dc */
    /* Body status: partially_structured */
    /* 1 basic block(s), 26 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[0, 8, 16, 24, 32, 40], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 stack_m16 = 0;
    u64 stack_m24 = 0;
    u64 stack_m32 = 0;
    u64 stack_0 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;
    u64 stack_32 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* block 0x1000013dc */
    tmp_x9 = stack_0; /* ldr x9,[sp] */
    tmp_x9 = tmp_x8 + tmp_x9; /* add x9,x8,x9 */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
    tmp_x9 = stack_0; /* ldr x9,[sp] */
    tmp_x9 = tmp_x8 ^ (tmp_x9 << 2); /* eor x9,x8,x9, LSL #0x2 */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
    tmp_x9 = stack_m32; /* ldur x9,[x29, #-0x20] */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    tmp_x9 = stack_40; /* ldr x9,[sp, #0x28] */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    tmp_x9 = stack_32; /* ldr x9,[sp, #0x20] */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    tmp_x9 = stack_16; /* ldr x9,[sp, #0x10] */
    tmp_x9 = tmp_x8 + tmp_x9; /* add x9,x8,x9 */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */

    /* return value unknown */
    return 0;
}

uint64_t op_logic(void)
{
    /* Entry: 0x100001444 */
    /* Body status: structured */
    /* 9 basic block(s), 21 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[0, 8], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 stack_0 = 0;
    u64 stack_8 = 0;

    /* Control flow structure: */
    /* block 0x100001444 */
    tmp_x8 = tmp_x8 & 7; /* and x8,x8,#0x7 */
    tmp_x8 = tmp_x8 - 2; /* subs x8,x8,#0x2; flags updated */
    /* conditional branch b.ne -> 0x100001458 */
    /* block 0x100001458 */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 & 127; /* and x8,x8,#0x7f */
    tmp_x8 = tmp_x8 - 99; /* subs x8,x8,#0x63; flags updated */
    /* conditional branch b.ne -> 0x100001470 */
    /* block 0x100001470 */
    /* branch to 0x100001474 */ /* b 0x100001474 */
    /* block 0x100001468 */
    /* branch to 0x10000146c */ /* b 0x10000146c */
    /* block 0x10000146c */
    /* branch to 0x100001484 */ /* b 0x100001484 */
    /* block 0x100001484 */
    tmp_x10 = stack_8; /* ldr x10,[sp, #0x8] */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
    /* block 0x100001450 */
    /* branch to 0x100001454 */ /* b 0x100001454 */
    /* block 0x100001454 */
    /* branch to 0x100001474 */ /* b 0x100001474 */
    /* block 0x100001474 */
    tmp_x8 = stack_0; /* ldr x8,[sp] */
    tmp_x8 = tmp_x8 + 1; /* add x8,x8,#0x1 */
    stack_0 = tmp_x8; /* str x8,[sp] */
    /* branch to 0x1000013c8 */ /* b 0x1000013c8 */

    /* return value unknown */
    return 0;
}

uint64_t tri_a(void)
{
    /* Entry: 0x100001498 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 4 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=pointer_like, offsets=[8], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_8 = 0;
    u64 stack_80 = 0;
    u64 stack_88 = 0;

    /* Control flow structure: */
    /* block 0x100001498 */
    tmp_x0 = stack_8; /* ldr x0,[sp, #0x8] */
    tmp_fp = stack_80; /* ldp x29,x30,[sp, #0x50] */
    tmp_lr = stack_88; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 96; /* add sp,sp,#0x60 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t rotmix(uint64_t arg1, uint64_t arg_10h)
{
    /* Entry: 0x1000014a8 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 36 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=pointer_like, offsets=[8], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 stack_8 = 0;

    /* Control flow structure: */
    /* block 0x1000014a8 */
    tmp_sp = tmp_sp - 16; /* sub sp,sp,#0x10 */
    stack_8 = tmp_x0; /* str x0,[sp, #0x8] */
    tmp_x9 = stack_8; /* ldr x9,[sp, #0x8] */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ (tmp_x9 >> 33); /* eor x8,x8,x9, LSR #0x21 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x9 = 36045; /* mov x9,#0x8ccd */
    /* 0x1000014c8: unsupported instruction: movk x9,#0xed55, LSL #16 */
    /* 0x1000014cc: unsupported instruction: movk x9,#0xafd7, LSL #32 */
    /* 0x1000014d0: unsupported instruction: movk x9,#0xff51, LSL #48 */
    tmp_x8 = tmp_x8 * tmp_x9; /* mul x8,x8,x9 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x9 = stack_8; /* ldr x9,[sp, #0x8] */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ (tmp_x9 >> 29); /* eor x8,x8,x9, LSR #0x1d */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x9 = 60499; /* mov x9,#0xec53 */
    /* 0x1000014f4: unsupported instruction: movk x9,#0x1a85, LSL #16 */
    /* 0x1000014f8: unsupported instruction: movk x9,#0xb9fe, LSL #32 */
    /* 0x1000014fc: unsupported instruction: movk x9,#0xc4ce, LSL #48 */
    tmp_x8 = tmp_x8 * tmp_x9; /* mul x8,x8,x9 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x9 = stack_8; /* ldr x9,[sp, #0x8] */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ (tmp_x9 >> 32); /* eor x8,x8,x9, LSR #0x20 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x10 = stack_8; /* ldr x10,[sp, #0x8] */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
    tmp_x0 = stack_8; /* ldr x0,[sp, #0x8] */
    tmp_sp = tmp_sp + 16; /* add sp,sp,#0x10 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t op_add(uint64_t arg1, uint64_t arg2, uint64_t arg_20h)
{
    /* Entry: 0x100001538 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 10 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 16, 24], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;

    /* Control flow structure: */
    /* block 0x100001538 */
    tmp_sp = tmp_sp - 32; /* sub sp,sp,#0x20 */
    stack_24 = tmp_x0; /* str x0,[sp, #0x18] */
    stack_16 = tmp_x1; /* str x1,[sp, #0x10] */
    tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
    tmp_x9 = stack_16; /* ldr x9,[sp, #0x10] */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    tmp_x9 = 4369; /* mov x9,#0x1111 */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x10 = stack_8; /* ldr x10,[sp, #0x8] */

    /* return value unknown */
    return 0;
}

uint64_t tri_b(void)
{
    /* Entry: 0x100001560 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 7 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=pointer_like, offsets=[8], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 stack_8 = 0;

    /* Control flow structure: */
    /* block 0x100001560 */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
    tmp_x0 = stack_8; /* ldr x0,[sp, #0x8] */
    tmp_sp = tmp_sp + 32; /* add sp,sp,#0x20 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t op_xor(uint64_t arg1, uint64_t arg2, uint64_t arg_20h)
{
    /* Entry: 0x10000157c */
    /* Body status: partially_structured */
    /* 1 basic block(s), 17 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 16, 24], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;

    /* Control flow structure: */
    /* block 0x10000157c */
    tmp_sp = tmp_sp - 32; /* sub sp,sp,#0x20 */
    stack_24 = tmp_x0; /* str x0,[sp, #0x18] */
    stack_16 = tmp_x1; /* str x1,[sp, #0x10] */
    tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
    tmp_x9 = stack_16; /* ldr x9,[sp, #0x10] */
    tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
    tmp_x9 = 8738; /* mov x9,#0x2222 */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x10 = stack_8; /* ldr x10,[sp, #0x8] */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
    tmp_x0 = stack_8; /* ldr x0,[sp, #0x8] */
    tmp_sp = tmp_sp + 32; /* add sp,sp,#0x20 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t op_mul(uint64_t arg1, uint64_t arg2, uint64_t arg_20h)
{
    /* Entry: 0x1000015c0 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 19 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 16, 24], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;

    /* Control flow structure: */
    /* block 0x1000015c0 */
    tmp_sp = tmp_sp - 32; /* sub sp,sp,#0x20 */
    stack_24 = tmp_x0; /* str x0,[sp, #0x18] */
    stack_16 = tmp_x1; /* str x1,[sp, #0x10] */
    tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
    tmp_x9 = 33; /* mov x9,#0x21 */
    tmp_x8 = tmp_x8 * tmp_x9; /* mul x8,x8,x9 */
    tmp_x9 = stack_16; /* ldr x9,[sp, #0x10] */
    tmp_x10 = 13107; /* mov x10,#0x3333 */
    tmp_x9 = tmp_x9 + tmp_x10; /* add x9,x9,x10 */
    tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x10 = stack_8; /* ldr x10,[sp, #0x8] */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
    tmp_x0 = stack_8; /* ldr x0,[sp, #0x8] */
    tmp_sp = tmp_sp + 32; /* add sp,sp,#0x20 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t op_shift(uint64_t arg1, uint64_t arg2, uint64_t arg_20h)
{
    /* Entry: 0x10000160c */
    /* Body status: partially_structured */
    /* 1 basic block(s), 15 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 16, 24], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;

    /* Control flow structure: */
    /* block 0x10000160c */
    tmp_sp = tmp_sp - 32; /* sub sp,sp,#0x20 */
    stack_24 = tmp_x0; /* str x0,[sp, #0x18] */
    stack_16 = tmp_x1; /* str x1,[sp, #0x10] */
    tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
    tmp_x9 = stack_16; /* ldr x9,[sp, #0x10] */
    tmp_x9 = tmp_x9 & 7; /* and x9,x9,#0x7 */
    tmp_x8 = tmp_x8 << tmp_x9; /* lsl x8,x8,x9 */
    tmp_x9 = stack_16; /* ldr x9,[sp, #0x10] */
    tmp_x10 = stack_24; /* ldr x10,[sp, #0x18] */
    tmp_x10 = tmp_x10 & 3; /* and x10,x10,#0x3 */
    tmp_x10 = tmp_x10 + 1; /* add x10,x10,#0x1 */
    tmp_x9 = tmp_x9 >> tmp_x10; /* lsr x9,x9,x10 */
    tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x10 = stack_8; /* ldr x10,[sp, #0x8] */

    /* return value unknown */
    return 0;
}

uint64_t tri_c(void)
{
    /* Entry: 0x100001648 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 7 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=pointer_like, offsets=[8], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 stack_8 = 0;

    /* Control flow structure: */
    /* block 0x100001648 */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
    tmp_x0 = stack_8; /* ldr x0,[sp, #0x8] */
    tmp_sp = tmp_sp + 32; /* add sp,sp,#0x20 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t op_div(uint64_t arg1, uint64_t arg2, uint64_t arg_20h)
{
    /* Entry: 0x100001664 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 26 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[0, 8, 16, 24], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 tmp_x11 = 0;
    u64 stack_0 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;

    /* Control flow structure: */
    /* block 0x100001664 */
    tmp_sp = tmp_sp - 32; /* sub sp,sp,#0x20 */
    stack_24 = tmp_x0; /* str x0,[sp, #0x18] */
    stack_16 = tmp_x1; /* str x1,[sp, #0x10] */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_x8 = tmp_x8 | 1; /* orr x8,x8,#0x1 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
    tmp_x9 = stack_8; /* ldr x9,[sp, #0x8] */
    tmp_x8 = tmp_x8 / tmp_x9; /* udiv x8,x8,x9 */
    tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
    tmp_x11 = stack_8; /* ldr x11,[sp, #0x8] */
    tmp_x10 = tmp_x9 / tmp_x11; /* udiv x10,x9,x11 */
    tmp_x10 = tmp_x10 * tmp_x11; /* mul x10,x10,x11 */
    tmp_x9 = tmp_x9 - tmp_x10; /* subs x9,x9,x10; flags updated */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    tmp_x9 = 17476; /* mov x9,#0x4444 */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    stack_0 = tmp_x8; /* str x8,[sp] */
    tmp_x10 = stack_0; /* ldr x10,[sp] */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
    tmp_x0 = stack_0; /* ldr x0,[sp] */
    tmp_sp = tmp_sp + 32; /* add sp,sp,#0x20 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t op_logic(uint64_t arg1, uint64_t arg2, uint64_t arg_20h)
{
    /* Entry: 0x1000016cc */
    /* Body status: partially_structured */
    /* 1 basic block(s), 21 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 16, 24], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;

    /* Control flow structure: */
    /* block 0x1000016cc */
    tmp_sp = tmp_sp - 32; /* sub sp,sp,#0x20 */
    stack_24 = tmp_x0; /* str x0,[sp, #0x18] */
    stack_16 = tmp_x1; /* str x1,[sp, #0x10] */
    tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
    tmp_x9 = stack_16; /* ldr x9,[sp, #0x10] */
    tmp_x8 = tmp_x8 & tmp_x9; /* and x8,x8,x9 */
    tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
    tmp_x10 = stack_16; /* ldr x10,[sp, #0x10] */
    tmp_x9 = tmp_x9 ^ (tmp_x10 << 2); /* eor x9,x9,x10, LSL #0x2 */
    tmp_x8 = tmp_x8 | tmp_x9; /* orr x8,x8,x9 */
    tmp_x9 = 21845; /* mov x9,#0x5555 */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x10 = stack_8; /* ldr x10,[sp, #0x8] */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
    tmp_x0 = stack_8; /* ldr x0,[sp, #0x8] */
    tmp_sp = tmp_sp + 32; /* add sp,sp,#0x20 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t tri_a(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_40h)
{
    /* Entry: 0x100001720 */
    /* Body status: structured */
    /* 14 basic block(s), 50 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[12, 16, 24], sizes=[4, 8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u32 tmp_w8 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m8 = 0;
    u64 stack_m16 = 0;
    u64 stack_12 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;
    u64 stack_48 = 0;
    u64 stack_56 = 0;

    /* Control flow structure: */
    /* block 0x100001720 */
    tmp_sp = tmp_sp - 64; /* sub sp,sp,#0x40 */
    stack_48 = tmp_fp; /* stp x29,x30,[sp, #0x30] */
    stack_56 = tmp_lr; /* paired store second register inferred offset +8 */
    tmp_fp = tmp_sp + 48; /* add x29,sp,#0x30 */
    stack_m8 = tmp_x0; /* stur x0,[x29, #-0x8] */
    stack_m16 = tmp_x1; /* stur x1,[x29, #-0x10] */
    stack_24 = tmp_x2; /* str x2,[sp, #0x18] */
    tmp_x8 = stack_m8; /* ldur x8,[x29, #-0x8] */
    tmp_x9 = stack_m16; /* ldur x9,[x29, #-0x10] */
    tmp_x8 = tmp_x8 ^ (tmp_x9 << 1); /* eor x8,x8,x9, LSL #0x1 */
    tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
    tmp_x8 = tmp_x8 ^ (tmp_x9 >> 1); /* eor x8,x8,x9, LSR #0x1 */
    stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
    stack_12 = 0; /* str wzr,[sp, #0xc] */
    /* branch to 0x100001758 */ /* b 0x100001758 */
    /* loop kind: while_like */
    /* loop header: 0x100001758 */
    /* loop exits: ['0x1000017a4', '0x1000017d8'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100001760 after subs at 0x10000175c; target 0x1000017d8; loop polarity inverted")) {
        /* if/else condition block: 0x100001758 */
        /* merge block: 0x1000017c8 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100001760 after subs at 0x10000175c; target 0x1000017d8")) {
            /* block 0x10000178c */
            /* branch to 0x100001790 */ /* b 0x100001790 */
            /* block 0x100001790 */
            /* branch to 0x1000017c8 */ /* b 0x1000017c8 */
        } else {
            /* block 0x100001794 */
            tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
            tmp_x8 = tmp_x8 & 63; /* and x8,x8,#0x3f */
            tmp_x8 = tmp_x8 - 41; /* subs x8,x8,#0x29; flags updated */
            /* conditional branch b.ne -> 0x1000017ac */
            /* block 0x1000017ac */
            tmp_x0 = stack_16; /* ldr x0,[sp, #0x10] */
            tmp_x1 = (i64)(i32)stack_12; /* ldrsw x1,[sp, #0xc] */
            call_0x100001538(tmp_x0, tmp_x1); /* bl 0x100001538; args refined from same-block evidence */
            /* block 0x1000017b8 */
            tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
            tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
            stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
            /* branch to 0x1000017c8 */ /* b 0x1000017c8 */
        }
        /* block 0x1000017c8 */
        tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
        /* branch to 0x100001758 */ /* b 0x100001758 */
    }
    /* block 0x1000017a4 */
    /* branch to 0x1000017a8 */ /* b 0x1000017a8 */
    /* block 0x1000017a8 */
    /* branch to 0x1000017d8 */ /* b 0x1000017d8 */
    /* block 0x1000017d8 */
    tmp_x0 = stack_16; /* ldr x0,[sp, #0x10] */
    tmp_fp = stack_48; /* ldp x29,x30,[sp, #0x30] */
    tmp_lr = stack_56; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 64; /* add sp,sp,#0x40 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t tri_b(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_30h)
{
    /* Entry: 0x1000017e8 */
    /* Body status: structured */
    /* 12 basic block(s), 58 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[0, 12, 16, 24, 32, 40], sizes=[1, 4, 8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u32 stack_12 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;
    u64 stack_32 = 0;
    u64 stack_40 = 0;

    /* Control flow structure: */
    /* block 0x1000017e8 */
    tmp_sp = tmp_sp - 48; /* sub sp,sp,#0x30 */
    stack_40 = tmp_x0; /* str x0,[sp, #0x28] */
    stack_32 = tmp_x1; /* str x1,[sp, #0x20] */
    stack_24 = tmp_x2; /* str x2,[sp, #0x18] */
    tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
    tmp_x9 = stack_32; /* ldr x9,[sp, #0x20] */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
    tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
    stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
    stack_12 = 0; /* str wzr,[sp, #0xc] */
    /* branch to 0x100001818 */ /* b 0x100001818 */
    /* loop kind: while_like */
    /* loop header: 0x100001818 */
    /* loop exits: ['0x100001894', '0x1000018b0'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100001820 after subs at 0x10000181c; target 0x1000018b0; loop polarity inverted")) {
        /* if/else condition block: 0x100001818 */
        /* merge block: 0x1000018a0 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100001820 after subs at 0x10000181c; target 0x1000018b0")) {
            /* block 0x100001880 */
            /* branch to 0x100001884 */ /* b 0x100001884 */
            /* block 0x100001884 */
            /* branch to 0x1000018a0 */ /* b 0x1000018a0 */
        } else {
            /* block 0x100001888 */
            tmp_w8 = stack_16; /* ldrb w8,[sp, #0x10] */
            tmp_x8 = tmp_x8 - 165; /* subs x8,x8,#0xa5; flags updated */
            /* conditional branch b.ne -> 0x10000189c */
            /* block 0x10000189c */
            /* branch to 0x1000018a0 */ /* b 0x1000018a0 */
        }
        /* block 0x1000018a0 */
        tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
        /* branch to 0x100001818 */ /* b 0x100001818 */
    }
    /* block 0x100001894 */
    /* branch to 0x100001898 */ /* b 0x100001898 */
    /* block 0x100001898 */
    /* branch to 0x1000018b0 */ /* b 0x1000018b0 */
    /* block 0x1000018b0 */
    tmp_x10 = stack_16; /* ldr x10,[sp, #0x10] */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
    tmp_x0 = stack_16; /* ldr x0,[sp, #0x10] */
    tmp_sp = tmp_sp + 48; /* add sp,sp,#0x30 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t tri_c(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_40h)
{
    /* Entry: 0x1000018d0 */
    /* Body status: unstructured */
    /* 33 basic block(s), 122 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[0, 12, 16, 24], sizes=[4, 8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x2 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m8 = 0;
    u64 stack_m16 = 0;
    u64 stack_0 = 0;
    u64 stack_12 = 0;
    u64 stack_16 = 0;
    u64 stack_24 = 0;
    u64 stack_48 = 0;
    u64 stack_56 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: irreducible_cfg */
    {
        /* block 0x1000018d0 */
        tmp_sp = tmp_sp - 64; /* sub sp,sp,#0x40 */
        stack_48 = tmp_fp; /* stp x29,x30,[sp, #0x30] */
        stack_56 = tmp_lr; /* paired store second register inferred offset +8 */
        tmp_fp = tmp_sp + 48; /* add x29,sp,#0x30 */
        stack_m8 = tmp_x0; /* stur x0,[x29, #-0x8] */
        stack_m16 = tmp_x1; /* stur x1,[x29, #-0x10] */
        stack_24 = tmp_x2; /* str x2,[sp, #0x18] */
        tmp_x8 = stack_m8; /* ldur x8,[x29, #-0x8] */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        stack_12 = 0; /* str wzr,[sp, #0xc] */
        /* branch to 0x1000018f8 */ /* b 0x1000018f8 */
        /* block 0x1000018f8 */
        tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
        tmp_w8 = tmp_w8 - 16; /* subs w8,w8,#0x10; flags updated */
        /* conditional branch b.ge -> 0x100001aa8 */
        /* block 0x100001904 */
        /* branch to 0x100001908 */ /* b 0x100001908 */
        /* block 0x100001908 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x9 = stack_m16; /* ldur x9,[x29, #-0x10] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x8 = tmp_x8 & 7; /* and x8,x8,#0x7 */
        stack_0 = tmp_x8; /* str x8,[sp] */
        /* cbz tmp_x8 -> 0x100001994 */
        /* block 0x100001930 */
        /* branch to 0x100001934 */ /* b 0x100001934 */
        /* block 0x100001934 */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 - 1; /* subs x8,x8,#0x1; flags updated */
        /* conditional branch b.eq -> 0x1000019b0 */
        /* block 0x100001940 */
        /* branch to 0x100001944 */ /* b 0x100001944 */
        /* block 0x100001944 */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 - 2; /* subs x8,x8,#0x2; flags updated */
        /* conditional branch b.eq -> 0x1000019d4 */
        /* block 0x100001950 */
        /* branch to 0x100001954 */ /* b 0x100001954 */
        /* block 0x100001954 */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 - 3; /* subs x8,x8,#0x3; flags updated */
        /* conditional branch b.eq -> 0x1000019f8 */
        /* block 0x100001960 */
        /* branch to 0x100001964 */ /* b 0x100001964 */
        /* block 0x100001964 */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 - 4; /* subs x8,x8,#0x4; flags updated */
        /* conditional branch b.eq -> 0x100001a10 */
        /* block 0x100001970 */
        /* branch to 0x100001974 */ /* b 0x100001974 */
        /* block 0x100001974 */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 - 5; /* subs x8,x8,#0x5; flags updated */
        /* conditional branch b.eq -> 0x100001a50 */
        /* block 0x100001980 */
        /* branch to 0x100001984 */ /* b 0x100001984 */
        /* block 0x100001984 */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 - 6; /* subs x8,x8,#0x6; flags updated */
        /* conditional branch b.eq -> 0x100001a54 */
        /* block 0x100001990 */
        /* branch to 0x100001a74 */ /* b 0x100001a74 */
        /* block 0x100001994 */
        tmp_x8 = stack_m8; /* ldur x8,[x29, #-0x8] */
        tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
        tmp_x9 = tmp_x8 ^ tmp_x9; /* eor x9,x8,x9 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x100001a94 */ /* b 0x100001a94 */
        /* block 0x1000019b0 */
        tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
        tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
        tmp_x10 = 3; /* mov x10,#0x3 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x9 = tmp_x8 + tmp_x9; /* add x9,x8,x9 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x100001a94 */ /* b 0x100001a94 */
        /* block 0x1000019d4 */
        tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
        tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
        tmp_x10 = 5; /* mov x10,#0x5 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x9 = tmp_x8 + tmp_x9; /* add x9,x8,x9 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x8 = tmp_x8 - tmp_x9; /* subs x8,x8,x9; flags updated */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x100001a94 */ /* b 0x100001a94 */
        /* block 0x1000019f8 */
        tmp_x9 = stack_16; /* ldr x9,[sp, #0x10] */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x8 = tmp_x8 >> 2; /* lsr x8,x8,#0x2 */
        tmp_x8 = tmp_x8 ^ (tmp_x9 << 5); /* eor x8,x8,x9, LSL #0x5 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x100001a94 */ /* b 0x100001a94 */
        /* block 0x100001a10 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        /* tbz tmp_w8 bit 0 -> 0x100001a34 */
        /* block 0x100001a18 */
        /* branch to 0x100001a1c */ /* b 0x100001a1c */
        /* block 0x100001a1c */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x9 = 22136; /* mov x9,#0x5678 */
        /* 0x100001a24: unsupported instruction: movk x9,#0x1234, LSL #16 */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x100001a4c */ /* b 0x100001a4c */
        /* block 0x100001a34 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x9 = 17185; /* mov x9,#0x4321 */
        /* 0x100001a3c: unsupported instruction: movk x9,#0x8765, LSL #16 */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x100001a4c */ /* b 0x100001a4c */
        /* block 0x100001a4c */
        /* branch to 0x100001a94 */ /* b 0x100001a94 */
        /* block 0x100001a50 */
        /* branch to 0x100001a98 */ /* b 0x100001a98 */
        /* block 0x100001a54 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
        tmp_x0 = tmp_x8 ^ tmp_x9; /* eor x0,x8,x9 */
        call_0x1000014a8(tmp_x0); /* bl 0x1000014a8; args refined from same-block evidence */
        /* block 0x100001a64 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x100001a94 */ /* b 0x100001a94 */
        /* block 0x100001a74 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x9 = 47806; /* mov x9,#0xbabe */
        /* 0x100001a7c: unsupported instruction: movk x9,#0xcafe, LSL #16 */
        /* 0x100001a80: unsupported instruction: movk x9,#0xbeef, LSL #32 */
        /* 0x100001a84: unsupported instruction: movk x9,#0xdead, LSL #48 */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x100001a94 */ /* b 0x100001a94 */
        /* block 0x100001a94 */
        /* branch to 0x100001a98 */ /* b 0x100001a98 */
        /* block 0x100001a98 */
        tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
        /* branch to 0x1000018f8 */ /* b 0x1000018f8 */
        /* block 0x100001aa8 */
        tmp_x0 = stack_16; /* ldr x0,[sp, #0x10] */
        tmp_fp = stack_48; /* ldp x29,x30,[sp, #0x30] */
        tmp_lr = stack_56; /* paired load second register inferred offset +8 */
        tmp_sp = tmp_sp + 64; /* add sp,sp,#0x40 */
        return tmp_x0; /* return value from x0 before ret */
    }
    /* unstructured region end */

}

uint64_t stack_chk_fail(void)
{
    /* Entry: 0x100001ab8 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 3 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[0], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x16 = 0;

    /* Control flow structure: */
    /* block 0x100001ab8 */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.__stack_chk_fail */
    tmp_x16 = *(u64 *)(tmp_x16); /* ldr x16, [x16] */
    /* branch to tmp_x16 */ /* br x16 */

    /* return value unknown */
    return 0;
}

int32_t printf(void * format)
{
    /* Entry: 0x100001ac4 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 4 instruction(s) */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[16], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x16 = 0;

    /* Control flow structure: */
    /* block 0x100001ac4 */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.__stack_chk_fail */
    tmp_x16 = *(u64 *)(tmp_x16 + 16); /* ldr x16, [x16, 0x10] */
    /* branch to tmp_x16 */ /* br x16 */
    /* 0x100001ad0: unsupported instruction: invalid */

    /* return value unknown */
    return 0;
}

