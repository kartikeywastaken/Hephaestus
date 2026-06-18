/*
 * recovered.c — Phase 5.7.2 Conservative ARM64 Coverage Cleanup
 * Schema version: 5.7.2
 * Generated: 2026-06-18T18:56:57Z
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
uint64_t FUN_1000004cc(void);
int32_t main(void);
uint64_t scan_items(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_50h);
uint64_t mixed_driver(void);
uint64_t FUN_1000007a0(void);
uint64_t cfg_pressure(void);
uint64_t FUN_100000998(void);
uint64_t nested_control(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_20h);
uint64_t pointer_walk(int32_t arg1, uint64_t arg2, uint64_t arg3, int32_t arg_30h);
uint64_t indirect_pressure(void);
uint64_t FUN_100000c48(void);
uint64_t mix_score(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_10h);
uint64_t byte_halfword_pressure(void);
uint64_t rotl32(int32_t arg1, uint64_t arg2, uint64_t arg_10h);
uint64_t stack_chk_fail(void);
int32_t printf(void * format);
int32_t puts(void * s);
uint64_t strlen(void * s);

/* Conservative call target helpers */
u64 call_0x100000740();
u64 call_0x1000009a8();
u64 call_0x100000ad8();
u64 call_0x100000c54();
u64 call_0x100000d4c();
u64 call_0x100000d94();
u64 call_0x100000da0();
u64 call_0x100000dac();
u64 call_0x100000db8();

/* ================================================== */
/*                 Function Definitions                */
/* ================================================== */

int32_t main(int32_t argc, char ** argv)
{
    /* Entry: 0x100000460 */
    /* Body status: structured */
    /* 29 basic block(s), 184 instruction(s) */

    /* ABI argument bindings: */
    /*   ? => param 1 (stack_save_restore) */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 64, 68, 74, 124, 156], sizes=[4] */
    /*   base=x10, kind=record_like, offsets=[4, 8, 9], sizes=[4] */
    /*   base=x8, kind=array_like, offsets=[0, 8], sizes=[4] */
    /*   base=x9, kind=array_like, offsets=[0, 10], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 tmp_x11 = 0;
    u64 tmp_x12 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u32 tmp_w11 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m8 = 0;
    u32 stack_20 = 0;
    u64 stack_24 = 0;
    u64 stack_28 = 0;
    u64 stack_44 = 0;
    u64 stack_48 = 0;
    u32 stack_52 = 0;
    u64 stack_56 = 0;
    u64 stack_124 = 0;
    u64 stack_156 = 0;
    u64 stack_192 = 0;
    u64 stack_200 = 0;

    /* Control flow structure: */
    /* if condition block: 0x100000460 */
    /* merge block: 0x1000004c4 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.le at 0x10000049c after subs at 0x100000498; target 0x1000004c4")) {
        /* block 0x1000004a0 */
        /* branch to 0x1000004a4 */ /* b 0x1000004a4 */
        /* block 0x1000004a4 */
        arg1 = stack_56; /* ldr x8, [sp + var_38h] */
        tmp_x0 = *(u64 *)(arg1 + 8); /* ldr x0, [x8, 8] */
        call_0x100000db8(tmp_x0); /* bl sym.imp.strlen; args refined from same-block evidence */
        tmp_x9 = tmp_x0; /* mov x9, x0 */
        arg1 = stack_52; /* ldr w8, [sp + var_34h] */
        arg1 = arg1 ^ tmp_w9; /* eor w8, w8, w9 */
        stack_52 = arg1; /* str w8, [sp + var_34h] */
        /* branch to 0x1000004c4 */ /* b 0x1000004c4 */
    }
    /* block 0x1000004c4 */
    stack_48 = 0; /* str wzr, [sp + var_30h] */
    /* branch to 0x1000004cc */ /* b 0x1000004cc */
    /* loop kind: while_like */
    /* loop header: 0x1000004cc */
    /* loop exits: ['0x1000005dc'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000004d4 after subs at 0x1000004d0; target 0x1000005dc; loop polarity inverted")) {
        /* if/else condition block: 0x1000004cc */
        /* merge block: 0x100000544 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000004d4 after subs at 0x1000004d0; target 0x1000005dc")) {
            /* block 0x100000518 */
            /* branch to 0x10000051c */ /* b 0x10000051c */
            /* block 0x10000051c */
            arg1 = stack_48; /* ldr w8, [sp + var_30h] */
            tmp_w9 = 11; /* mov w9, 0xb */
            arg1 = arg1 * tmp_w9; /* mul w8, w8, w9 */
            stack_24 = arg1; /* str w8, [sp + var_0h_2] */
            /* branch to 0x100000544 */ /* b 0x100000544 */
        } else {
            /* block 0x100000530 */
            arg1 = stack_48; /* ldr w8, [sp + var_30h] */
            tmp_w9 = 7; /* mov w9, 7 */
            /* 0x100000538: unsupported instruction: mneg w8, w8, w9 */
            stack_24 = arg1; /* str w8, [sp + var_0h_2] */
            /* branch to 0x100000544 */ /* b 0x100000544 */
        }
        /* block 0x100000544 */
        arg1 = stack_24; /* ldr w8, [sp + var_0h_2] */
        tmp_x9 = (i64)(i32)stack_48; /* ldrsw x9, [sp + var_30h] */
        tmp_x11 = 12; /* mov x11, 0xc */
        tmp_x12 = tmp_x9 * tmp_x11; /* mul x12, x9, x11 */
        tmp_x9 = tmp_sp + 88; /* add x9, sp, 0x58 */
        tmp_x10 = tmp_x9; /* mov x10, x9 */
        tmp_x10 = tmp_x10 + tmp_x12; /* add x10, x10, x12 */
        *(u32 *)(tmp_x10 + 4) = arg1; /* str w8, [x10, 4] */
        arg1 = stack_48; /* ldr w8, [sp + var_30h] */
        tmp_w10 = 29; /* mov w10, 0x1d */
        arg1 = arg1 * tmp_w10; /* mul w8, w8, w10 */
        tmp_w10 = stack_52; /* ldr w10, [sp + var_34h] */
        arg1 = arg1 ^ tmp_w10; /* eor w8, w8, w10 */
        tmp_x10 = (i64)(i32)stack_48; /* ldrsw x10, [sp + var_30h] */
        tmp_x12 = tmp_x10 * tmp_x11; /* mul x12, x10, x11 */
        tmp_x10 = tmp_x9; /* mov x10, x9 */
        tmp_x10 = tmp_x10 + tmp_x12; /* add x10, x10, x12 */
        *(u8 *)(tmp_x10 + 8) = arg1; /* strb w8, [x10, 8] */
        arg1 = stack_48; /* ldr w8, [sp + var_30h] */
        arg1 = arg1 & 7; /* and w8, w8, 7 */
        tmp_x10 = (i64)(i32)stack_48; /* ldrsw x10, [sp + var_30h] */
        tmp_x12 = tmp_x10 * tmp_x11; /* mul x12, x10, x11 */
        tmp_x10 = tmp_x9; /* mov x10, x9 */
        tmp_x10 = tmp_x10 + tmp_x12; /* add x10, x10, x12 */
        *(u8 *)(tmp_x10 + 9) = arg1; /* strb w8, [x10, 9] */
        arg1 = stack_48; /* ldr w8, [sp + var_30h] */
        tmp_w10 = 13; /* mov w10, 0xd */
        arg1 = arg1 * tmp_w10; /* mul w8, w8, w10 */
        arg1 = arg1 + 100; /* add w8, w8, 0x64 */
        tmp_x10 = (i64)(i32)stack_48; /* ldrsw x10, [sp + var_30h] */
        tmp_x10 = tmp_x10 * tmp_x11; /* mul x10, x10, x11 */
        tmp_x9 = tmp_x9 + tmp_x10; /* add x9, x9, x10 */
        *(u16 *)(tmp_x9 + 10) = arg1; /* strh w8, [x9, 0xa] */
        /* branch to 0x1000005cc */ /* b 0x1000005cc */
        /* block 0x1000005cc */
        arg1 = stack_48; /* ldr w8, [sp + var_30h] */
        arg1 = arg1 + 1; /* add w8, w8, 1 */
        stack_48 = arg1; /* str w8, [sp + var_30h] */
        /* branch to 0x1000004cc */ /* b 0x1000004cc */
    }
    /* block 0x1000005dc */
    stack_124 = 0; /* str wzr, [sp + var_7ch] */
    arg1 = stack_156; /* ldrb w8, [sp + var_9ch] */
    arg1 = arg1 | 32; /* orr w8, w8, 0x20 */
    stack_156 = arg1; /* strb w8, [sp + var_9ch] */
    stack_44 = 0; /* str wzr, [sp + var_2ch] */
    /* branch to 0x1000005f4 */ /* b 0x1000005f4 */
    /* loop kind: while_like */
    /* loop header: 0x1000005f4 */
    /* loop exits: ['0x100000650'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000005fc after subs at 0x1000005f8; target 0x100000650; loop polarity inverted")) {
        /* block 0x1000005f4 */
        arg1 = stack_44; /* ldr w8, [sp + var_2ch] */
        arg1 = arg1 - 16; /* subs w8, w8, 0x10; flags updated */
        /* conditional branch b.ge -> 0x100000650 */
        /* block 0x100000600 */
        /* branch to 0x100000604 */ /* b 0x100000604 */
        /* block 0x100000604 */
        arg1 = stack_52; /* ldr w8, [sp + var_34h] */
        tmp_w9 = stack_44; /* ldr w9, [sp + var_2ch] */
        tmp_w11 = 8; /* mov w11, 8 */
        tmp_w10 = ((i32)tmp_w9) / ((i32)tmp_w11); /* sdiv w10, w9, w11 */
        tmp_w10 = tmp_w10 * tmp_w11; /* mul w10, w10, w11 */
        tmp_w9 = tmp_w9 - tmp_w10; /* subs w9, w9, w10; flags updated */
        arg1 = arg1 >> tmp_w9; /* lsr w8, w8, w9 */
        tmp_w9 = stack_44; /* ldr w9, [sp + var_2ch] */
        tmp_w10 = 31; /* mov w10, 0x1f */
        tmp_w9 = tmp_w9 * tmp_w10; /* mul w9, w9, w10 */
        arg1 = arg1 ^ tmp_w9; /* eor w8, w8, w9 */
        tmp_x10 = (i64)(i32)stack_44; /* ldrsw x10, [sp + var_2ch] */
        tmp_x9 = tmp_sp + 72; /* add x9, sp, 0x48 */
        *(u8 *)(tmp_x9) = arg1; /* strb w8, [x9, x10] */
        /* branch to 0x100000640 */ /* b 0x100000640 */
        /* block 0x100000640 */
        arg1 = stack_44; /* ldr w8, [sp + var_2ch] */
        arg1 = arg1 + 1; /* add w8, w8, 1 */
        stack_44 = arg1; /* str w8, [sp + var_2ch] */
        /* branch to 0x1000005f4 */ /* b 0x1000005f4 */
    }
    /* if/else condition block: 0x100000650 */
    /* merge block: 0x100000708 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbnz w8 at 0x1000006a8 targeting 0x1000006c0; polarity inverted")) {
        /* block 0x1000006ac */
        /* branch to 0x1000006b0 */ /* b 0x1000006b0 */
        /* block 0x1000006b0 */
        tmp_x0 = 0x100000000; /* adrp x0, 0x100000000 */
        tmp_x0 = tmp_x0 + 3524; /* add x0, x0, 0xdc4 */
        call_0x100000dac(tmp_x0); /* bl sym.imp.puts; args refined from same-block evidence */
        /* branch to 0x100000708 */ /* b 0x100000708 */
    } else {
        /* if/else condition block: 0x1000006c0 */
        /* merge block: 0x100000704 */
        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: tbz w8 bit 0 at 0x1000006c4 targeting 0x1000006e8; polarity inverted")) {
            /* block 0x1000006c8 */
            /* branch to 0x1000006cc */ /* b 0x1000006cc */
            /* block 0x1000006cc */
            arg1 = stack_28; /* ldr w8, [sp + var_1ch] */
            tmp_x9 = tmp_sp; /* mov x9, sp */
            *(u64 *)(tmp_x9) = arg1; /* str x8, [x9] */
            tmp_x0 = 0x100000000; /* adrp x0, 0x100000000 */
            tmp_x0 = tmp_x0 + 3529; /* add x0, x0, 0xdc9 */
            call_0x100000da0(tmp_x0); /* bl sym.imp.printf; args refined from same-block evidence */
            /* branch to 0x100000704 */ /* b 0x100000704 */
        } else {
            /* block 0x1000006e8 */
            arg1 = stack_28; /* ldr w8, [sp + var_1ch] */
            tmp_x9 = tmp_sp; /* mov x9, sp */
            *(u64 *)(tmp_x9) = arg1; /* str x8, [x9] */
            tmp_x0 = 0x100000000; /* adrp x0, 0x100000000 */
            tmp_x0 = tmp_x0 + 3542; /* add x0, x0, 0xdd6 */
            call_0x100000da0(tmp_x0); /* bl sym.imp.printf; args refined from same-block evidence */
            /* branch to 0x100000704 */ /* b 0x100000704 */
        }
        /* block 0x100000704 */
        /* branch to 0x100000708 */ /* b 0x100000708 */
    }
    /* block 0x100000708 */
    arg1 = stack_28; /* ldrb w8, [sp + var_1ch] */
    stack_20 = arg1; /* str w8, [sp + var_14h] */
    tmp_x9 = stack_m8; /* ldur x9, [x29, -8] */
    arg1 = 0x100004000; /* adrp x8, reloc.__stack_chk_fail */
    arg1 = *(u64 *)(arg1 + 8); /* ldr x8, [x8, 8] */
    arg1 = *(u64 *)(arg1); /* ldr x8, [x8] */
    arg1 = arg1 - tmp_x9; /* subs x8, x8, x9; flags updated */
    /* conditional branch b.eq -> 0x100000730 */
    /* block 0x100000730 */
    tmp_w0 = stack_20; /* ldr w0, [sp + var_14h] */
    tmp_fp = stack_192; /* ldp x29, x30, [sp + var_c0h] */
    tmp_lr = stack_200; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 208; /* add sp, sp, 0xd0 */
    return tmp_w0; /* return value from w0 before ret */
    /* block 0x100000728 */
    /* branch to 0x10000072c */ /* b 0x10000072c */
    /* block 0x10000072c */
    call_0x100000d94(); /* bl sym.imp.__stack_chk_fail */

}

uint64_t FUN_1000004cc(void)
{
    /* Entry: 0x1000004cc */
    /* Body status: structured */
    /* 7 basic block(s), 31 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[24, 48], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u32 stack_24 = 0;
    u64 stack_48 = 0;

    /* Control flow structure: */
    /* block 0x1000004cc */
    tmp_w8 = stack_48; /* ldr w8,[sp, #0x30] */
    tmp_w8 = tmp_w8 - 8; /* subs w8,w8,#0x8; flags updated */
    /* conditional branch b.ge -> 0x1000005dc */
    /* block 0x1000004d8 */
    /* branch to 0x1000004dc */ /* b 0x1000004dc */
    /* block 0x1000004dc */
    tmp_w8 = stack_48; /* ldr w8,[sp, #0x30] */
    tmp_w9 = 17; /* mov w9,#0x11 */
    tmp_w8 = tmp_w8 * tmp_w9; /* mul w8,w8,w9 */
    tmp_w8 = tmp_w8 + 3; /* add w8,w8,#0x3 */
    tmp_x9 = (i64)(i32)stack_48; /* ldrsw x9,[sp, #0x30] */
    tmp_x10 = 12; /* mov x10,#0xc */
    tmp_x10 = tmp_x9 * tmp_x10; /* mul x10,x9,x10 */
    tmp_x9 = tmp_sp + 88; /* add x9,sp,#0x58 */
    *(u32 *)(tmp_x9 + tmp_x10) = tmp_w8; /* str w8,[x9, x10, LSL #0x0] */
    tmp_w8 = stack_48; /* ldr w8,[sp, #0x30] */
    tmp_w10 = 2; /* mov w10,#0x2 */
    tmp_w9 = ((i32)tmp_w8) / ((i32)tmp_w10); /* sdiv w9,w8,w10 */
    tmp_w9 = tmp_w9 * tmp_w10; /* mul w9,w9,w10 */
    tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
    /* cbnz tmp_w8 -> 0x100000530 */
    /* block 0x100000530 */
    tmp_w8 = stack_48; /* ldr w8,[sp, #0x30] */
    tmp_w9 = 7; /* mov w9,#0x7 */
    /* 0x100000538: unsupported instruction: mneg w8,w8,w9 */
    stack_24 = tmp_w8; /* str w8,[sp, #0x18] */
    /* branch to 0x100000544 */ /* b 0x100000544 */
    /* block 0x100000518 */
    /* branch to 0x10000051c */ /* b 0x10000051c */
    /* block 0x10000051c */
    tmp_w8 = stack_48; /* ldr w8,[sp, #0x30] */
    tmp_w9 = 11; /* mov w9,#0xb */
    tmp_w8 = tmp_w8 * tmp_w9; /* mul w8,w8,w9 */
    stack_24 = tmp_w8; /* str w8,[sp, #0x18] */
    /* branch to 0x100000544 */ /* b 0x100000544 */
    /* block 0x100000544 */
    tmp_w8 = stack_24; /* ldr w8,[sp, #0x18] */

    /* return value unknown */
    return 0;
}

int32_t main(void)
{
    /* Entry: 0x100000548 */
    /* Body status: unstructured */
    /* 25 basic block(s), 126 instruction(s) */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[20, 28, 32, 36, 40, 44, 48, 52, 74, 124, 156], sizes=[1, 4] */
    /*   base=x10, kind=record_like, offsets=[4, 8, 9], sizes=[1, 4] */
    /*   base=x8, kind=array_like, offsets=[0, 8], sizes=[8] */
    /*   base=x9, kind=record_like, offsets=[0, 10], sizes=[2, 8] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x1 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u64 tmp_x11 = 0;
    u64 tmp_x12 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u32 tmp_w2 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u32 tmp_w11 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u64 stack_m8 = 0;
    u32 stack_20 = 0;
    u32 stack_28 = 0;
    u32 stack_32 = 0;
    u32 stack_36 = 0;
    u32 stack_40 = 0;
    u64 stack_44 = 0;
    u64 stack_48 = 0;
    u32 stack_52 = 0;
    u32 stack_74 = 0;
    u64 stack_124 = 0;
    u32 stack_156 = 0;
    u64 stack_192 = 0;
    u64 stack_200 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: fragmented_loop_body */
    {
        /* block 0x100000548 */
        tmp_x9 = (i64)(i32)stack_48; /* ldrsw x9,[sp, #0x30] */
        tmp_x11 = 12; /* mov x11,#0xc */
        tmp_x12 = tmp_x9 * tmp_x11; /* mul x12,x9,x11 */
        tmp_x9 = tmp_sp + 88; /* add x9,sp,#0x58 */
        tmp_x10 = tmp_x9; /* mov x10,x9 */
        tmp_x10 = tmp_x10 + tmp_x12; /* add x10,x10,x12 */
        *(u32 *)(tmp_x10 + 4) = tmp_w8; /* str w8,[x10, #0x4] */
        tmp_w8 = stack_48; /* ldr w8,[sp, #0x30] */
        tmp_w10 = 29; /* mov w10,#0x1d */
        tmp_w8 = tmp_w8 * tmp_w10; /* mul w8,w8,w10 */
        tmp_w10 = stack_52; /* ldr w10,[sp, #0x34] */
        tmp_w8 = tmp_w8 ^ tmp_w10; /* eor w8,w8,w10 */
        tmp_x10 = (i64)(i32)stack_48; /* ldrsw x10,[sp, #0x30] */
        tmp_x12 = tmp_x10 * tmp_x11; /* mul x12,x10,x11 */
        tmp_x10 = tmp_x9; /* mov x10,x9 */
        tmp_x10 = tmp_x10 + tmp_x12; /* add x10,x10,x12 */
        *(u8 *)(tmp_x10 + 8) = tmp_w8; /* strb w8,[x10, #0x8] */
        tmp_w8 = stack_48; /* ldr w8,[sp, #0x30] */
        tmp_w8 = tmp_w8 & 7; /* and w8,w8,#0x7 */
        tmp_x10 = (i64)(i32)stack_48; /* ldrsw x10,[sp, #0x30] */
        tmp_x12 = tmp_x10 * tmp_x11; /* mul x12,x10,x11 */
        tmp_x10 = tmp_x9; /* mov x10,x9 */
        tmp_x10 = tmp_x10 + tmp_x12; /* add x10,x10,x12 */
        *(u8 *)(tmp_x10 + 9) = tmp_w8; /* strb w8,[x10, #0x9] */
        tmp_w8 = stack_48; /* ldr w8,[sp, #0x30] */
        tmp_w10 = 13; /* mov w10,#0xd */
        tmp_w8 = tmp_w8 * tmp_w10; /* mul w8,w8,w10 */
        tmp_w8 = tmp_w8 + 100; /* add w8,w8,#0x64 */
        tmp_x10 = (i64)(i32)stack_48; /* ldrsw x10,[sp, #0x30] */
        tmp_x10 = tmp_x10 * tmp_x11; /* mul x10,x10,x11 */
        tmp_x9 = tmp_x9 + tmp_x10; /* add x9,x9,x10 */
        *(u16 *)(tmp_x9 + 10) = tmp_w8; /* strh w8,[x9, #0xa] */
        /* branch to 0x1000005cc */ /* b 0x1000005cc */
        /* block 0x1000005cc */
        tmp_w8 = stack_48; /* ldr w8,[sp, #0x30] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_48 = tmp_w8; /* str w8,[sp, #0x30] */
        /* branch to 0x1000004cc */ /* b 0x1000004cc */
        /* block 0x1000005dc */
        stack_124 = 0; /* str wzr,[sp, #0x7c] */
        tmp_w8 = stack_156; /* ldrb w8,[sp, #0x9c] */
        tmp_w8 = tmp_w8 | 32; /* orr w8,w8,#0x20 */
        stack_156 = tmp_w8; /* strb w8,[sp, #0x9c] */
        stack_44 = 0; /* str wzr,[sp, #0x2c] */
        /* branch to 0x1000005f4 */ /* b 0x1000005f4 */
        /* block 0x1000005f4 */
        tmp_w8 = stack_44; /* ldr w8,[sp, #0x2c] */
        tmp_w8 = tmp_w8 - 16; /* subs w8,w8,#0x10; flags updated */
        /* conditional branch b.ge -> 0x100000650 */
        /* block 0x100000600 */
        /* branch to 0x100000604 */ /* b 0x100000604 */
        /* block 0x100000604 */
        tmp_w8 = stack_52; /* ldr w8,[sp, #0x34] */
        tmp_w9 = stack_44; /* ldr w9,[sp, #0x2c] */
        tmp_w11 = 8; /* mov w11,#0x8 */
        tmp_w10 = ((i32)tmp_w9) / ((i32)tmp_w11); /* sdiv w10,w9,w11 */
        tmp_w10 = tmp_w10 * tmp_w11; /* mul w10,w10,w11 */
        tmp_w9 = tmp_w9 - tmp_w10; /* subs w9,w9,w10; flags updated */
        tmp_w8 = tmp_w8 >> tmp_w9; /* lsr w8,w8,w9 */
        tmp_w9 = stack_44; /* ldr w9,[sp, #0x2c] */
        tmp_w10 = 31; /* mov w10,#0x1f */
        tmp_w9 = tmp_w9 * tmp_w10; /* mul w9,w9,w10 */
        tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8,w8,w9 */
        tmp_x10 = (i64)(i32)stack_44; /* ldrsw x10,[sp, #0x2c] */
        tmp_x9 = tmp_sp + 72; /* add x9,sp,#0x48 */
        *(u8 *)(tmp_x9 + tmp_x10) = tmp_w8; /* strb w8,[x9, x10, LSL ] */
        /* branch to 0x100000640 */ /* b 0x100000640 */
        /* block 0x100000640 */
        tmp_w8 = stack_44; /* ldr w8,[sp, #0x2c] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_44 = tmp_w8; /* str w8,[sp, #0x2c] */
        /* branch to 0x1000005f4 */ /* b 0x1000005f4 */
        /* block 0x100000650 */
        tmp_w2 = stack_52; /* ldr w2,[sp, #0x34] */
        tmp_x0 = tmp_sp + 88; /* add x0,sp,#0x58 */
        tmp_w1 = 8; /* mov w1,#0x8 */
        call_0x100000740(tmp_x0, tmp_w1, tmp_w2); /* bl 0x100000740; args refined from same-block evidence */
        /* block 0x100000660 */
        stack_40 = tmp_w0; /* str w0,[sp, #0x28] */
        tmp_w0 = 5; /* mov w0,#0x5 */
        tmp_w1 = 7; /* mov w1,#0x7 */
        tmp_w2 = 3; /* mov w2,#0x3 */
        call_0x1000009a8(tmp_w0, tmp_w1, tmp_w2); /* bl 0x1000009a8; args refined from same-block evidence */
        /* block 0x100000674 */
        stack_36 = tmp_w0; /* str w0,[sp, #0x24] */
        tmp_x0 = tmp_sp + 72; /* add x0,sp,#0x48 */
        tmp_w2 = stack_74; /* ldrb w2,[sp, #0x4a] */
        tmp_x1 = 16; /* mov x1,#0x10 */
        call_0x100000ad8(tmp_x0, tmp_x1, tmp_w2); /* bl 0x100000ad8; args refined from same-block evidence */
        /* block 0x100000688 */
        stack_32 = tmp_w0; /* str w0,[sp, #0x20] */
        tmp_w8 = stack_40; /* ldr w8,[sp, #0x28] */
        tmp_w9 = stack_36; /* ldr w9,[sp, #0x24] */
        tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
        tmp_w9 = stack_32; /* ldr w9,[sp, #0x20] */
        tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
        stack_28 = tmp_w8; /* str w8,[sp, #0x1c] */
        tmp_w8 = stack_28; /* ldr w8,[sp, #0x1c] */
        /* cbnz tmp_w8 -> 0x1000006c0 */
        /* block 0x1000006ac */
        /* branch to 0x1000006b0 */ /* b 0x1000006b0 */
        /* block 0x1000006b0 */
        tmp_x0 = 0x100000000; /* adrp x0,0x100000000 */
        tmp_x0 = tmp_x0 + 3524; /* add x0,x0,#0xdc4 */
        call_0x100000dac(tmp_x0); /* bl 0x100000dac; args refined from same-block evidence */
        /* block 0x1000006bc */
        /* branch to 0x100000708 */ /* b 0x100000708 */
        /* block 0x1000006c0 */
        tmp_w8 = stack_28; /* ldr w8,[sp, #0x1c] */
        /* tbz tmp_w8 bit 31 -> 0x1000006e8 */
        /* block 0x1000006c8 */
        /* branch to 0x1000006cc */ /* b 0x1000006cc */
        /* block 0x1000006cc */
        tmp_w8 = stack_28; /* ldr w8,[sp, #0x1c] */
        tmp_x9 = tmp_sp; /* mov x9,sp */
        *(u64 *)(tmp_x9) = tmp_x8; /* str x8,[x9] */
        tmp_x0 = 0x100000000; /* adrp x0,0x100000000 */
        tmp_x0 = tmp_x0 + 3529; /* add x0,x0,#0xdc9 */
        call_0x100000da0(tmp_x0); /* bl 0x100000da0; args refined from same-block evidence */
        /* block 0x1000006e4 */
        /* branch to 0x100000704 */ /* b 0x100000704 */
        /* block 0x1000006e8 */
        tmp_w8 = stack_28; /* ldr w8,[sp, #0x1c] */
        tmp_x9 = tmp_sp; /* mov x9,sp */
        *(u64 *)(tmp_x9) = tmp_x8; /* str x8,[x9] */
        tmp_x0 = 0x100000000; /* adrp x0,0x100000000 */
        tmp_x0 = tmp_x0 + 3542; /* add x0,x0,#0xdd6 */
        call_0x100000da0(tmp_x0); /* bl 0x100000da0; args refined from same-block evidence */
        /* block 0x100000700 */
        /* branch to 0x100000704 */ /* b 0x100000704 */
        /* block 0x100000704 */
        /* branch to 0x100000708 */ /* b 0x100000708 */
        /* block 0x100000708 */
        tmp_w8 = stack_28; /* ldrb w8,[sp, #0x1c] */
        stack_20 = tmp_w8; /* str w8,[sp, #0x14] */
        tmp_x9 = stack_m8; /* ldur x9,[x29, #-0x8] */
        tmp_x8 = 0x100004000; /* adrp x8,0x100004000 */
        tmp_x8 = *(u64 *)(tmp_x8 + 8); /* ldr x8,[x8, #0x8] */
        tmp_x8 = *(u64 *)(tmp_x8); /* ldr x8,[x8] */
        tmp_x8 = tmp_x8 - tmp_x9; /* subs x8,x8,x9; flags updated */
        /* conditional branch b.eq -> 0x100000730 */
        /* block 0x100000728 */
        /* branch to 0x10000072c */ /* b 0x10000072c */
        /* block 0x10000072c */
        call_0x100000d94(); /* bl 0x100000d94 */
        /* block 0x100000730 */
        tmp_w0 = stack_20; /* ldr w0,[sp, #0x14] */
        tmp_fp = stack_192; /* ldp x29,x30,[sp, #0xc0] */
        tmp_lr = stack_200; /* paired load second register inferred offset +8 */
        tmp_sp = tmp_sp + 208; /* add sp,sp,#0xd0 */
        return tmp_w0; /* return value from w0 before ret */
    }
    /* unstructured region end */

}

uint64_t scan_items(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_50h)
{
    /* Entry: 0x100000740 */
    /* Body status: unstructured */
    /* 39 basic block(s), 154 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[12, 16, 28, 32], sizes=[4] */
    /*   base=x8, kind=record_like, offsets=[0, 4, 8, 9, 10], sizes=[4] */
    /*   base=x9, kind=scalar, offsets=[0], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u64 tmp_x0 = 0;
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u32 tmp_w2 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u64 tmp_fp = 0;
    u64 tmp_lr = 0;
    u32 stack_m4 = 0;
    u64 stack_m16 = 0;
    u32 stack_m20 = 0;
    u32 stack_m24 = 0;
    u32 stack_m28 = 0;
    u64 stack_16 = 0;
    u32 stack_28 = 0;
    u32 stack_32 = 0;
    u64 stack_64 = 0;
    u64 stack_72 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: switch_candidate */
    {
        /* block 0x100000740 */
        tmp_sp = tmp_sp - 80; /* sub sp, sp, 0x50 */
        stack_64 = tmp_fp; /* stp x29, x30, [sp + var_40h] */
        stack_72 = tmp_lr; /* paired store second register inferred offset +8 */
        tmp_fp = tmp_sp + 64; /* add x29, sp, 0x40 */
        stack_m16 = tmp_x0; /* stur x0, [x29, -0x10] */
        stack_m20 = tmp_w1; /* stur w1, [x29, -0x14] */
        stack_m24 = tmp_w2; /* stur w2, [x29, -0x18] */
        tmp_x8 = stack_m16; /* ldur x8, [x29, -0x10] */
        /* cbnz tmp_x8 -> 0x100000770 */
        /* block 0x100000760 */
        /* branch to 0x100000764 */ /* b 0x100000764 */
        /* block 0x100000764 */
        tmp_w8 = -1000; /* mov w8, -0x3e8 */
        stack_m4 = tmp_w8; /* stur w8, [x29, -4] */
        /* branch to 0x100000998 */ /* b 0x100000998 */
        /* block 0x100000770 */
        tmp_w8 = stack_m20; /* ldur w8, [x29, -0x14] */
        tmp_w8 = tmp_w8 - 0; /* subs w8, w8, 0; flags updated */
        /* conditional branch b.gt -> 0x10000078c */
        /* block 0x10000077c */
        /* branch to 0x100000780 */ /* b 0x100000780 */
        /* block 0x100000780 */
        tmp_w8 = -2000; /* mov w8, -0x7d0 */
        stack_m4 = tmp_w8; /* stur w8, [x29, -4] */
        /* branch to 0x100000998 */ /* b 0x100000998 */
        /* block 0x10000078c */
        stack_m28 = 0; /* stur wzr, [x29, -0x1c] */
        stack_32 = 0; /* str wzr, [sp + var_20h] */
        tmp_w8 = stack_m24; /* ldur w8, [x29, -0x18] */
        stack_28 = tmp_w8; /* str w8, [sp + var_1ch] */
        /* branch to 0x1000007a0 */ /* b 0x1000007a0 */
        /* block 0x1000007a0 */
        tmp_w8 = stack_32; /* ldr w8, [sp + var_20h] */
        tmp_w9 = stack_m20; /* ldur w9, [x29, -0x14] */
        tmp_w8 = tmp_w8 - tmp_w9; /* subs w8, w8, w9; flags updated */
        /* conditional branch b.ge -> 0x100000980 */
        /* block 0x1000007d8 */
        /* branch to 0x1000007dc */ /* b 0x1000007dc */
        /* block 0x1000007dc */
        tmp_w8 = stack_m28; /* ldur w8, [x29, -0x1c] */
        tmp_w8 = tmp_w8 - 3; /* subs w8, w8, 3; flags updated */
        stack_m28 = tmp_w8; /* stur w8, [x29, -0x1c] */
        tmp_w8 = stack_32; /* ldr w8, [sp + var_20h] */
        tmp_w8 = tmp_w8 + 1; /* add w8, w8, 1 */
        stack_32 = tmp_w8; /* str w8, [sp + var_20h] */
        /* branch to 0x1000007a0 */ /* b 0x1000007a0 */
        /* block 0x1000007f8 */
        tmp_x8 = stack_16; /* ldr x8, [sp + var_10h] */
        tmp_w8 = *(u8 *)(tmp_x8 + 8); /* ldrb w8, [x8, 8] */
        /* tbz tmp_w8 bit 0 -> 0x100000820 */
        /* block 0x1000008c8 */
        /* branch to 0x1000008cc */ /* b 0x1000008cc */
        /* block 0x1000008d8 */
        /* branch to 0x1000008dc */ /* b 0x1000008dc */
        /* block 0x1000008e8 */
        /* branch to 0x10000091c */ /* b 0x10000091c */
        /* block 0x1000008ec */
        tmp_w8 = stack_m28; /* ldur w8, [x29, -0x1c] */
        tmp_w8 = tmp_w8 + 10; /* add w8, w8, 0xa */
        stack_m28 = tmp_w8; /* stur w8, [x29, -0x1c] */
        /* branch to 0x100000930 */ /* b 0x100000930 */
        /* block 0x1000008fc */
        tmp_w8 = stack_m28; /* ldur w8, [x29, -0x1c] */
        tmp_w8 = tmp_w8 + 20; /* add w8, w8, 0x14 */
        stack_m28 = tmp_w8; /* stur w8, [x29, -0x1c] */
        /* branch to 0x100000930 */ /* b 0x100000930 */
        /* block 0x10000090c */
        tmp_w8 = stack_m28; /* ldur w8, [x29, -0x1c] */
        tmp_w8 = tmp_w8 - 30; /* subs w8, w8, 0x1e; flags updated */
        stack_m28 = tmp_w8; /* stur w8, [x29, -0x1c] */
        /* branch to 0x100000930 */ /* b 0x100000930 */
        /* block 0x10000091c */
        tmp_w8 = stack_m28; /* ldur w8, [x29, -0x1c] */
        tmp_w9 = 51; /* mov w9, 0x33 */
        tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8, w8, w9 */
        stack_m28 = tmp_w8; /* stur w8, [x29, -0x1c] */
        /* branch to 0x100000930 */ /* b 0x100000930 */
        /* block 0x100000930 */
        tmp_w8 = stack_28; /* ldr w8, [sp + var_1ch] */
        tmp_x9 = stack_16; /* ldr x9, [sp + var_10h] */
        tmp_w9 = *(u32 *)(tmp_x9); /* ldr w9, [x9] */
        tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8, w8, w9 */
        tmp_w9 = stack_m28; /* ldur w9, [x29, -0x1c] */
        tmp_w0 = tmp_w8 ^ tmp_w9; /* eor w0, w8, w9 */
        tmp_x8 = stack_16; /* ldr x8, [sp + var_10h] */
        tmp_w8 = *(u8 *)(tmp_x8 + 9); /* ldrb w8, [x8, 9] */
        tmp_w1 = tmp_w8 + 1; /* add w1, w8, 1 */
        call_0x100000d4c(tmp_w0, tmp_w1); /* bl sym._rotl32; args refined from same-block evidence */
        stack_28 = tmp_w0; /* str w0, [sp + var_1ch] */
        tmp_w8 = stack_28; /* ldrb w8, [sp + var_1ch] */
        tmp_w8 = tmp_w8 - 66; /* subs w8, w8, 0x42; flags updated */
        /* conditional branch b.ne -> 0x100000970 */
        /* block 0x100000968 */
        /* branch to 0x10000096c */ /* b 0x10000096c */
        /* block 0x10000096c */
        /* branch to 0x100000980 */ /* b 0x100000980 */
        /* block 0x100000970 */
        tmp_w8 = stack_32; /* ldr w8, [sp + var_20h] */
        tmp_w8 = tmp_w8 + 1; /* add w8, w8, 1 */
        stack_32 = tmp_w8; /* str w8, [sp + var_20h] */
        /* branch to 0x1000007a0 */ /* b 0x1000007a0 */
        /* block 0x100000980 */
        tmp_w8 = stack_m28; /* ldur w8, [x29, -0x1c] */
        tmp_w9 = stack_28; /* ldr w9, [sp + var_1ch] */
        tmp_w9 = tmp_w9 & 0x7fffffff; /* and w9, w9, 0x7fffffff */
        tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8, w8, w9 */
        stack_m4 = tmp_w8; /* stur w8, [x29, -4] */
        /* branch to 0x100000998 */ /* b 0x100000998 */
        /* block 0x100000998 */
        tmp_w0 = stack_m4; /* ldur w0, [x29, -4] */
        tmp_fp = stack_64; /* ldp x29, x30, [sp + var_40h] */
        tmp_lr = stack_72; /* paired load second register inferred offset +8 */
        tmp_sp = tmp_sp + 80; /* add sp, sp, 0x50 */
        return tmp_w0; /* return value from w0 before ret */
    }
    /* unstructured region end */

}

uint64_t mixed_driver(void)
{
    /* Entry: 0x100000768 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 2 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Conservative pseudo declarations: */
    u32 tmp_w8 = 0;
    u32 stack_m4 = 0;

    /* Control flow structure: */
    /* block 0x100000768 */
    stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
    /* branch to 0x100000998 */ /* b 0x100000998 */

    /* return value unknown */
    return 0;
}

uint64_t FUN_1000007a0(void)
{
    /* Entry: 0x1000007a0 */
    /* Body status: structured */
    /* 18 basic block(s), 70 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[16, 32], sizes=[4, 8] */
    /*   base=x8, kind=record_like, offsets=[0, 4, 8, 9, 10], sizes=[1, 2, 4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u32 tmp_w2 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u64 stack_m16 = 0;
    u32 stack_m20 = 0;
    u32 stack_m28 = 0;
    u64 stack_16 = 0;
    u64 stack_32 = 0;

    /* Control flow structure: */
    /* loop kind: while_like */
    /* loop header: 0x1000007a0 */
    /* loop exits: ['0x1000007f8'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000007ac after subs at 0x1000007a8; target 0x100000980")) {
        /* block 0x1000007a0 */
        tmp_w8 = stack_32; /* ldr w8,[sp, #0x20] */
        tmp_w9 = stack_m20; /* ldur w9,[x29, #-0x14] */
        tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
        /* conditional branch b.ge -> 0x100000980 */
        /* block 0x1000007b0 */
        /* branch to 0x1000007b4 */ /* b 0x1000007b4 */
        /* block 0x1000007b4 */
        tmp_x8 = stack_m16; /* ldur x8,[x29, #-0x10] */
        tmp_x9 = (i64)(i32)stack_32; /* ldrsw x9,[sp, #0x20] */
        tmp_x10 = 12; /* mov x10,#0xc */
        tmp_x9 = tmp_x9 * tmp_x10; /* mul x9,x9,x10 */
        tmp_x8 = tmp_x8 + tmp_x9; /* add x8,x8,x9 */
        stack_16 = tmp_x8; /* str x8,[sp, #0x10] */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_w8 = *(u32 *)(tmp_x8); /* ldr w8,[x8] */
        /* cbnz tmp_w8 -> 0x1000007f8 */
        /* block 0x1000007d8 */
        /* branch to 0x1000007dc */ /* b 0x1000007dc */
        /* block 0x1000007dc */
        tmp_w8 = stack_m28; /* ldur w8,[x29, #-0x1c] */
        tmp_w8 = tmp_w8 - 3; /* subs w8,w8,#0x3; flags updated */
        stack_m28 = tmp_w8; /* stur w8,[x29, #-0x1c] */
        tmp_w8 = stack_32; /* ldr w8,[sp, #0x20] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_32 = tmp_w8; /* str w8,[sp, #0x20] */
        /* branch to 0x1000007a0 */ /* b 0x1000007a0 */
    }
    /* if/else condition block: 0x1000007f8 */
    /* merge block: 0x100000838 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: tbz w8 bit #0 at 0x100000800 targeting 0x100000820; polarity inverted")) {
        /* block 0x100000804 */
        /* branch to 0x100000808 */ /* b 0x100000808 */
        /* block 0x100000808 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_w9 = *(u32 *)(tmp_x8 + 4); /* ldr w9,[x8, #0x4] */
        tmp_w8 = stack_m28; /* ldur w8,[x29, #-0x1c] */
        tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
        stack_m28 = tmp_w8; /* stur w8,[x29, #-0x1c] */
        /* branch to 0x100000838 */ /* b 0x100000838 */
    } else {
        /* block 0x100000820 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_w9 = *(u32 *)(tmp_x8 + 4); /* ldr w9,[x8, #0x4] */
        tmp_w8 = stack_m28; /* ldur w8,[x29, #-0x1c] */
        tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
        stack_m28 = tmp_w8; /* stur w8,[x29, #-0x1c] */
        /* branch to 0x100000838 */ /* b 0x100000838 */
    }
    /* block 0x100000838 */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_w8 = *(u8 *)(tmp_x8 + 8); /* ldrb w8,[x8, #0x8] */
    /* tbz tmp_w8 bit 2 -> 0x100000874 */
    /* block 0x100000844 */
    /* branch to 0x100000848 */ /* b 0x100000848 */
    /* block 0x100000848 */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_w0 = *(u32 *)(tmp_x8 + 4); /* ldr w0,[x8, #0x4] */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_w1 = *(u8 *)(tmp_x8 + 9); /* ldrb w1,[x8, #0x9] */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_w2 = *(u8 *)(tmp_x8 + 8); /* ldrb w2,[x8, #0x8] */
    call_0x100000c54(tmp_w0, tmp_w1, tmp_w2); /* bl 0x100000c54; args refined from same-block evidence */
    /* block 0x100000864 */
    tmp_w8 = stack_m28; /* ldur w8,[x29, #-0x1c] */
    tmp_w8 = tmp_w8 + tmp_w0; /* add w8,w8,w0 */
    stack_m28 = tmp_w8; /* stur w8,[x29, #-0x1c] */
    /* branch to 0x100000874 */ /* b 0x100000874 */
    /* if/else condition block: 0x100000874 */
    /* merge block: 0x1000008b4 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: tbnz w8 bit #0 at 0x10000087c targeting 0x10000089c; polarity inverted")) {
        /* block 0x100000880 */
        /* branch to 0x100000884 */ /* b 0x100000884 */
        /* block 0x100000884 */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_w9 = *(u16 *)(tmp_x8 + 10); /* ldrh w9,[x8, #0xa] */
        tmp_w8 = stack_m28; /* ldur w8,[x29, #-0x1c] */
        tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
        stack_m28 = tmp_w8; /* stur w8,[x29, #-0x1c] */
        /* branch to 0x1000008b4 */ /* b 0x1000008b4 */
    } else {
        /* block 0x10000089c */
        tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
        tmp_w9 = *(u16 *)(tmp_x8 + 10); /* ldrh w9,[x8, #0xa] */
        tmp_w8 = stack_m28; /* ldur w8,[x29, #-0x1c] */
        tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
        stack_m28 = tmp_w8; /* stur w8,[x29, #-0x1c] */
        /* branch to 0x1000008b4 */ /* b 0x1000008b4 */
    }
    /* block 0x1000008b4 */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */

    /* return value unknown */
    return 0;
}

uint64_t cfg_pressure(void)
{
    /* Entry: 0x1000008b8 */
    /* Body status: structured */
    /* 16 basic block(s), 56 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[12, 16, 28, 32], sizes=[1, 4, 8] */
    /*   base=x8, kind=scalar, offsets=[9], sizes=[1] */
    /*   base=x9, kind=scalar, offsets=[0], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 stack_m4 = 0;
    u32 stack_m28 = 0;
    u32 stack_12 = 0;
    u64 stack_16 = 0;
    u32 stack_28 = 0;
    u32 stack_32 = 0;

    /* Control flow structure: */
    /* block 0x1000008b8 */
    tmp_w8 = *(u8 *)(tmp_x8 + 9); /* ldrb w8,[x8, #0x9] */
    tmp_w8 = tmp_w8 & 3; /* and w8,w8,#0x3 */
    stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
    /* cbz tmp_w8 -> 0x1000008ec */
    /* block 0x1000008ec */
    tmp_w8 = stack_m28; /* ldur w8,[x29, #-0x1c] */
    tmp_w8 = tmp_w8 + 10; /* add w8,w8,#0xa */
    stack_m28 = tmp_w8; /* stur w8,[x29, #-0x1c] */
    /* branch to 0x100000930 */ /* b 0x100000930 */
    /* block 0x1000008c8 */
    /* branch to 0x1000008cc */ /* b 0x1000008cc */
    /* block 0x1000008cc */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    tmp_w8 = tmp_w8 - 1; /* subs w8,w8,#0x1; flags updated */
    /* conditional branch b.eq -> 0x1000008fc */
    /* block 0x1000008fc */
    tmp_w8 = stack_m28; /* ldur w8,[x29, #-0x1c] */
    tmp_w8 = tmp_w8 + 20; /* add w8,w8,#0x14 */
    stack_m28 = tmp_w8; /* stur w8,[x29, #-0x1c] */
    /* branch to 0x100000930 */ /* b 0x100000930 */
    /* block 0x1000008d8 */
    /* branch to 0x1000008dc */ /* b 0x1000008dc */
    /* block 0x1000008dc */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    tmp_w8 = tmp_w8 - 2; /* subs w8,w8,#0x2; flags updated */
    /* conditional branch b.eq -> 0x10000090c */
    /* block 0x10000090c */
    tmp_w8 = stack_m28; /* ldur w8,[x29, #-0x1c] */
    tmp_w8 = tmp_w8 - 30; /* subs w8,w8,#0x1e; flags updated */
    stack_m28 = tmp_w8; /* stur w8,[x29, #-0x1c] */
    /* branch to 0x100000930 */ /* b 0x100000930 */
    /* block 0x1000008e8 */
    /* branch to 0x10000091c */ /* b 0x10000091c */
    /* block 0x10000091c */
    tmp_w8 = stack_m28; /* ldur w8,[x29, #-0x1c] */
    tmp_w9 = 51; /* mov w9,#0x33 */
    tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8,w8,w9 */
    stack_m28 = tmp_w8; /* stur w8,[x29, #-0x1c] */
    /* branch to 0x100000930 */ /* b 0x100000930 */
    /* block 0x100000930 */
    tmp_w8 = stack_28; /* ldr w8,[sp, #0x1c] */
    tmp_x9 = stack_16; /* ldr x9,[sp, #0x10] */
    tmp_w9 = *(u32 *)(tmp_x9); /* ldr w9,[x9] */
    tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8,w8,w9 */
    tmp_w9 = stack_m28; /* ldur w9,[x29, #-0x1c] */
    tmp_w0 = tmp_w8 ^ tmp_w9; /* eor w0,w8,w9 */
    tmp_x8 = stack_16; /* ldr x8,[sp, #0x10] */
    tmp_w8 = *(u8 *)(tmp_x8 + 9); /* ldrb w8,[x8, #0x9] */
    tmp_w1 = tmp_w8 + 1; /* add w1,w8,#0x1 */
    call_0x100000d4c(tmp_w0, tmp_w1); /* bl 0x100000d4c; args refined from same-block evidence */
    /* block 0x100000958 */
    stack_28 = tmp_w0; /* str w0,[sp, #0x1c] */
    tmp_w8 = stack_28; /* ldrb w8,[sp, #0x1c] */
    tmp_w8 = tmp_w8 - 66; /* subs w8,w8,#0x42; flags updated */
    /* conditional branch b.ne -> 0x100000970 */
    /* block 0x100000970 */
    tmp_w8 = stack_32; /* ldr w8,[sp, #0x20] */
    tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
    stack_32 = tmp_w8; /* str w8,[sp, #0x20] */
    /* branch to 0x1000007a0 */ /* b 0x1000007a0 */
    /* block 0x100000968 */
    /* branch to 0x10000096c */ /* b 0x10000096c */
    /* block 0x10000096c */
    /* branch to 0x100000980 */ /* b 0x100000980 */
    /* block 0x100000980 */
    tmp_w8 = stack_m28; /* ldur w8,[x29, #-0x1c] */
    tmp_w9 = stack_28; /* ldr w9,[sp, #0x1c] */
    tmp_w9 = tmp_w9 & 0x7fffffff; /* and w9,w9,#0x7fffffff */
    tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8,w8,w9 */
    stack_m4 = tmp_w8; /* stur w8,[x29, #-0x4] */
    /* branch to 0x100000998 */ /* b 0x100000998 */

    /* return value unknown */
    return 0;
}

uint64_t FUN_100000998(void)
{
    /* Entry: 0x100000998 */
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
    /* block 0x100000998 */
    tmp_w0 = stack_m4; /* ldur w0,[x29, #-0x4] */
    tmp_fp = stack_64; /* ldp x29,x30,[sp, #0x40] */
    tmp_lr = stack_72; /* paired load second register inferred offset +8 */
    tmp_sp = tmp_sp + 80; /* add sp,sp,#0x50 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t nested_control(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_20h)
{
    /* Entry: 0x1000009a8 */
    /* Body status: structured */
    /* 23 basic block(s), 76 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[4, 8, 12, 16, 20, 24, 28], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u32 tmp_w2 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 stack_4 = 0;
    u32 stack_8 = 0;
    u32 stack_12 = 0;
    u32 stack_16 = 0;
    u32 stack_20 = 0;
    u32 stack_24 = 0;
    u32 stack_28 = 0;

    /* Control flow structure: */
    /* block 0x1000009a8 */
    tmp_sp = tmp_sp - 32; /* sub sp,sp,#0x20 */
    stack_24 = tmp_w0; /* str w0,[sp, #0x18] */
    stack_20 = tmp_w1; /* str w1,[sp, #0x14] */
    stack_16 = tmp_w2; /* str w2,[sp, #0x10] */
    stack_12 = 0; /* str wzr,[sp, #0xc] */
    stack_8 = 0; /* str wzr,[sp, #0x8] */
    /* branch to 0x1000009c4 */ /* b 0x1000009c4 */
    /* loop kind: while_like */
    /* loop header: 0x1000009c4 */
    /* loop exits: ['0x100000a8c', '0x100000ac0'] */
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000009d0 after subs at 0x1000009cc; target 0x100000ac0; loop polarity inverted")) {
        /* block 0x1000009c4 */
        tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
        tmp_w9 = stack_24; /* ldr w9,[sp, #0x18] */
        tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
        /* conditional branch b.ge -> 0x100000ac0 */
        /* block 0x1000009d4 */
        /* branch to 0x1000009d8 */ /* b 0x1000009d8 */
        /* block 0x1000009d8 */
        tmp_w8 = stack_20; /* ldr w8,[sp, #0x14] */
        stack_4 = tmp_w8; /* str w8,[sp, #0x4] */
        /* branch to 0x1000009e4 */ /* b 0x1000009e4 */
        /* loop kind: while_like */
        /* loop header: 0x1000009e4 */
        /* loop exits: ['0x100000a8c', '0x100000aac'] */
        while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.le at 0x1000009ec after subs at 0x1000009e8; target 0x100000aac; loop polarity inverted")) {
            /* if condition block: 0x1000009e4 */
            /* merge block: 0x100000a7c */
            if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.le at 0x1000009ec after subs at 0x1000009e8; target 0x100000aac")) {
                /* if condition block: 0x100000a40 */
                /* merge block: 0x100000a7c */
                if (HEPHAESTUS_UNKNOWN_COND("condition unknown: block 0x100000a40")) {
                    /* block 0x100000a5c */
                    /* branch to 0x100000a60 */ /* b 0x100000a60 */
                    /* block 0x100000a60 */
                    tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
                    tmp_w9 = 3; /* mov w9,#0x3 */
                    tmp_w9 = tmp_w8 * tmp_w9; /* mul w9,w8,w9 */
                    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
                    tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
                    stack_12 = tmp_w8; /* str w8,[sp, #0xc] */
                    /* branch to 0x100000a7c */ /* b 0x100000a7c */
                }
            }
            /* block 0x100000a7c */
            tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
            tmp_w9 = 5000; /* mov w9,#0x1388 */
            tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
            /* conditional branch b.le -> 0x100000a9c */
            /* block 0x100000a9c */
            tmp_w8 = stack_4; /* ldr w8,[sp, #0x4] */
            tmp_w8 = tmp_w8 - 1; /* subs w8,w8,#0x1; flags updated */
            stack_4 = tmp_w8; /* str w8,[sp, #0x4] */
            /* branch to 0x1000009e4 */ /* b 0x1000009e4 */
        }
        /* block 0x100000aac */
        /* branch to 0x100000ab0 */ /* b 0x100000ab0 */
        /* block 0x100000ab0 */
        tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
        stack_8 = tmp_w8; /* str w8,[sp, #0x8] */
        /* branch to 0x1000009c4 */ /* b 0x1000009c4 */
    }
    /* block 0x100000ac0 */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    stack_28 = tmp_w8; /* str w8,[sp, #0x1c] */
    /* branch to 0x100000acc */ /* b 0x100000acc */
    /* block 0x100000a8c */
    /* branch to 0x100000a90 */ /* b 0x100000a90 */
    /* block 0x100000a90 */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    stack_28 = tmp_w8; /* str w8,[sp, #0x1c] */
    /* branch to 0x100000acc */ /* b 0x100000acc */
    /* block 0x100000acc */
    tmp_w0 = stack_28; /* ldr w0,[sp, #0x1c] */
    tmp_sp = tmp_sp + 32; /* add sp,sp,#0x20 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t pointer_walk(int32_t arg1, uint64_t arg2, uint64_t arg3, int32_t arg_30h)
{
    /* Entry: 0x100000ad8 */
    /* Body status: structured */
    /* 24 basic block(s), 95 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* ABI argument bindings: */
    /*   ? => param 0 (stack_save_restore) */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[0, 7, 8, 16, 23, 24, 32, 44], sizes=[4] */
    /*   base=x8, kind=scalar, offsets=[0], sizes=[4] */
    /*   base=x9, kind=scalar, offsets=[0], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u64 stack_8 = 0;
    u64 stack_16 = 0;
    u32 stack_44 = 0;

    /* Control flow structure: */
    /* if/else condition block: 0x100000ad8 */
    /* merge block: 0x100000c48 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbnz x8 at 0x100000aec targeting 0x100000b00; polarity inverted")) {
        /* block 0x100000af0 */
        /* branch to 0x100000af4 */ /* b 0x100000af4 */
        /* block 0x100000af4 */
        arg0 = -1; /* mov w8, -1 */
        stack_44 = arg0; /* str w8, [sp + var_2ch] */
        /* branch to 0x100000c48 */ /* b 0x100000c48 */
    } else {
        /* block 0x100000b00 */
        stack_16 = 0; /* str wzr, [sp + var_10h] */
        stack_8 = 0; /* str xzr, [sp + var_8h] */
        /* branch to 0x100000b0c */ /* b 0x100000b0c */
        /* loop kind: while_like */
        /* loop header: 0x100000b0c */
        /* loop exits: ['0x100000c3c'] */
        while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.hs at 0x100000b18 after subs at 0x100000b14; target 0x100000c3c; loop polarity inverted")) {
            /* if condition block: 0x100000b0c */
            /* merge block: 0x100000c2c */
            if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.hs at 0x100000b18 after subs at 0x100000b14; target 0x100000c3c")) {
                /* if condition block: 0x100000ba4 */
                /* merge block: 0x100000c28 */
                if (HEPHAESTUS_UNKNOWN_COND("condition unknown: block 0x100000ba4")) {
                    /* block 0x100000c14 */
                    /* branch to 0x100000c18 */ /* b 0x100000c18 */
                    /* block 0x100000c18 */
                    arg0 = stack_16; /* ldr w8, [sp + var_10h] */
                    arg0 = arg0 + 9; /* add w8, w8, 9 */
                    stack_16 = arg0; /* str w8, [sp + var_10h] */
                    /* branch to 0x100000c28 */ /* b 0x100000c28 */
                }
                /* block 0x100000c28 */
                /* branch to 0x100000c2c */ /* b 0x100000c2c */
            }
            /* block 0x100000c2c */
            arg0 = stack_8; /* ldr x8, [sp + var_8h] */
            arg0 = arg0 + 1; /* add x8, x8, 1 */
            stack_8 = arg0; /* str x8, [sp + var_8h] */
            /* branch to 0x100000b0c */ /* b 0x100000b0c */
        }
        /* block 0x100000c3c */
        arg0 = stack_16; /* ldr w8, [sp + var_10h] */
        stack_44 = arg0; /* str w8, [sp + var_2ch] */
        /* branch to 0x100000c48 */ /* b 0x100000c48 */
    }
    /* block 0x100000c48 */
    tmp_w0 = stack_44; /* ldr w0, [sp + var_2ch] */
    tmp_sp = tmp_sp + 48; /* add sp, sp, 0x30 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t indirect_pressure(void)
{
    /* Entry: 0x100000b7c */
    /* Body status: unstructured */
    /* 10 basic block(s), 51 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[0, 8, 16, 24, 32, 44], sizes=[4, 8] */

    /* Conservative pseudo declarations: */
    u64 tmp_x8 = 0;
    u64 tmp_x9 = 0;
    u64 tmp_x10 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 stack_0 = 0;
    u64 stack_8 = 0;
    u32 stack_16 = 0;
    u64 stack_24 = 0;
    u64 stack_32 = 0;
    u32 stack_44 = 0;

    /* Control flow structure: */
    /* unstructured region begin */
    /* reason: fragmented_loop_body */
    {
        /* block 0x100000b7c */
        /* branch to 0x100000b80 */ /* b 0x100000b80 */
        /* block 0x100000b80 */
        tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
        tmp_w8 = tmp_w8 - 1; /* subs w8,w8,#0x1; flags updated */
        stack_16 = tmp_w8; /* str w8,[sp, #0x10] */
        /* branch to 0x100000b90 */ /* b 0x100000b90 */
        /* block 0x100000b90 */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 + 3; /* add x8,x8,#0x3 */
        tmp_x9 = stack_24; /* ldr x9,[sp, #0x18] */
        tmp_x8 = tmp_x8 - tmp_x9; /* subs x8,x8,x9; flags updated */
        /* conditional branch b.cs -> 0x100000c2c */
        /* block 0x100000ba4 */
        /* branch to 0x100000ba8 */ /* b 0x100000ba8 */
        /* block 0x100000ba8 */
        tmp_x8 = stack_32; /* ldr x8,[sp, #0x20] */
        tmp_x9 = stack_8; /* ldr x9,[sp, #0x8] */
        tmp_w9 = *(u8 *)(tmp_x8 + tmp_x9); /* ldrb w9,[x8, x9, LSL ] */
        tmp_x8 = stack_32; /* ldr x8,[sp, #0x20] */
        tmp_x10 = stack_8; /* ldr x10,[sp, #0x8] */
        tmp_x10 = tmp_x10 + 1; /* add x10,x10,#0x1 */
        tmp_w8 = *(u8 *)(tmp_x8 + tmp_x10); /* ldrb w8,[x8, x10, LSL ] */
        tmp_w8 = tmp_w8 << 16; /* lsl w8,w8,#0x10 */
        tmp_w8 = tmp_w8 | (tmp_w9 << 24); /* orr w8,w8,w9, LSL #0x18 */
        tmp_x9 = stack_32; /* ldr x9,[sp, #0x20] */
        tmp_x10 = stack_8; /* ldr x10,[sp, #0x8] */
        tmp_x10 = tmp_x10 + 2; /* add x10,x10,#0x2 */
        tmp_w9 = *(u8 *)(tmp_x9 + tmp_x10); /* ldrb w9,[x9, x10, LSL ] */
        tmp_w8 = tmp_w8 | (tmp_w9 << 8); /* orr w8,w8,w9, LSL #0x8 */
        tmp_x9 = stack_32; /* ldr x9,[sp, #0x20] */
        tmp_x10 = stack_8; /* ldr x10,[sp, #0x8] */
        tmp_x10 = tmp_x10 + 3; /* add x10,x10,#0x3 */
        tmp_w9 = *(u8 *)(tmp_x9 + tmp_x10); /* ldrb w9,[x9, x10, LSL ] */
        tmp_w8 = tmp_w8 | tmp_w9; /* orr w8,w8,w9 */
        stack_0 = tmp_w8; /* str w8,[sp] */
        tmp_w8 = stack_0; /* ldr w8,[sp] */
        tmp_w9 = 42405; /* mov w9,#0xa5a5 */
        /* 0x100000c00: unsupported instruction: movk w9,#0xa5a5, LSL #16 */
        tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8,w8,w9 */
        tmp_w9 = 0x1000000; /* mov w9,#0x1000000 */
        tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
        /* conditional branch b.cs -> 0x100000c28 */
        /* block 0x100000c14 */
        /* branch to 0x100000c18 */ /* b 0x100000c18 */
        /* block 0x100000c18 */
        tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
        tmp_w8 = tmp_w8 + 9; /* add w8,w8,#0x9 */
        stack_16 = tmp_w8; /* str w8,[sp, #0x10] */
        /* branch to 0x100000c28 */ /* b 0x100000c28 */
        /* block 0x100000c28 */
        /* branch to 0x100000c2c */ /* b 0x100000c2c */
        /* block 0x100000c2c */
        tmp_x8 = stack_8; /* ldr x8,[sp, #0x8] */
        tmp_x8 = tmp_x8 + 1; /* add x8,x8,#0x1 */
        stack_8 = tmp_x8; /* str x8,[sp, #0x8] */
        /* branch to 0x100000b0c */ /* b 0x100000b0c */
        /* block 0x100000c3c */
        tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
        stack_44 = tmp_w8; /* str w8,[sp, #0x2c] */
        /* branch to 0x100000c48 */ /* b 0x100000c48 */
    }
    /* unstructured region end */

    /* return value unknown */
    return 0;
}

uint64_t FUN_100000c48(void)
{
    /* Entry: 0x100000c48 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 3 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=scalar, offsets=[44], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u32 stack_44 = 0;

    /* Control flow structure: */
    /* block 0x100000c48 */
    tmp_w0 = stack_44; /* ldr w0,[sp, #0x2c] */
    tmp_sp = tmp_sp + 48; /* add sp,sp,#0x30 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t mix_score(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_10h)
{
    /* Entry: 0x100000c54 */
    /* Body status: structured */
    /* 19 basic block(s), 62 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[0, 4, 8, 12], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 stack_0 = 0;
    u32 stack_4 = 0;
    u32 stack_8 = 0;
    u32 stack_12 = 0;

    /* Control flow structure: */
    /* if/else condition block: 0x100000c54 */
    /* merge block: 0x100000ca0 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbnz w8 at 0x100000c6c targeting 0x100000c84; polarity inverted")) {
        /* block 0x100000c70 */
        /* branch to 0x100000c74 */ /* b 0x100000c74 */
        /* block 0x100000c74 */
        tmp_w8 = stack_0; /* ldr w8, [sp] */
        tmp_w8 = tmp_w8 + 11; /* add w8, w8, 0xb */
        stack_0 = tmp_w8; /* str w8, [sp] */
        /* branch to 0x100000ca0 */ /* b 0x100000ca0 */
    } else {
        /* block 0x100000c84 */
        tmp_w8 = stack_12; /* ldr w8, [sp + var_ch] */
        tmp_w9 = 3; /* mov w9, 3 */
        tmp_w9 = tmp_w8 * tmp_w9; /* mul w9, w8, w9 */
        tmp_w8 = stack_0; /* ldr w8, [sp] */
        tmp_w8 = tmp_w8 + tmp_w9; /* add w8, w8, w9 */
        stack_0 = tmp_w8; /* str w8, [sp] */
        /* branch to 0x100000ca0 */ /* b 0x100000ca0 */
    }
    /* block 0x100000ca0 */
    tmp_w8 = stack_8; /* ldr w8, [sp + var_8h] */
    /* cbz tmp_w8 -> 0x100000cc0 */
    /* block 0x100000cc0 */
    tmp_w8 = stack_0; /* ldr w8, [sp] */
    tmp_w8 = tmp_w8 + 7; /* add w8, w8, 7 */
    stack_0 = tmp_w8; /* str w8, [sp] */
    /* branch to 0x100000cd0 */ /* b 0x100000cd0 */
    /* block 0x100000ca8 */
    /* branch to 0x100000cac */ /* b 0x100000cac */
    /* block 0x100000cac */
    tmp_w9 = stack_8; /* ldr w9, [sp + var_8h] */
    tmp_w8 = stack_0; /* ldr w8, [sp] */
    tmp_w8 = tmp_w8 - tmp_w9; /* subs w8, w8, w9, lsl 1; flags updated */
    stack_0 = tmp_w8; /* str w8, [sp] */
    /* branch to 0x100000cd0 */ /* b 0x100000cd0 */
    /* if condition block: 0x100000cd0 */
    /* merge block: 0x100000cf0 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: tbz w8 bit 3 at 0x100000cd4 targeting 0x100000cf0")) {
        /* block 0x100000cd8 */
        /* branch to 0x100000cdc */ /* b 0x100000cdc */
        /* block 0x100000cdc */
        tmp_w8 = stack_0; /* ldr w8, [sp] */
        tmp_w9 = 85; /* mov w9, 0x55 */
        tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8, w8, w9 */
        stack_0 = tmp_w8; /* str w8, [sp] */
        /* branch to 0x100000cf0 */ /* b 0x100000cf0 */
    }
    /* block 0x100000cf0 */
    tmp_w8 = stack_4; /* ldr w8, [sp + var_4h] */
    /* tbnz tmp_w8 bit 7 -> 0x100000d0c */
    /* block 0x100000cf8 */
    /* branch to 0x100000cfc */ /* b 0x100000cfc */
    /* block 0x100000cfc */
    tmp_w8 = stack_0; /* ldr w8, [sp] */
    tmp_w8 = tmp_w8 + 19; /* add w8, w8, 0x13 */
    stack_0 = tmp_w8; /* str w8, [sp] */
    /* branch to 0x100000d0c */ /* b 0x100000d0c */
    /* if/else condition block: 0x100000d0c */
    /* merge block: 0x100000d40 */
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.hs at 0x100000d18 after subs at 0x100000d14; target 0x100000d30; polarity inverted")) {
        /* block 0x100000d1c */
        /* branch to 0x100000d20 */ /* b 0x100000d20 */
        /* block 0x100000d20 */
        tmp_w8 = stack_0; /* ldr w8, [sp] */
        tmp_w8 = tmp_w8 + 5; /* add w8, w8, 5 */
        stack_0 = tmp_w8; /* str w8, [sp] */
        /* branch to 0x100000d40 */ /* b 0x100000d40 */
    } else {
        /* block 0x100000d30 */
        tmp_w8 = stack_0; /* ldr w8, [sp] */
        tmp_w8 = tmp_w8 - 5; /* subs w8, w8, 5; flags updated */
        stack_0 = tmp_w8; /* str w8, [sp] */
        /* branch to 0x100000d40 */ /* b 0x100000d40 */
    }
    /* block 0x100000d40 */
    tmp_w0 = stack_0; /* ldr w0, [sp] */
    tmp_sp = tmp_sp + 16; /* add sp, sp, 0x10 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t byte_halfword_pressure(void)
{
    /* Entry: 0x100000d00 */
    /* Body status: structured */
    /* 6 basic block(s), 19 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[0, 4, 12], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 stack_0 = 0;
    u32 stack_4 = 0;
    u32 stack_12 = 0;

    /* Control flow structure: */
    /* block 0x100000d00 */
    tmp_w8 = tmp_w8 + 19; /* add w8,w8,#0x13 */
    stack_0 = tmp_w8; /* str w8,[sp] */
    /* branch to 0x100000d0c */ /* b 0x100000d0c */
    /* block 0x100000d0c */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    tmp_w9 = stack_4; /* ldr w9,[sp, #0x4] */
    tmp_w8 = tmp_w8 - tmp_w9; /* subs w8,w8,w9; flags updated */
    /* conditional branch b.cs -> 0x100000d30 */
    /* block 0x100000d30 */
    tmp_w8 = stack_0; /* ldr w8,[sp] */
    tmp_w8 = tmp_w8 - 5; /* subs w8,w8,#0x5; flags updated */
    stack_0 = tmp_w8; /* str w8,[sp] */
    /* branch to 0x100000d40 */ /* b 0x100000d40 */
    /* block 0x100000d1c */
    /* branch to 0x100000d20 */ /* b 0x100000d20 */
    /* block 0x100000d20 */
    tmp_w8 = stack_0; /* ldr w8,[sp] */
    tmp_w8 = tmp_w8 + 5; /* add w8,w8,#0x5 */
    stack_0 = tmp_w8; /* str w8,[sp] */
    /* branch to 0x100000d40 */ /* b 0x100000d40 */
    /* block 0x100000d40 */
    tmp_w0 = stack_0; /* ldr w0,[sp] */
    tmp_sp = tmp_sp + 16; /* add sp,sp,#0x10 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t rotl32(int32_t arg1, uint64_t arg2, uint64_t arg_10h)
{
    /* Entry: 0x100000d4c */
    /* Body status: partially_structured */
    /* 1 basic block(s), 18 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 12], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    u32 tmp_w0 = 0;
    u32 tmp_w1 = 0;
    u32 tmp_w8 = 0;
    u32 tmp_w9 = 0;
    u32 tmp_w10 = 0;
    u32 tmp_w11 = 0;
    u32 stack_8 = 0;
    u32 stack_12 = 0;

    /* Control flow structure: */
    /* block 0x100000d4c */
    tmp_sp = tmp_sp - 16; /* sub sp,sp,#0x10 */
    stack_12 = tmp_w0; /* str w0,[sp, #0xc] */
    stack_8 = tmp_w1; /* str w1,[sp, #0x8] */
    tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
    tmp_w8 = tmp_w8 & 31; /* and w8,w8,#0x1f */
    stack_8 = tmp_w8; /* str w8,[sp, #0x8] */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    tmp_w9 = stack_8; /* ldr w9,[sp, #0x8] */
    tmp_w8 = tmp_w8 << tmp_w9; /* lsl w8,w8,w9 */
    tmp_w9 = stack_12; /* ldr w9,[sp, #0xc] */
    tmp_w11 = stack_8; /* ldr w11,[sp, #0x8] */
    tmp_w10 = 32; /* mov w10,#0x20 */
    tmp_w10 = tmp_w10 - tmp_w11; /* subs w10,w10,w11; flags updated */
    tmp_w10 = tmp_w10 & 31; /* and w10,w10,#0x1f */
    tmp_w9 = tmp_w9 >> tmp_w10; /* lsr w9,w9,w10 */
    tmp_w0 = tmp_w8 | tmp_w9; /* orr w0,w8,w9 */
    tmp_sp = tmp_sp + 16; /* add sp,sp,#0x10 */
    return tmp_w0; /* return value from w0 before ret */

}

uint64_t stack_chk_fail(void)
{
    /* Entry: 0x100000d94 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 3 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[0], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x16 = 0;

    /* Control flow structure: */
    /* block 0x100000d94 */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.__stack_chk_fail */
    tmp_x16 = *(u64 *)(tmp_x16); /* ldr x16, [x16] */
    /* branch to tmp_x16 */ /* br x16 */

    /* return value unknown */
    return 0;
}

int32_t printf(void * format)
{
    /* Entry: 0x100000da0 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 3 instruction(s) */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[16], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x16 = 0;

    /* Control flow structure: */
    /* block 0x100000da0 */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.__stack_chk_fail */
    tmp_x16 = *(u64 *)(tmp_x16 + 16); /* ldr x16, [x16, 0x10] */
    /* branch to tmp_x16 */ /* br x16 */

    /* return value unknown */
    return 0;
}

int32_t puts(void * s)
{
    /* Entry: 0x100000dac */
    /* Body status: partially_structured */
    /* 1 basic block(s), 3 instruction(s) */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[24], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x16 = 0;

    /* Control flow structure: */
    /* block 0x100000dac */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.__stack_chk_fail */
    tmp_x16 = *(u64 *)(tmp_x16 + 24); /* ldr x16, [x16, 0x18] */
    /* branch to tmp_x16 */ /* br x16 */

    /* return value unknown */
    return 0;
}

uint64_t strlen(void * s)
{
    /* Entry: 0x100000db8 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 5 instruction(s) */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[32], sizes=[4] */

    /* Conservative pseudo declarations: */
    u64 tmp_x16 = 0;

    /* Control flow structure: */
    /* block 0x100000db8 */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.__stack_chk_fail */
    tmp_x16 = *(u64 *)(tmp_x16 + 32); /* ldr x16, [x16, 0x20] */
    /* branch to tmp_x16 */ /* br x16 */
    /* 0x100000dc4: unsupported instruction: sqshlu v26.2d, v11.2d, 0x32 */
    /* 0x100000dc8: unsupported instruction: invalid */

    /* return value unknown */
    return 0;
}

