/*
 * recovered.c — Phase 5.7.2 Conservative ARM64 Coverage Cleanup
 * Schema version: 5.7.2
 * Generated: 2026-06-16T17:23:49Z
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
uint64_t mixed_driver(uint64_t arg1, uint64_t arg_30h);
uint64_t cfg_pressure(uint64_t arg1, uint64_t arg2, uint64_t arg_50h);
uint64_t indirect_pressure(uint64_t arg1, uint64_t arg_40h);
uint64_t stack_layout_pressure(uint64_t arg1);
uint64_t abi_pressure(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg4, uint64_t arg5, uint64_t arg6, uint64_t arg7, uint64_t arg8, uint64_t arg_60h);
uint64_t rotmix(uint64_t arg1, uint64_t arg_10h);
uint64_t op_add(uint64_t arg1, uint64_t arg2, uint64_t arg_20h);
uint64_t op_xor(uint64_t arg1, uint64_t arg2, uint64_t arg_20h);
uint64_t op_mul(uint64_t arg1, uint64_t arg2, uint64_t arg_20h);
uint64_t op_shift(uint64_t arg1, uint64_t arg2, uint64_t arg_20h);
uint64_t op_div(uint64_t arg1, uint64_t arg2, uint64_t arg_20h);
uint64_t op_logic(uint64_t arg1, uint64_t arg2, uint64_t arg_20h);
uint64_t tri_a(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_40h);
uint64_t tri_b(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_30h);
uint64_t tri_c(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_40h);
uint64_t stack_chk_fail(void);
int32_t printf(void * format);

/* Conservative call target helpers */
u64 call_0x10000074c();
u64 call_0x100000880();
u64 call_0x100000b44();
u64 call_0x100000cc8();
u64 call_0x100001054();
u64 call_0x100001220();
u64 call_0x1000012b0();
u64 call_0x1000012f4();
u64 call_0x100001338();
u64 call_0x100001384();
u64 call_0x1000013dc();
u64 call_0x100001444();
u64 call_0x100001498();
u64 call_0x100001560();
u64 call_0x100001648();
u64 call_0x100001830();
u64 call_0x10000183c();

/* ================================================== */
/*                 Function Definitions                */
/* ================================================== */

int32_t main(int32_t argc, char ** argv)
{
    /* Entry: 0x100000548 */
    /* Body status: structured */
    /* 29 basic block(s), 129 instruction(s) */

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
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
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
    u64 stack_96 = 0;
    u64 stack_104 = 0;

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
    /* loop exits: ['0x1000006f4'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000670 after subs at 0x10000066c; target 0x1000006f4; loop polarity inverted")) {
        /* block 0x100000668 */
        tmp_w8 = stack_32; /* ldr w8,[sp, #0x20] */
        tmp_w8 = tmp_w8 - 18; /* subs w8,w8,#0x12; flags updated */
        /* conditional branch b.ge -> 0x1000006f4 */
        /* block 0x100000674 */
        /* branch to 0x100000678 */ /* b 0x100000678 */
        /* block 0x100000678 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = stack_m32; /* ldur x9,[x29, #-0x20] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x9 = (i64)(i32)stack_32; /* ldrsw x9,[sp, #0x20] */
        tmp_x0 = tmp_x8 + tmp_x9; /* add x0,x8,x9 */
        call_0x10000074c(tmp_x0); /* bl 0x10000074c; args refined from same-block evidence */
        /* block 0x100000690 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        tmp_x0 = stack_m24; /* ldur x0,[x29, #-0x18] */
        tmp_x8 = stack_m32; /* ldur x8,[x29, #-0x20] */
        tmp_x9 = (i64)(i32)stack_32; /* ldrsw x9,[sp, #0x20] */
        tmp_x1 = tmp_x8 ^ tmp_x9; /* eor x1,x8,x9 */
        call_0x100000880(tmp_x0, tmp_x1); /* bl 0x100000880; args refined from same-block evidence */
        /* block 0x1000006b0 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = (i64)(i32)stack_32; /* ldrsw x9,[sp, #0x20] */
        tmp_x10 = 9; /* mov x10,#0x9 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x0 = tmp_x8 + tmp_x9; /* add x0,x8,x9 */
        call_0x100000b44(tmp_x0); /* bl 0x100000b44; args refined from same-block evidence */
        /* block 0x1000006d4 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x1000006e4 */ /* b 0x1000006e4 */
        /* block 0x1000006e4 */
        tmp_w8 = stack_32; /* ldr w8,[sp, #0x20] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_32 = tmp_w8; /* str w8,[sp, #0x20] */
        /* branch to 0x100000668 */ /* b 0x100000668 */
    }
    /* block 0x1000006f4 */
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
    tmp_x0 = tmp_x0 + 2120; /* add x0,x0,#0x848 */
    call_0x100001830(tmp_x0); /* bl 0x100001830; args refined from same-block evidence */
    /* block 0x100000728 */
    tmp_x9 = stack_16; /* ldr x9,[sp, #0x10] */
    tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
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
    /* Entry: 0x10000074c */
    /* Body status: structured */
    /* 16 basic block(s), 77 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[12, 16], sizes=[4, 8] */

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
    /* block 0x10000074c */
    tmp_sp = tmp_sp - 48; /* sub sp,sp,#0x30 */
    stack_32 = tmp_fp; /* stp x29,x30,[sp, #0x20] */
    stack_40 = tmp_lr; /* paired store second register inferred offset +8 */
    tmp_fp = tmp_sp + 32; /* add x29,sp,#0x20 */
    stack_m8 = tmp_x0; /* stur x0,[x29, #-0x8] */
    tmp_x8 = stack_m8; /* ldur x8,[x29, #-0x8] */
    stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
    stack_12 = 0; /* str wzr,[sp, #0xc] */
    /* branch to 0x10000076c */ /* b 0x10000076c */
    /* loop kind: while_like */
    /* loop header: 0x10000076c */
    /* loop exits: ['0x100000854', '0x100000870'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000774 after subs at 0x100000770; target 0x100000870; loop polarity inverted")) {
        /* if/else condition block: 0x10000076c */
        /* merge block: 0x100000860 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000774 after subs at 0x100000770; target 0x100000870")) {
            /* block 0x10000083c */
            /* branch to 0x100000840 */ /* b 0x100000840 */
            /* block 0x100000840 */
            /* branch to 0x100000860 */ /* b 0x100000860 */
        } else {
            /* block 0x100000844 */
            tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
            tmp_x8 = tmp_x8 & 4095; /* and x8,x8,#0xfff */
            tmp_x8 = tmp_x8 - 1911; /* subs x8,x8,#0x777; flags updated */
            /* conditional branch b.ne -> 0x10000085c */
            /* block 0x10000085c */
            /* branch to 0x100000860 */ /* b 0x100000860 */
        }
        /* block 0x100000860 */
        tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
        /* branch to 0x10000076c */ /* b 0x10000076c */
    }
    /* block 0x100000854 */
    /* branch to 0x100000858 */ /* b 0x100000858 */
    /* block 0x100000858 */
    /* branch to 0x100000870 */ /* b 0x100000870 */
    /* block 0x100000870 */
    tmp_x0 = stack_16; /* ldr x0,[sp, #0x10] */
    tmp_fp = stack_32; /* ldp x29,x30,[sp, #0x20] */
    tmp_lr = stack_40; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 48; /* add sp,sp,#0x30 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t cfg_pressure(uint64_t arg1, uint64_t arg2, uint64_t arg_50h)
{
    /* Entry: 0x100000880 */
    /* Body status: unstructured */
    /* 52 basic block(s), 177 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 16, 24, 32], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

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
        /* block 0x100000880 */
        tmp_sp = tmp_sp - 80; /* sub sp,sp,#0x50 */
        stack_64 = tmp_fp; /* stp x29,x30,[sp, #0x40] */
        stack_72 = tmp_lr; /* paired store second register inferred offset +8 */
        tmp_fp = tmp_sp + 64; /* add x29,sp,#0x40 */
        stack_m8 = tmp_x0; /* stur x0,[x29, #-0x8] */
        stack_m16 = tmp_x1; /* stur x1,[x29, #-0x10] */
        tmp_x8 = stack_m8; /* ldur x8,[x29, #-0x8] */
        tmp_x9 = stack_m16; /* ldur x9,[x29, #-0x10] */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        stack_32 = 0; /* str xzr,[sp, #0x20] */
        /* branch to 0x1000008ac */ /* b 0x1000008ac */
        /* block 0x1000008ac */
        tmp_x8 = stack_32; /* ldr x8,[sp, #0x20] */
        tmp_x8 = tmp_x8 - 80; /* subs x8,x8,#0x50; flags updated */
        /* conditional branch b.cs -> 0x100000b20 */
        /* block 0x1000008b8 */
        /* branch to 0x1000008bc */ /* b 0x1000008bc */
        /* block 0x1000008bc */
        tmp_x8 = stack_32; /* ldr x8,[sp, #0x20] */
        tmp_x9 = 50855; /* mov x9,#0xc6a7 */
        /* 0x1000008c4: unsupported instruction: movk x9,#0x4e67, LSL #16 */
        tmp_x9 = tmp_x8 * tmp_x9; /* mul x9,x8,x9 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 & 15; /* and x8,x8,#0xf */
        tmp_x8 = tmp_x8 - 9; /* subs x8,x8,#0x9; flags updated */
        /* conditional branch b.ne -> 0x1000008f0 */
        /* block 0x1000008e8 */
        /* branch to 0x1000008ec */ /* b 0x1000008ec */
        /* block 0x1000008ec */
        /* branch to 0x100000b10 */ /* b 0x100000b10 */
        /* block 0x1000008f0 */
        stack_24 = 0; /* str xzr,[sp, #0x18] */
        /* branch to 0x1000008f8 */ /* b 0x1000008f8 */
        /* block 0x1000008f8 */
        tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
        tmp_x8 = tmp_x8 - 32; /* subs x8,x8,#0x20; flags updated */
        /* conditional branch b.cs -> 0x100000af4 */
        /* block 0x100000904 */
        /* branch to 0x100000908 */ /* b 0x100000908 */
        /* block 0x100000908 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = stack_32; /* ldr x9,[sp, #0x20] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x8 = tmp_x8 & 7; /* and x8,x8,#0x7 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
        /* cbz tmp_x8 -> 0x100000994 */
        /* block 0x100000930 */
        /* branch to 0x100000934 */ /* b 0x100000934 */
        /* block 0x100000934 */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 - 1; /* subs x8,x8,#0x1; flags updated */
        /* conditional branch b.eq -> 0x1000009b4 */
        /* block 0x100000940 */
        /* branch to 0x100000944 */ /* b 0x100000944 */
        /* block 0x100000944 */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 - 2; /* subs x8,x8,#0x2; flags updated */
        /* conditional branch b.eq -> 0x1000009d4 */
        /* block 0x100000950 */
        /* branch to 0x100000954 */ /* b 0x100000954 */
        /* block 0x100000954 */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 - 3; /* subs x8,x8,#0x3; flags updated */
        /* conditional branch b.eq -> 0x100000a14 */
        /* block 0x100000960 */
        /* branch to 0x100000964 */ /* b 0x100000964 */
        /* block 0x100000964 */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 - 4; /* subs x8,x8,#0x4; flags updated */
        /* conditional branch b.eq -> 0x100000a34 */
        /* block 0x100000970 */
        /* branch to 0x100000974 */ /* b 0x100000974 */
        /* block 0x100000974 */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 - 5; /* subs x8,x8,#0x5; flags updated */
        /* conditional branch b.eq -> 0x100000a84 */
        /* block 0x100000980 */
        /* branch to 0x100000984 */ /* b 0x100000984 */
        /* block 0x100000984 */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 - 6; /* subs x8,x8,#0x6; flags updated */
        /* conditional branch b.eq -> 0x100000a88 */
        /* block 0x100000990 */
        /* branch to 0x100000aa8 */ /* b 0x100000aa8 */
        /* block 0x100000994 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
        tmp_x0 = tmp_x8 + tmp_x9; /* add x0,x8,x9 */
        call_0x100000cc8(tmp_x0); /* bl 0x100000cc8; args refined from same-block evidence */
        /* block 0x1000009a4 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000ac8 */ /* b 0x100000ac8 */
        /* block 0x1000009b4 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
        tmp_x0 = tmp_x8 ^ tmp_x9; /* eor x0,x8,x9 */
        call_0x100000b44(tmp_x0); /* bl 0x100000b44; args refined from same-block evidence */
        /* block 0x1000009c4 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000ac8 */ /* b 0x100000ac8 */
        /* block 0x1000009d4 */
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
        /* 0x1000009fc: unsupported instruction: movk x7,#0xfeed, LSL #16 */
        call_0x100001054(tmp_x0, tmp_x1, tmp_x2, tmp_x3, tmp_x4, tmp_x5, tmp_x6, tmp_x7); /* bl 0x100001054; args refined from same-block evidence */
        /* block 0x100000a04 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000ac8 */ /* b 0x100000ac8 */
        /* block 0x100000a14 */
        tmp_x9 = stack_m24; /* ldur x9,[x29, #-0x18] */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 >> 5; /* lsr x8,x8,#0x5 */
        tmp_x8 = tmp_x8 ^ (tmp_x9 << 3); /* eor x8,x8,x9, LSL #0x3 */
        tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000ac8 */ /* b 0x100000ac8 */
        /* block 0x100000a34 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        /* tbz tmp_w8 bit 0 -> 0x100000a60 */
        /* block 0x100000a3c */
        /* branch to 0x100000a40 */ /* b 0x100000a40 */
        /* block 0x100000a40 */
        tmp_x0 = stack_m24; /* ldur x0,[x29, #-0x18] */
        tmp_x1 = stack_m8; /* ldur x1,[x29, #-0x8] */
        tmp_x2 = stack_m16; /* ldur x2,[x29, #-0x10] */
        call_0x100001498(tmp_x0, tmp_x1, tmp_x2); /* bl 0x100001498; args refined from same-block evidence */
        /* block 0x100000a50 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000a80 */ /* b 0x100000a80 */
        /* block 0x100000a60 */
        tmp_x0 = stack_m24; /* ldur x0,[x29, #-0x18] */
        tmp_x1 = stack_m16; /* ldur x1,[x29, #-0x10] */
        tmp_x2 = stack_m8; /* ldur x2,[x29, #-0x8] */
        call_0x100001560(tmp_x0, tmp_x1, tmp_x2); /* bl 0x100001560; args refined from same-block evidence */
        /* block 0x100000a70 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000a80 */ /* b 0x100000a80 */
        /* block 0x100000a80 */
        /* branch to 0x100000ac8 */ /* b 0x100000ac8 */
        /* block 0x100000a84 */
        /* branch to 0x100000ae4 */ /* b 0x100000ae4 */
        /* block 0x100000a88 */
        tmp_x0 = stack_m24; /* ldur x0,[x29, #-0x18] */
        tmp_x1 = stack_32; /* ldr x1,[sp, #0x20] */
        tmp_x2 = stack_24; /* ldr x2,[sp, #0x18] */
        call_0x100001648(tmp_x0, tmp_x1, tmp_x2); /* bl 0x100001648; args refined from same-block evidence */
        /* block 0x100000a98 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000ac8 */ /* b 0x100000ac8 */
        /* block 0x100000aa8 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x9 = 30864; /* mov x9,#0x7890 */
        /* 0x100000ab0: unsupported instruction: movk x9,#0x3456, LSL #16 */
        /* 0x100000ab4: unsupported instruction: movk x9,#0xef12, LSL #32 */
        /* 0x100000ab8: unsupported instruction: movk x9,#0xabcd, LSL #48 */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
        /* branch to 0x100000ac8 */ /* b 0x100000ac8 */
        /* block 0x100000ac8 */
        tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
        tmp_x8 = tmp_x8 & 1023; /* and x8,x8,#0x3ff */
        tmp_x8 = tmp_x8 - 341; /* subs x8,x8,#0x155; flags updated */
        /* conditional branch b.ne -> 0x100000ae0 */
        /* block 0x100000ad8 */
        /* branch to 0x100000adc */ /* b 0x100000adc */
        /* block 0x100000adc */
        /* branch to 0x100000af4 */ /* b 0x100000af4 */
        /* block 0x100000ae0 */
        /* branch to 0x100000ae4 */ /* b 0x100000ae4 */
        /* block 0x100000ae4 */
        tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
        tmp_x8 = tmp_x8 + 1; /* add x8,x8,#0x1 */
        stack_24 = tmp_x8; /* str x8,[sp, #0x18] */
        /* branch to 0x1000008f8 */ /* b 0x1000008f8 */
        /* block 0x100000af4 */
        tmp_w8 = stack_m24; /* ldurh w8,[x29, #-0x18] */
        tmp_x9 = 48879; /* mov x9,#0xbeef */
        tmp_x8 = tmp_x8 - tmp_x9; /* subs x8,x8,x9; flags updated */
        /* conditional branch b.ne -> 0x100000b0c */
        /* block 0x100000b04 */
        /* branch to 0x100000b08 */ /* b 0x100000b08 */
        /* block 0x100000b08 */
        /* branch to 0x100000b20 */ /* b 0x100000b20 */
        /* block 0x100000b0c */
        /* branch to 0x100000b10 */ /* b 0x100000b10 */
        /* block 0x100000b10 */
        tmp_x8 = stack_32; /* ldr x8,[sp, #0x20] */
        tmp_x8 = tmp_x8 + 1; /* add x8,x8,#0x1 */
        stack_32 = tmp_x8; /* str x8,[sp, #0x20] */
        /* branch to 0x1000008ac */ /* b 0x1000008ac */
        /* block 0x100000b20 */
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
    /* unstructured region end */

}

uint64_t indirect_pressure(uint64_t arg1, uint64_t arg_40h)
{
    /* Entry: 0x100000b44 */
    /* Body status: structured */
    /* 15 basic block(s), 97 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[0, 8, 16, 24], sizes=[8] */
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
    /* block 0x100000b44 */
    tmp_sp = tmp_sp - 64; /* sub sp,sp,#0x40 */
    stack_48 = tmp_fp; /* stp x29,x30,[sp, #0x30] */
    stack_56 = tmp_lr; /* paired store second register inferred offset +8 */
    tmp_fp = tmp_sp + 48; /* add x29,sp,#0x30 */
    stack_m8 = tmp_x0; /* stur x0,[x29, #-0x8] */
    tmp_x8 = stack_m8; /* ldur x8,[x29, #-0x8] */
    stack_m16 = tmp_x8; /* stur x8,[x29, #-0x10] */
    stack_24 = 0; /* str xzr,[sp, #0x18] */
    /* branch to 0x100000b64 */ /* b 0x100000b64 */
    /* loop kind: while_like */
    /* loop header: 0x100000b64 */
    /* loop exits: ['0x100000bd0', '0x100000ca4'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition unknown: loop header 0x100000b64")) {
        /* block 0x100000b64 */
        tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
        tmp_x8 = tmp_x8 - 96; /* subs x8,x8,#0x60; flags updated */
        /* conditional branch b.cs -> 0x100000ca4 */
        /* block 0x100000b70 */
        /* branch to 0x100000b74 */ /* b 0x100000b74 */
        /* block 0x100000b74 */
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
        /* block 0x100000bb8 */
        tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
        tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
        stack_m16 = tmp_x8; /* stur x8,[x29, #-0x10] */
        tmp_w8 = stack_m16; /* ldurb w8,[x29, #-0x10] */
        tmp_x8 = tmp_x8 - 66; /* subs x8,x8,#0x42; flags updated */
        /* conditional branch b.ne -> 0x100000bd8 */
        /* if/else condition block: 0x100000bd8 */
        /* merge block: 0x100000c94 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ne at 0x100000be4 after subs at 0x100000be0; target 0x100000bf0; polarity inverted")) {
            /* block 0x100000be8 */
            /* branch to 0x100000bec */ /* b 0x100000bec */
            /* block 0x100000bec */
            /* branch to 0x100000c94 */ /* b 0x100000c94 */
        } else {
            /* block 0x100000bf0 */
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
            /* block 0x100000c2c */
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
            /* block 0x100000c84 */
            tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
            tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
            stack_m16 = tmp_x8; /* stur x8,[x29, #-0x10] */
            /* branch to 0x100000c94 */ /* b 0x100000c94 */
        }
        /* block 0x100000c94 */
        tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
        tmp_x8 = tmp_x8 + 1; /* add x8,x8,#0x1 */
        stack_24 = tmp_x8; /* str x8,[sp, #0x18] */
        /* branch to 0x100000b64 */ /* b 0x100000b64 */
    }
    /* block 0x100000bd0 */
    /* branch to 0x100000bd4 */ /* b 0x100000bd4 */
    /* block 0x100000bd4 */
    /* branch to 0x100000ca4 */ /* b 0x100000ca4 */
    /* block 0x100000ca4 */
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

uint64_t stack_layout_pressure(uint64_t arg1)
{
    /* Entry: 0x100000cc8 */
    /* Body status: structured */
    /* 42 basic block(s), 227 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[8, 16, 20, 24, 28, 32, 36, 40, 48], sizes=[4, 8] */
    /*   base=x8, kind=array_like, offsets=[0, 8], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

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
    /* block 0x100000cc8 */
    stack_m32 = tmp_x28; /* stp x28,x27,[sp, #-0x20]! */
    stack_m24 = tmp_x27; /* paired store second register inferred offset +8 */
    stack_16 = tmp_fp; /* stp x29,x30,[sp, #0x10] */
    stack_24 = tmp_lr; /* paired store second register inferred offset +8 */
    tmp_fp = tmp_sp + 16; /* add x29,sp,#0x10 */
    tmp_sp = tmp_sp - 960; /* sub sp,sp,#0x3c0 */
    tmp_x8 = 0x100004000; /* adrp x8,0x100004000 */
    tmp_x8 = *(u64 *)(tmp_x8 + 8); /* ldr x8,[x8, #0x8] */
    tmp_x8 = *(u64 *)(tmp_x8); /* ldr x8,[x8] */
    stack_m24 = tmp_x8; /* stur x8,[x29, #-0x18] */
    stack_48 = tmp_x0; /* str x0,[sp, #0x30] */
    tmp_x8 = stack_48; /* ldr x8,[sp, #0x30] */
    stack_40 = tmp_x8; /* str x8,[sp, #0x28] */
    stack_36 = 0; /* str wzr,[sp, #0x24] */
    /* branch to 0x100000cfc */ /* b 0x100000cfc */
    /* loop kind: while_like */
    /* loop header: 0x100000cfc */
    /* loop exits: ['0x100000d44'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000d04 after subs at 0x100000d00; target 0x100000d44; loop polarity inverted")) {
        /* block 0x100000cfc */
        tmp_w8 = stack_36; /* ldr w8,[sp, #0x24] */
        tmp_w8 = tmp_w8 - 40; /* subs w8,w8,#0x28; flags updated */
        /* conditional branch b.ge -> 0x100000d44 */
        /* block 0x100000d08 */
        /* branch to 0x100000d0c */ /* b 0x100000d0c */
        /* block 0x100000d0c */
        tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
        tmp_x9 = (i64)(i32)stack_36; /* ldrsw x9,[sp, #0x24] */
        tmp_x10 = 17; /* mov x10,#0x11 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x0 = tmp_x8 + tmp_x9; /* add x0,x8,x9 */
        call_0x100001220(tmp_x0); /* bl 0x100001220; args refined from same-block evidence */
        /* block 0x100000d24 */
        tmp_x9 = (i64)(i32)stack_36; /* ldrsw x9,[sp, #0x24] */
        tmp_x8 = tmp_sp + 632; /* add x8,sp,#0x278 */
        *(u64 *)(tmp_x8 + (tmp_x9 << 3)) = tmp_x0; /* str x0,[x8, x9, LSL #0x3] */
        /* branch to 0x100000d34 */ /* b 0x100000d34 */
        /* block 0x100000d34 */
        tmp_w8 = stack_36; /* ldr w8,[sp, #0x24] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_36 = tmp_w8; /* str w8,[sp, #0x24] */
        /* branch to 0x100000cfc */ /* b 0x100000cfc */
    }
    /* block 0x100000d44 */
    stack_32 = 0; /* str wzr,[sp, #0x20] */
    /* branch to 0x100000d4c */ /* b 0x100000d4c */
    /* loop kind: while_like */
    /* loop header: 0x100000d4c */
    /* loop exits: ['0x100000d90'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000d54 after subs at 0x100000d50; target 0x100000d90; loop polarity inverted")) {
        /* block 0x100000d4c */
        tmp_w8 = stack_32; /* ldr w8,[sp, #0x20] */
        tmp_w8 = tmp_w8 - 80; /* subs w8,w8,#0x50; flags updated */
        /* conditional branch b.ge -> 0x100000d90 */
        /* block 0x100000d58 */
        /* branch to 0x100000d5c */ /* b 0x100000d5c */
        /* block 0x100000d5c */
        tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
        tmp_x9 = (i64)(i32)stack_32; /* ldrsw x9,[sp, #0x20] */
        tmp_x10 = 33; /* mov x10,#0x21 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        tmp_x10 = (i64)(i32)stack_32; /* ldrsw x10,[sp, #0x20] */
        tmp_x9 = tmp_sp + 312; /* add x9,sp,#0x138 */
        *(u32 *)(tmp_x9 + (tmp_x10 << 2)) = tmp_w8; /* str w8,[x9, x10, LSL #0x2] */
        /* branch to 0x100000d80 */ /* b 0x100000d80 */
        /* block 0x100000d80 */
        tmp_w8 = stack_32; /* ldr w8,[sp, #0x20] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_32 = tmp_w8; /* str w8,[sp, #0x20] */
        /* branch to 0x100000d4c */ /* b 0x100000d4c */
    }
    /* block 0x100000d90 */
    stack_28 = 0; /* str wzr,[sp, #0x1c] */
    /* branch to 0x100000d98 */ /* b 0x100000d98 */
    /* loop kind: while_like */
    /* loop header: 0x100000d98 */
    /* loop exits: ['0x100000ddc'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000da0 after subs at 0x100000d9c; target 0x100000ddc; loop polarity inverted")) {
        /* block 0x100000d98 */
        tmp_w8 = stack_28; /* ldr w8,[sp, #0x1c] */
        tmp_w8 = tmp_w8 - 64; /* subs w8,w8,#0x40; flags updated */
        /* conditional branch b.ge -> 0x100000ddc */
        /* block 0x100000da4 */
        /* branch to 0x100000da8 */ /* b 0x100000da8 */
        /* block 0x100000da8 */
        tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
        tmp_x9 = (i64)(i32)stack_28; /* ldrsw x9,[sp, #0x1c] */
        tmp_x10 = 11; /* mov x10,#0xb */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x10 = (i64)(i32)stack_28; /* ldrsw x10,[sp, #0x1c] */
        tmp_x9 = tmp_sp + 184; /* add x9,sp,#0xb8 */
        *(u16 *)(tmp_x9 + (tmp_x10 << 1)) = tmp_w8; /* strh w8,[x9, x10, LSL #0x1] */
        /* branch to 0x100000dcc */ /* b 0x100000dcc */
        /* block 0x100000dcc */
        tmp_w8 = stack_28; /* ldr w8,[sp, #0x1c] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_28 = tmp_w8; /* str w8,[sp, #0x1c] */
        /* branch to 0x100000d98 */ /* b 0x100000d98 */
    }
    /* block 0x100000ddc */
    stack_24 = 0; /* str wzr,[sp, #0x18] */
    /* branch to 0x100000de4 */ /* b 0x100000de4 */
    /* loop kind: while_like */
    /* loop header: 0x100000de4 */
    /* loop exits: ['0x100000e24'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000dec after subs at 0x100000de8; target 0x100000e24; loop polarity inverted")) {
        /* block 0x100000de4 */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w8 = tmp_w8 - 128; /* subs w8,w8,#0x80; flags updated */
        /* conditional branch b.ge -> 0x100000e24 */
        /* block 0x100000df0 */
        /* branch to 0x100000df4 */ /* b 0x100000df4 */
        /* block 0x100000df4 */
        tmp_x8 = stack_40; /* ldr x8,[sp, #0x28] */
        tmp_w9 = stack_24; /* ldr w9,[sp, #0x18] */
        tmp_w9 = tmp_w9 & 7; /* and w9,w9,#0x7 */
        tmp_x8 = tmp_x8 >> tmp_x9; /* lsr x8,x8,x9 */
        tmp_x10 = (i64)(i32)stack_24; /* ldrsw x10,[sp, #0x18] */
        tmp_x9 = tmp_sp + 56; /* add x9,sp,#0x38 */
        *(u8 *)(tmp_x9 + tmp_x10) = tmp_w8; /* strb w8,[x9, x10, LSL ] */
        /* branch to 0x100000e14 */ /* b 0x100000e14 */
        /* block 0x100000e14 */
        tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_24 = tmp_w8; /* str w8,[sp, #0x18] */
        /* branch to 0x100000de4 */ /* b 0x100000de4 */
    }
    /* block 0x100000e24 */
    stack_20 = 0; /* str wzr,[sp, #0x14] */
    /* branch to 0x100000e2c */ /* b 0x100000e2c */
    /* loop kind: while_like */
    /* loop header: 0x100000e2c */
    /* loop exits: ['0x100001004'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000e34 after subs at 0x100000e30; target 0x100001004; loop polarity inverted")) {
        /* if condition block: 0x100000e2c */
        /* merge block: 0x100000ff0 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100000e34 after subs at 0x100000e30; target 0x100001004")) {
            /* block 0x100000f48 */
            /* branch to 0x100000f4c */ /* b 0x100000f4c */
            /* block 0x100000f4c */
            /* branch to 0x100000ff0 */ /* b 0x100000ff0 */
        }
        /* block 0x100000ff0 */
        /* branch to 0x100000ff4 */ /* b 0x100000ff4 */
        /* block 0x100000ff4 */
        tmp_w8 = stack_20; /* ldr w8,[sp, #0x14] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_20 = tmp_w8; /* str w8,[sp, #0x14] */
        /* branch to 0x100000e2c */ /* b 0x100000e2c */
    }
    /* if/else condition block: 0x100001004 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.eq at 0x100001034 after subs at 0x100001030; target 0x100001040; polarity inverted")) {
        /* block 0x100001038 */
        /* branch to 0x10000103c */ /* b 0x10000103c */
        /* block 0x10000103c */
        call_0x10000183c(); /* bl 0x10000183c */
    } else {
        /* block 0x100001040 */
        tmp_x0 = stack_8; /* ldr x0,[sp, #0x8] */
        tmp_sp = tmp_sp + 960; /* add sp,sp,#0x3c0 */
        tmp_fp = stack_16; /* ldp x29,x30,[sp, #0x10] */
        tmp_lr = stack_24; /* paired load second register inferred offset +8 */
        /* unsupported paired load: ldp x28,x27,[sp], #0x20 */
        return tmp_x0; /* return value from x0 before ret */
    }

}

uint64_t abi_pressure(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg4, uint64_t arg5, uint64_t arg6, uint64_t arg7, uint64_t arg8, uint64_t arg_60h)
{
    /* Entry: 0x100001054 */
    /* Body status: structured */
    /* 18 basic block(s), 115 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[0, 8, 16, 24, 32, 40], sizes=[8] */
    /*   base=x9, kind=pointer_like, offsets=[80], sizes=[8] */

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
    /* block 0x100001054 */
    tmp_sp = tmp_sp - 96; /* sub sp,sp,#0x60 */
    stack_80 = tmp_fp; /* stp x29,x30,[sp, #0x50] */
    stack_88 = tmp_lr; /* paired store second register inferred offset +8 */
    tmp_fp = tmp_sp + 80; /* add x29,sp,#0x50 */
    stack_m8 = tmp_x0; /* stur x0,[x29, #-0x8] */
    stack_m16 = tmp_x1; /* stur x1,[x29, #-0x10] */
    stack_m24 = tmp_x2; /* stur x2,[x29, #-0x18] */
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
    call_0x1000012b0(tmp_x0, tmp_x1); /* bl 0x1000012b0; args refined from same-block evidence */
    /* block 0x1000010ac */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x0 = stack_24; /* ldr x0,[sp, #0x18] */
    tmp_x1 = stack_16; /* ldr x1,[sp, #0x10] */
    call_0x1000012f4(tmp_x0, tmp_x1); /* bl 0x1000012f4; args refined from same-block evidence */
    /* block 0x1000010c4 */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x0 = stack_8; /* ldr x0,[sp, #0x8] */
    tmp_x1 = stack_m8; /* ldur x1,[x29, #-0x8] */
    call_0x100001338(tmp_x0, tmp_x1); /* bl 0x100001338; args refined from same-block evidence */
    /* block 0x1000010dc */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x0 = stack_m16; /* ldur x0,[x29, #-0x10] */
    tmp_x1 = stack_8; /* ldr x1,[sp, #0x8] */
    call_0x100001384(tmp_x0, tmp_x1); /* bl 0x100001384; args refined from same-block evidence */
    /* block 0x1000010f4 */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x0 = tmp_x8 + 17; /* add x0,x8,#0x11 */
    tmp_x8 = stack_m24; /* ldur x8,[x29, #-0x18] */
    tmp_x1 = tmp_x8 | 1; /* orr x1,x8,#0x1 */
    call_0x1000013dc(tmp_x0, tmp_x1); /* bl 0x1000013dc; args refined from same-block evidence */
    /* block 0x100001114 */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x0 = stack_m32; /* ldur x0,[x29, #-0x20] */
    tmp_x1 = stack_40; /* ldr x1,[sp, #0x28] */
    call_0x100001444(tmp_x0, tmp_x1); /* bl 0x100001444; args refined from same-block evidence */
    /* block 0x10000112c */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    stack_0 = 0; /* str xzr,[sp] */
    /* branch to 0x100001140 */ /* b 0x100001140 */
    /* loop kind: while_like */
    /* loop header: 0x100001140 */
    /* loop exits: ['0x1000011e0', '0x1000011fc'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition unknown: loop header 0x100001140")) {
        /* if/else condition block: 0x100001140 */
        /* merge block: 0x1000011ec */
        if (HEPHAESTUS_UNKNOWN_COND("condition unknown: block 0x100001140")) {
            /* block 0x1000011c8 */
            /* branch to 0x1000011cc */ /* b 0x1000011cc */
            /* block 0x1000011cc */
            /* branch to 0x1000011ec */ /* b 0x1000011ec */
        } else {
            /* block 0x1000011d0 */
            tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
            tmp_x8 = tmp_x8 & 127; /* and x8,x8,#0x7f */
            tmp_x8 = tmp_x8 - 99; /* subs x8,x8,#0x63; flags updated */
            /* conditional branch b.ne -> 0x1000011e8 */
            /* block 0x1000011e8 */
            /* branch to 0x1000011ec */ /* b 0x1000011ec */
        }
        /* block 0x1000011ec */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 + 1; /* add x8,x8,#0x1 */
        stack_0 = tmp_x8; /* str x8,[sp] */
        /* branch to 0x100001140 */ /* b 0x100001140 */
    }
    /* block 0x1000011e0 */
    /* branch to 0x1000011e4 */ /* b 0x1000011e4 */
    /* block 0x1000011e4 */
    /* branch to 0x1000011fc */ /* b 0x1000011fc */
    /* block 0x1000011fc */
    tmp_x10 = stack_8; /* ldr x10,[sp, #0x8] */
    tmp_x9 = 0x100008000; /* adrp x9,0x100008000 */
    tmp_x8 = *(u64 *)(tmp_x9 + 80); /* ldr x8,[x9, #0x50] */
    tmp_x8 = tmp_x8 ^ tmp_x10; /* eor x8,x8,x10 */
    *(u64 *)(tmp_x9 + 80) = tmp_x8; /* str x8,[x9, #0x50] */
    tmp_x0 = stack_8; /* ldr x0,[sp, #0x8] */
    tmp_fp = stack_80; /* ldp x29,x30,[sp, #0x50] */
    tmp_lr = stack_88; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 96; /* add sp,sp,#0x60 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t rotmix(uint64_t arg1, uint64_t arg_10h)
{
    /* Entry: 0x100001220 */
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
    /* block 0x100001220 */
    tmp_sp = tmp_sp - 16; /* sub sp,sp,#0x10 */
    stack_8 = tmp_x0; /* str x0,[sp, #0x8] */
    tmp_x9 = stack_8; /* ldr x9,[sp, #0x8] */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ (tmp_x9 >> 33); /* eor x8,x8,x9, LSR #0x21 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x9 = 36045; /* mov x9,#0x8ccd */
    /* 0x100001240: unsupported instruction: movk x9,#0xed55, LSL #16 */
    /* 0x100001244: unsupported instruction: movk x9,#0xafd7, LSL #32 */
    /* 0x100001248: unsupported instruction: movk x9,#0xff51, LSL #48 */
    tmp_x8 = tmp_x8 * tmp_x9; /* mul x8,x8,x9 */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x9 = stack_8; /* ldr x9,[sp, #0x8] */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x8 = tmp_x8 ^ (tmp_x9 >> 29); /* eor x8,x8,x9, LSR #0x1d */
    stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
    tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
    tmp_x9 = 60499; /* mov x9,#0xec53 */
    /* 0x10000126c: unsupported instruction: movk x9,#0x1a85, LSL #16 */
    /* 0x100001270: unsupported instruction: movk x9,#0xb9fe, LSL #32 */
    /* 0x100001274: unsupported instruction: movk x9,#0xc4ce, LSL #48 */
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
    /* Entry: 0x1000012b0 */
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
    /* block 0x1000012b0 */
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
    /* Entry: 0x1000012f4 */
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
    /* block 0x1000012f4 */
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
    /* Entry: 0x100001338 */
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
    /* block 0x100001338 */
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
    /* Entry: 0x100001384 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 22 instruction(s) */
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
    /* block 0x100001384 */
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
    /* Entry: 0x1000013dc */
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
    /* block 0x1000013dc */
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
    /* Entry: 0x100001444 */
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
    /* block 0x100001444 */
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
    /* Entry: 0x100001498 */
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
    /* block 0x100001498 */
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
    /* branch to 0x1000014d0 */ /* b 0x1000014d0 */
    /* loop kind: while_like */
    /* loop header: 0x1000014d0 */
    /* loop exits: ['0x10000151c', '0x100001550'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000014d8 after subs at 0x1000014d4; target 0x100001550; loop polarity inverted")) {
        /* if/else condition block: 0x1000014d0 */
        /* merge block: 0x100001540 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000014d8 after subs at 0x1000014d4; target 0x100001550")) {
            /* block 0x100001504 */
            /* branch to 0x100001508 */ /* b 0x100001508 */
            /* block 0x100001508 */
            /* branch to 0x100001540 */ /* b 0x100001540 */
        } else {
            /* block 0x10000150c */
            tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
            tmp_x8 = tmp_x8 & 63; /* and x8,x8,#0x3f */
            tmp_x8 = tmp_x8 - 41; /* subs x8,x8,#0x29; flags updated */
            /* conditional branch b.ne -> 0x100001524 */
            /* block 0x100001524 */
            tmp_x0 = stack_16; /* ldr x0,[sp, #0x10] */
            tmp_x1 = (i64)(i32)stack_12; /* ldrsw x1,[sp, #0xc] */
            call_0x1000012b0(tmp_x0, tmp_x1); /* bl 0x1000012b0; args refined from same-block evidence */
            /* block 0x100001530 */
            tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
            tmp_x8 = tmp_x8 ^ tmp_x0; /* eor x8,x8,x0 */
            stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
            /* branch to 0x100001540 */ /* b 0x100001540 */
        }
        /* block 0x100001540 */
        tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
        /* branch to 0x1000014d0 */ /* b 0x1000014d0 */
    }
    /* block 0x10000151c */
    /* branch to 0x100001520 */ /* b 0x100001520 */
    /* block 0x100001520 */
    /* branch to 0x100001550 */ /* b 0x100001550 */
    /* block 0x100001550 */
    tmp_x0 = stack_16; /* ldr x0,[sp, #0x10] */
    tmp_fp = stack_48; /* ldp x29,x30,[sp, #0x30] */
    tmp_lr = stack_56; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 64; /* add sp,sp,#0x40 */
    return tmp_x0; /* return value from x0 before ret */

}

uint64_t tri_b(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_30h)
{
    /* Entry: 0x100001560 */
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
    /* block 0x100001560 */
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
    /* branch to 0x100001590 */ /* b 0x100001590 */
    /* loop kind: while_like */
    /* loop header: 0x100001590 */
    /* loop exits: ['0x10000160c', '0x100001628'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100001598 after subs at 0x100001594; target 0x100001628; loop polarity inverted")) {
        /* if/else condition block: 0x100001590 */
        /* merge block: 0x100001618 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x100001598 after subs at 0x100001594; target 0x100001628")) {
            /* block 0x1000015f8 */
            /* branch to 0x1000015fc */ /* b 0x1000015fc */
            /* block 0x1000015fc */
            /* branch to 0x100001618 */ /* b 0x100001618 */
        } else {
            /* block 0x100001600 */
            tmp_w8 = stack_16; /* ldrb w8,[sp, #0x10] */
            tmp_x8 = tmp_x8 - 165; /* subs x8,x8,#0xa5; flags updated */
            /* conditional branch b.ne -> 0x100001614 */
            /* block 0x100001614 */
            /* branch to 0x100001618 */ /* b 0x100001618 */
        }
        /* block 0x100001618 */
        tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
        /* branch to 0x100001590 */ /* b 0x100001590 */
    }
    /* block 0x10000160c */
    /* branch to 0x100001610 */ /* b 0x100001610 */
    /* block 0x100001610 */
    /* branch to 0x100001628 */ /* b 0x100001628 */
    /* block 0x100001628 */
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
    /* Entry: 0x100001648 */
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
        /* block 0x100001648 */
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
        /* branch to 0x100001670 */ /* b 0x100001670 */
        /* block 0x100001670 */
        tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
        tmp_w8 = tmp_w8 - 16; /* subs w8,w8,#0x10; flags updated */
        /* conditional branch b.ge -> 0x100001820 */
        /* block 0x10000167c */
        /* branch to 0x100001680 */ /* b 0x100001680 */
        /* block 0x100001680 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x9 = stack_m16; /* ldur x9,[x29, #-0x10] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        tmp_x8 = tmp_x8 & 7; /* and x8,x8,#0x7 */
        stack_0 = tmp_x8; /* str x8,[sp] */
        /* cbz tmp_x8 -> 0x10000170c */
        /* block 0x1000016a8 */
        /* branch to 0x1000016ac */ /* b 0x1000016ac */
        /* block 0x1000016ac */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 - 1; /* subs x8,x8,#0x1; flags updated */
        /* conditional branch b.eq -> 0x100001728 */
        /* block 0x1000016b8 */
        /* branch to 0x1000016bc */ /* b 0x1000016bc */
        /* block 0x1000016bc */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 - 2; /* subs x8,x8,#0x2; flags updated */
        /* conditional branch b.eq -> 0x10000174c */
        /* block 0x1000016c8 */
        /* branch to 0x1000016cc */ /* b 0x1000016cc */
        /* block 0x1000016cc */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 - 3; /* subs x8,x8,#0x3; flags updated */
        /* conditional branch b.eq -> 0x100001770 */
        /* block 0x1000016d8 */
        /* branch to 0x1000016dc */ /* b 0x1000016dc */
        /* block 0x1000016dc */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 - 4; /* subs x8,x8,#0x4; flags updated */
        /* conditional branch b.eq -> 0x100001788 */
        /* block 0x1000016e8 */
        /* branch to 0x1000016ec */ /* b 0x1000016ec */
        /* block 0x1000016ec */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 - 5; /* subs x8,x8,#0x5; flags updated */
        /* conditional branch b.eq -> 0x1000017c8 */
        /* block 0x1000016f8 */
        /* branch to 0x1000016fc */ /* b 0x1000016fc */
        /* block 0x1000016fc */
        tmp_x8 = stack_0; /* ldr x8,[sp] */
        tmp_x8 = tmp_x8 - 6; /* subs x8,x8,#0x6; flags updated */
        /* conditional branch b.eq -> 0x1000017cc */
        /* block 0x100001708 */
        /* branch to 0x1000017ec */ /* b 0x1000017ec */
        /* block 0x10000170c */
        tmp_x8 = stack_m8; /* ldur x8,[x29, #-0x8] */
        tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
        tmp_x9 = tmp_x8 ^ tmp_x9; /* eor x9,x8,x9 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x10000180c */ /* b 0x10000180c */
        /* block 0x100001728 */
        tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
        tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
        tmp_x10 = 3; /* mov x10,#0x3 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x9 = tmp_x8 + tmp_x9; /* add x9,x8,x9 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x10000180c */ /* b 0x10000180c */
        /* block 0x10000174c */
        tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
        tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
        tmp_x10 = 5; /* mov x10,#0x5 */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x9 = tmp_x8 + tmp_x9; /* add x9,x8,x9 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x8 = tmp_x8 - tmp_x9; /* subs x8,x8,x9; flags updated */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x10000180c */ /* b 0x10000180c */
        /* block 0x100001770 */
        tmp_x9 = stack_16; /* ldr x9,[sp, #0x10] */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x8 = tmp_x8 >> 2; /* lsr x8,x8,#0x2 */
        tmp_x8 = tmp_x8 ^ (tmp_x9 << 5); /* eor x8,x8,x9, LSL #0x5 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x10000180c */ /* b 0x10000180c */
        /* block 0x100001788 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        /* tbz tmp_w8 bit 0 -> 0x1000017ac */
        /* block 0x100001790 */
        /* branch to 0x100001794 */ /* b 0x100001794 */
        /* block 0x100001794 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x9 = 22136; /* mov x9,#0x5678 */
        /* 0x10000179c: unsupported instruction: movk x9,#0x1234, LSL #16 */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x1000017c4 */ /* b 0x1000017c4 */
        /* block 0x1000017ac */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x9 = 17185; /* mov x9,#0x4321 */
        /* 0x1000017b4: unsupported instruction: movk x9,#0x8765, LSL #16 */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x1000017c4 */ /* b 0x1000017c4 */
        /* block 0x1000017c4 */
        /* branch to 0x10000180c */ /* b 0x10000180c */
        /* block 0x1000017c8 */
        /* branch to 0x100001810 */ /* b 0x100001810 */
        /* block 0x1000017cc */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x9 = (i64)(i32)stack_12; /* ldrsw x9,[sp, #0xc] */
        tmp_x0 = tmp_x8 ^ tmp_x9; /* eor x0,x8,x9 */
        call_0x100001220(tmp_x0); /* bl 0x100001220; args refined from same-block evidence */
        /* block 0x1000017dc */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x8 = tmp_x8 + tmp_x0; /* add x8,x8,x0 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x10000180c */ /* b 0x10000180c */
        /* block 0x1000017ec */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_x9 = 47806; /* mov x9,#0xbabe */
        /* 0x1000017f4: unsupported instruction: movk x9,#0xcafe, LSL #16 */
        /* 0x1000017f8: unsupported instruction: movk x9,#0xbeef, LSL #32 */
        /* 0x1000017fc: unsupported instruction: movk x9,#0xdead, LSL #48 */
        tmp_x8 = tmp_x8 ^ tmp_x9; /* eor x8,x8,x9 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        /* branch to 0x10000180c */ /* b 0x10000180c */
        /* block 0x10000180c */
        /* branch to 0x100001810 */ /* b 0x100001810 */
        /* block 0x100001810 */
        tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
        /* branch to 0x100001670 */ /* b 0x100001670 */
        /* block 0x100001820 */
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
    /* Entry: 0x10000183c */
    /* Body status: partially_structured */
    /* 1 basic block(s), 4 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[16], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x16 = 0;

    /* Control flow structure: */
    /* block 0x10000183c */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.printf */
    tmp_x16 = *(u64 *)(tmp_x16 + 16); /* ldr x16, [x16, 0x10] */
    /* branch to tmp_x16 */ /* br x16 */
    /* 0x100001848: unsupported instruction: invalid */

    /* return value unknown */
    return 0;
}

int32_t printf(void * format)
{
    /* Entry: 0x100001830 */
    /* Body status: structured */
    /* 1 basic block(s), 3 instruction(s) */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[0], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x16 = 0;

    /* Control flow structure: */
    /* block 0x100001830 */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.printf */
    tmp_x16 = *(u64 *)(tmp_x16); /* ldr x16, [x16] */
    /* branch to tmp_x16 */ /* br x16 */
    /* block 0x10000183c: no lowered statements */

    /* return value unknown */
    return 0;
}

