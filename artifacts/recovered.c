/*
 * recovered.c — Phase 5.1 Source Reconstruction Skeleton
 * Schema version: 5.2.0
 * Generated: 2026-06-15T19:01:44Z
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

/* ================================================== */
/*                 Forward Declarations                */
/* ================================================== */

int32_t main(int32_t argc, void * argv);
uint64_t reduce_array(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_40h);
uint64_t op_add(int32_t arg1, uint64_t arg2, uint64_t arg_10h);
uint64_t op_xor(int32_t arg1, uint64_t arg2, uint64_t arg_10h);
uint64_t weird_loop(uint64_t arg1, uint64_t arg_10h);
uint64_t stack_chk_fail(void);
int32_t printf(void * format);

/* ================================================== */
/*                 Function Definitions                */
/* ================================================== */

int32_t main(int32_t argc, void * argv)
{
    /* Entry: 0x100000460 */
    /* Body status: structured */
    /* 13 basic block(s), 73 instruction(s) */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[36, 40, 48, 52, 56], sizes=[4, 8] */
    /*   base=x8, kind=array_like, offsets=[0, 8], sizes=[8] */
    /*   base=x9, kind=array_like, offsets=[0, 8, 16], sizes=[8] */

    /* Control flow structure: */
    /* sequence begin */
        /* sequence begin */
            /* block 0x100000460 */
            tmp_sp = tmp_sp - 128; /* sub sp,sp,#0x80 */
            stack_112 = tmp_x29; /* stp x29,x30,[sp, #0x70] */
            stack_120 = tmp_x30; /* paired store second register inferred offset +8 */
            tmp_x29 = tmp_sp + 112; /* add x29,sp,#0x70 */
            tmp_x8 = 0x100004000; /* adrp x8,0x100004000 */
            tmp_x8 = *(u64 *)(tmp_x8 + 8); /* ldr x8,[x8, #0x8] */
            tmp_x8 = *(u64 *)(tmp_x8); /* ldr x8,[x8] */
            stack_m8 = tmp_x8; /* stur x8,[x29, #-0x8] */
            stack_m44 = 0; /* stur wzr,[x29, #-0x2c] */
            stack_m48 = 0; /* stur wzr,[x29, #-0x30] */
            /* branch to 0x100000488 */ /* b 0x100000488 */
            /* loop (while_like) header=0x100000488 exits=['0x1000004c8'] */
                /* sequence begin */
                    /* block 0x100000488 */
                    tmp_w8 = stack_m48; /* ldur w8,[x29, #-0x30] */
                    /* 0x10000048c: unsupported instruction: subs w8,w8,#0x8 */
                    /* 0x100000490: unsupported instruction: b.ge 0x1000004c8 */
                    /* sequence begin */
                        /* block 0x100000494 */
                        /* branch to 0x100000498 */ /* b 0x100000498 */
                        /* block 0x100000498 */
                        tmp_w8 = stack_m48; /* ldur w8,[x29, #-0x30] */
                        tmp_w9 = 7; /* mov w9,#0x7 */
                        tmp_w8 = tmp_w8 * tmp_w9; /* mul w8,w8,w9 */
                        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
                        tmp_x10 = (i64)(i32)stack_m48; /* ldursw x10,[x29, #-0x30] */
                        tmp_x9 = tmp_x29 - 40; /* sub x9,x29,#0x28 */
                        *(u32 *)(tmp_x9 + (tmp_x10 << 2)) = tmp_w8; /* str w8,[x9, x10, LSL #0x2] */
                        /* branch to 0x1000004b8 */ /* b 0x1000004b8 */
                        /* block 0x1000004b8 */
                        tmp_w8 = stack_m48; /* ldur w8,[x29, #-0x30] */
                        tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
                        stack_m48 = tmp_w8; /* stur w8,[x29, #-0x30] */
                        /* branch to 0x100000488 */ /* b 0x100000488 */
                    /* sequence end */
                /* sequence end */
            /* sequence begin */
                /* block 0x1000004c8 */
                tmp_x0 = tmp_x29 - 40; /* sub x0,x29,#0x28 */
                stack_40 = tmp_x0; /* str x0,[sp, #0x28] */
                tmp_w1 = 8; /* mov w1,#0x8 */
                stack_36 = tmp_w1; /* str w1,[sp, #0x24] */
                tmp_x2 = 0x100000000; /* adrp x2,0x100000000 */
                tmp_x2 = tmp_x2 + 1584; /* add x2,x2,#0x630 */
                call_0x100000584(tmp_x0, tmp_x1, tmp_x2, tmp_x3); /* bl 0x100000584 */
                /* block 0x1000004e4 */
                tmp_w1 = stack_36; /* ldr w1,[sp, #0x24] */
                tmp_x8 = tmp_x0; /* mov x8,x0 */
                tmp_x0 = stack_40; /* ldr x0,[sp, #0x28] */
                stack_m52 = tmp_w8; /* stur w8,[x29, #-0x34] */
                tmp_x2 = 0x100000000; /* adrp x2,0x100000000 */
                tmp_x2 = tmp_x2 + 1616; /* add x2,x2,#0x650 */
                call_0x100000584(tmp_x0, tmp_x1, tmp_x2, tmp_x3); /* bl 0x100000584 */
                /* block 0x100000500 */
                stack_56 = tmp_w0; /* str w0,[sp, #0x38] */
                tmp_w8 = stack_m52; /* ldur w8,[x29, #-0x34] */
                tmp_w9 = stack_56; /* ldr w9,[sp, #0x38] */
                tmp_w0 = tmp_w8 ^ tmp_w9; /* eor w0,w8,w9 */
                call_0x100000670(tmp_x0, tmp_x1); /* bl 0x100000670 */
                /* block 0x100000514 */
                stack_52 = tmp_w0; /* str w0,[sp, #0x34] */
                tmp_w8 = stack_m52; /* ldur w8,[x29, #-0x34] */
                tmp_x11 = tmp_x8; /* mov x11,x8 */
                tmp_w8 = stack_56; /* ldr w8,[sp, #0x38] */
                tmp_x10 = tmp_x8; /* mov x10,x8 */
                tmp_w8 = stack_52; /* ldr w8,[sp, #0x34] */
                tmp_x9 = tmp_sp; /* mov x9,sp */
                *(u64 *)(tmp_x9) = tmp_x11; /* str x11,[x9] */
                *(u64 *)(tmp_x9 + 8) = tmp_x10; /* str x10,[x9, #0x8] */
                *(u64 *)(tmp_x9 + 16) = tmp_x8; /* str x8,[x9, #0x10] */
                tmp_x0 = 0x100000000; /* adrp x0,0x100000000 */
                tmp_x0 = tmp_x0 + 1840; /* add x0,x0,#0x730 */
                call_0x100000724(tmp_x0); /* bl 0x100000724 */
                /* block 0x100000548 */
                tmp_w8 = stack_52; /* ldr w8,[sp, #0x34] */
                tmp_w8 = tmp_w8 & 31; /* and w8,w8,#0x1f */
                stack_48 = tmp_w8; /* str w8,[sp, #0x30] */
                tmp_x9 = stack_m8; /* ldur x9,[x29, #-0x8] */
                tmp_x8 = 0x100004000; /* adrp x8,0x100004000 */
                tmp_x8 = *(u64 *)(tmp_x8 + 8); /* ldr x8,[x8, #0x8] */
                tmp_x8 = *(u64 *)(tmp_x8); /* ldr x8,[x8] */
                /* 0x100000564: unsupported instruction: subs x8,x8,x9 */
                /* 0x100000568: unsupported instruction: b.eq 0x100000574 */
            /* sequence end */
        /* sequence end */
        /* block 0x100000574 */
        tmp_w0 = stack_48; /* ldr w0,[sp, #0x30] */
        tmp_x29 = stack_112; /* ldp x29,x30,[sp, #0x70] */
        tmp_x30 = stack_120; /* paired load second register inferred offset +8 */
        tmp_sp = tmp_sp + 128; /* add sp,sp,#0x80 */
        /* return via x0 */ /* ret */
        /* sequence begin */
            /* block 0x10000056c */
            /* branch to 0x100000570 */ /* b 0x100000570 */
            /* block 0x100000570 */
            call_0x100000718(); /* bl 0x100000718 */
        /* sequence end */
    /* sequence end */

    return 0; /* placeholder */
}

uint64_t reduce_array(uint64_t arg1, uint64_t arg2, uint64_t arg3, uint64_t arg_40h)
{
    /* Entry: 0x100000584 */
    /* Body status: structured */
    /* 11 basic block(s), 43 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=record_like, offsets=[12, 16, 20, 24], sizes=[4, 8] */

    /* Control flow structure: */
    /* sequence begin */
        /* block 0x100000584 */
        tmp_sp = tmp_sp - 64; /* sub sp,sp,#0x40 */
        stack_48 = tmp_x29; /* stp x29,x30,[sp, #0x30] */
        stack_56 = tmp_x30; /* paired store second register inferred offset +8 */
        tmp_x29 = tmp_sp + 48; /* add x29,sp,#0x30 */
        stack_m8 = tmp_x0; /* stur x0,[x29, #-0x8] */
        stack_m12 = tmp_w1; /* stur w1,[x29, #-0xc] */
        stack_24 = tmp_x2; /* str x2,[sp, #0x18] */
        stack_20 = 0; /* str wzr,[sp, #0x14] */
        stack_16 = 0; /* str wzr,[sp, #0x10] */
        /* branch to 0x1000005a8 */ /* b 0x1000005a8 */
        /* loop (while_like) header=0x1000005a8 exits=['0x100000620'] */
            /* sequence begin */
                /* if-else (condition at block 0x1000005a8) merge=0x10000060c */
                /* then: */
                    /* sequence begin */
                        /* block 0x1000005d4 */
                        /* branch to 0x1000005d8 */ /* b 0x1000005d8 */
                        /* block 0x1000005d8 */
                        tmp_x8 = stack_24; /* ldr x8,[sp, #0x18] */
                        tmp_w0 = stack_20; /* ldr w0,[sp, #0x14] */
                        tmp_w1 = stack_12; /* ldr w1,[sp, #0xc] */
                        /* indirect call via tmp_x8 */ /* blr x8 */
                        /* block 0x1000005e8 */
                        stack_20 = tmp_w0; /* str w0,[sp, #0x14] */
                        /* branch to 0x10000060c */ /* b 0x10000060c */
                    /* sequence end */
                /* else: */
                    /* block 0x1000005f0 */
                    tmp_w8 = stack_20; /* ldr w8,[sp, #0x14] */
                    tmp_w9 = stack_12; /* ldr w9,[sp, #0xc] */
                    tmp_w10 = 3; /* mov w10,#0x3 */
                    tmp_w9 = tmp_w9 * tmp_w10; /* mul w9,w9,w10 */
                    tmp_w8 = tmp_w8 + tmp_w9; /* add w8,w8,w9 */
                    stack_20 = tmp_w8; /* str w8,[sp, #0x14] */
                    /* branch to 0x10000060c */ /* b 0x10000060c */
                /* sequence begin */
                    /* block 0x10000060c */
                    /* branch to 0x100000610 */ /* b 0x100000610 */
                    /* block 0x100000610 */
                    tmp_w8 = stack_16; /* ldr w8,[sp, #0x10] */
                    tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
                    stack_16 = tmp_w8; /* str w8,[sp, #0x10] */
                    /* branch to 0x1000005a8 */ /* b 0x1000005a8 */
                /* sequence end */
            /* sequence end */
        /* block 0x100000620 */
        tmp_w0 = stack_20; /* ldr w0,[sp, #0x14] */
        tmp_x29 = stack_48; /* ldp x29,x30,[sp, #0x30] */
        tmp_x30 = stack_56; /* paired load second register inferred offset +8 */
        tmp_sp = tmp_sp + 64; /* add sp,sp,#0x40 */
        /* return via x0 */ /* ret */
    /* sequence end */

    return 0; /* placeholder */
}

uint64_t op_add(int32_t arg1, uint64_t arg2, uint64_t arg_10h)
{
    /* Entry: 0x100000630 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 8 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 12], sizes=[4] */

    /* Control flow structure: */
    /* block 0x100000630 */
    tmp_sp = tmp_sp - 16; /* sub sp,sp,#0x10 */
    stack_12 = tmp_w0; /* str w0,[sp, #0xc] */
    stack_8 = tmp_w1; /* str w1,[sp, #0x8] */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    tmp_w9 = stack_8; /* ldr w9,[sp, #0x8] */
    tmp_w0 = tmp_w8 + tmp_w9; /* add w0,w8,w9 */
    tmp_sp = tmp_sp + 16; /* add sp,sp,#0x10 */
    /* return via x0 */ /* ret */

    return 0; /* placeholder */
}

uint64_t op_xor(int32_t arg1, uint64_t arg2, uint64_t arg_10h)
{
    /* Entry: 0x100000650 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 8 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[8, 12], sizes=[4] */

    /* Control flow structure: */
    /* block 0x100000650 */
    tmp_sp = tmp_sp - 16; /* sub sp,sp,#0x10 */
    stack_12 = tmp_w0; /* str w0,[sp, #0xc] */
    stack_8 = tmp_w1; /* str w1,[sp, #0x8] */
    tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
    tmp_w9 = stack_8; /* ldr w9,[sp, #0x8] */
    tmp_w0 = tmp_w8 ^ tmp_w9; /* eor w0,w8,w9 */
    tmp_sp = tmp_sp + 16; /* add sp,sp,#0x10 */
    /* return via x0 */ /* ret */

    return 0; /* placeholder */
}

uint64_t weird_loop(uint64_t arg1, uint64_t arg_10h)
{
    /* Entry: 0x100000670 */
    /* Body status: structured */
    /* 12 basic block(s), 42 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=sp, kind=array_like, offsets=[4, 8, 12], sizes=[4] */

    /* Control flow structure: */
    /* sequence begin */
        /* sequence begin */
            /* block 0x100000670 */
            tmp_sp = tmp_sp - 16; /* sub sp,sp,#0x10 */
            stack_12 = tmp_w0; /* str w0,[sp, #0xc] */
            tmp_w8 = stack_12; /* ldr w8,[sp, #0xc] */
            stack_8 = tmp_w8; /* str w8,[sp, #0x8] */
            stack_4 = 0; /* str wzr,[sp, #0x4] */
            /* branch to 0x100000688 */ /* b 0x100000688 */
            /* loop (while_like) header=0x100000688 exits=['0x1000006e0', '0x10000070c'] */
                /* sequence begin */
                    /* if-else (condition at block 0x100000688) merge=0x1000006fc */
                    /* then: */
                        /* sequence begin */
                            /* block 0x1000006c8 */
                            /* branch to 0x1000006cc */ /* b 0x1000006cc */
                            /* block 0x1000006cc */
                            /* branch to 0x1000006fc */ /* b 0x1000006fc */
                        /* sequence end */
                    /* else: */
                        /* sequence begin */
                            /* block 0x1000006d0 */
                            tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
                            tmp_w8 = tmp_w8 & 15; /* and w8,w8,#0xf */
                            /* 0x1000006d8: unsupported instruction: subs w8,w8,#0x9 */
                            /* 0x1000006dc: unsupported instruction: b.ne 0x1000006e8 */
                            /* block 0x1000006e8 */
                            tmp_w9 = stack_4; /* ldr w9,[sp, #0x4] */
                            tmp_w8 = stack_8; /* ldr w8,[sp, #0x8] */
                            tmp_w8 = tmp_w8 ^ tmp_w9; /* eor w8,w8,w9 */
                            stack_8 = tmp_w8; /* str w8,[sp, #0x8] */
                            /* branch to 0x1000006fc */ /* b 0x1000006fc */
                        /* sequence end */
                    /* block 0x1000006fc */
                    tmp_w8 = stack_4; /* ldr w8,[sp, #0x4] */
                    tmp_w8 = tmp_w8 + 1; /* add w8,w8,#0x1 */
                    stack_4 = tmp_w8; /* str w8,[sp, #0x4] */
                    /* branch to 0x100000688 */ /* b 0x100000688 */
                /* sequence end */
        /* sequence end */
        /* sequence begin */
            /* block 0x1000006e0 */
            /* branch to 0x1000006e4 */ /* b 0x1000006e4 */
            /* block 0x1000006e4 */
            /* branch to 0x10000070c */ /* b 0x10000070c */
        /* sequence end */
        /* block 0x10000070c */
        tmp_w0 = stack_8; /* ldr w0,[sp, #0x8] */
        tmp_sp = tmp_sp + 16; /* add sp,sp,#0x10 */
        /* return via x0 */ /* ret */
    /* sequence end */

    return 0; /* placeholder */
}

uint64_t stack_chk_fail(void)
{
    /* Entry: 0x100000718 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 3 instruction(s) */
    /* WARNING: unknown_return_type_defaulted_to_u64 */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[0], sizes=[4] */

    /* Control flow structure: */
    /* block 0x100000718 */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.__stack_chk_fail */
    tmp_x16 = *(u64 *)(tmp_x16); /* ldr x16, [x16] */
    /* branch to tmp_x16 */ /* br x16 */

    return 0; /* placeholder */
}

int32_t printf(void * format)
{
    /* Entry: 0x100000724 */
    /* Body status: partially_structured */
    /* 1 basic block(s), 4 instruction(s) */

    /* Layout candidates: */
    /*   base=x16, kind=scalar, offsets=[16], sizes=[4] */

    /* Control flow structure: */
    /* block 0x100000724 */
    tmp_x16 = 0x100004000; /* adrp x16, reloc.__stack_chk_fail */
    tmp_x16 = *(u64 *)(tmp_x16 + 16); /* ldr x16, [x16, 0x10] */
    /* branch to tmp_x16 */ /* br x16 */
    /* 0x100000730: unsupported instruction: invalid */

    return 0; /* placeholder */
}

