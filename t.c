/*
 * hephaestus_param_layout_1k.c
 *
 * Around 1000 lines. Designed specifically to trigger Phase 4B.2
 * parameter_layout_evidence.
 *
 * Key patterns:
 *   - function parameters are pointers to struct-like records
 *   - parameter pointer x0/x1 is saved to stack
 *   - later restored into x8/x9
 *   - x8/x9 used as memory bases with repeated offsets
 *   - layout recovery should produce record_like candidates
 *   - 4B.2 should link those candidates back to arg0/arg1
 *
 * Build:
 *   clang -O0 -g hephaestus_param_layout_1k.c -o hephaestus_param_layout_1k
 */
#include <stdio.h>
#include <stdint.h>

#define ITEM_VALUES 12
#define NODE_HISTORY 16
#define DEVICE_REGS 16
#define TABLE_COUNT 32
#define ROUND_COUNT 24

typedef struct {
    int id;
    long score;
    char flag;
    int values[ITEM_VALUES];
    long history[NODE_HISTORY];
} Item;

typedef struct {
    int opcode;
    int flags;
    long ticks;
    Item *primary;
    Item *secondary;
    int scratch[16];
} Context;

typedef struct {
    int dev_id;
    int status;
    long counter;
    int regs[DEVICE_REGS];
    Item cache[4];
} Device;

typedef struct {
    Item items[TABLE_COUNT];
    Device devices[8];
    Context contexts[8];
    long checksum;
} SystemState;

static long clamp_l(long v, long lo, long hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

static int abs_i(int x) {
    if (x < 0) return -x;
    return x;
}

static long tiny_hash(long seed, int round) {
    long acc = seed ^ 0x9e3779b97f4a7c15ULL;
    for (int i = 0; i < 8; i++) {
        acc ^= (acc << 7) + (acc >> 3) + round + i;
        if ((acc & 3) == 0) acc += round * 17;
        else acc -= i * 13;
    }
    return acc;
}

static void init_item(Item *it, int id, int seed) {
    it->id = id;
    it->score = (long)seed * 97L + id;
    it->flag = (char)((id + seed) & 0x7f);
    for (int i = 0; i < ITEM_VALUES; i++) {
        it->values[i] = seed + id * (i + 1) - i;
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        it->history[i] = (long)(seed + i) * (long)(id + 3);
    }
}

static void init_device(Device *dev, int id, int seed) {
    dev->dev_id = id;
    dev->status = seed ^ id;
    dev->counter = (long)seed * 31L + id;
    for (int i = 0; i < DEVICE_REGS; i++) {
        dev->regs[i] = seed + id + i * 5;
    }
    for (int i = 0; i < 4; i++) {
        init_item(&dev->cache[i], id * 10 + i, seed + i);
    }
}

static void init_system(SystemState *sys, int seed) {
    sys->checksum = seed;
    for (int i = 0; i < TABLE_COUNT; i++) {
        init_item(&sys->items[i], i, seed + i);
    }
    for (int i = 0; i < 8; i++) {
        init_device(&sys->devices[i], i, seed + i * 3);
        sys->contexts[i].opcode = i;
        sys->contexts[i].flags = seed ^ i;
        sys->contexts[i].ticks = seed + i;
        sys->contexts[i].primary = &sys->items[(i * 3) % TABLE_COUNT];
        sys->contexts[i].secondary = &sys->items[(i * 7 + 1) % TABLE_COUNT];
        for (int j = 0; j < 16; j++) {
            sys->contexts[i].scratch[j] = seed + i + j;
        }
    }
}

/*
 * This function should create parameter_layout_evidence for arg0.
 * It uses the parameter pointer repeatedly as a record base.
 */
static long inspect_item_direct(Item *it, int bias) {
    long acc = bias;
    acc += it->id;
    acc += it->score;
    acc += it->flag;
    for (int i = 0; i < ITEM_VALUES; i++) {
        acc += it->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if ((i & 1) == 0) acc += it->history[i];
        else acc ^= it->history[i];
    }
    return acc;
}

/*
 * This function intentionally saves arg0 to stack and reloads it.
 * At -O0 on AArch64 this usually becomes:
 *   str x0, [sp, ...]
 *   ldr x8, [sp, ...]
 *   ldr/str ..., [x8, #offset]
 */
static long inspect_item_stack(Item *it, int bias) {
    Item *saved = it;
    long acc = bias;
    acc += saved->id;
    acc += saved->score;
    saved->score += bias;
    acc += saved->flag;
    saved->values[0] += bias;
    saved->values[1] ^= saved->id;
    saved->values[2] += (int)(saved->score & 0xff);
    for (int i = 0; i < ITEM_VALUES; i++) {
        int v = saved->values[i];
        if ((v & 1) == 0) acc += v;
        else acc -= v;
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        saved->history[i] += acc + i;
        acc ^= saved->history[i];
    }
    return acc;
}

/*
 * This should create evidence for arg0 and arg1.
 */
static long compare_items(Item *left, Item *right, int bias) {
    Item *a = left;
    Item *b = right;
    long acc = bias;
    acc += a->id - b->id;
    acc += a->score + b->score;
    acc += a->flag ^ b->flag;
    for (int i = 0; i < ITEM_VALUES; i++) {
        acc += a->values[i];
        acc -= b->values[ITEM_VALUES - 1 - i];
        if ((acc & 7) == 3) {
            a->values[i] ^= b->id;
        } else {
            b->values[i] += a->id;
        }
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        acc += a->history[i] ^ b->history[i];
    }
    return acc;
}

/*
 * Context has pointer fields, but layout evidence should attach to Context *ctx
 * if ctx itself is used as base. Later it calls inspect_item_stack on ctx->primary.
 */
static long process_context(Context *ctx, int bias) {
    Context *local = ctx;
    long acc = bias;
    acc += local->opcode;
    acc += local->flags;
    acc += local->ticks;
    local->ticks += bias;
    for (int i = 0; i < 16; i++) {
        local->scratch[i] += bias + i;
        acc += local->scratch[i];
    }
    if (local->primary) {
        acc += inspect_item_stack(local->primary, bias + 1);
    }
    if (local->secondary) {
        acc += compare_items(local->primary, local->secondary, bias + 2);
    }
    return acc;
}

static long device_mix(Device *dev, Item *external, int bias) {
    Device *d = dev;
    Item *it = external;
    long acc = bias;
    acc += d->dev_id;
    acc += d->status;
    acc += d->counter;
    d->counter += bias;
    for (int i = 0; i < DEVICE_REGS; i++) {
        d->regs[i] += bias + i;
        acc += d->regs[i];
    }
    for (int i = 0; i < 4; i++) {
        acc += compare_items(&d->cache[i], it, bias + i);
    }
    return acc;
}

static long mutate_item_deep(Item *it, int round) {
    Item *p = it;
    long acc = round;
    switch ((p->flag + round) & 7) {
        case 0: p->score += p->id; break;
        case 1: p->score -= p->values[0]; break;
        case 2: p->flag ^= (char)round; break;
        case 3: p->values[3] += p->id; break;
        case 4: p->values[4] -= p->id; break;
        case 5: p->history[5] ^= p->score; break;
        case 6: p->history[6] += p->values[6]; break;
        default: p->score += tiny_hash(p->score, round); break;
    }
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    for (int i = 0; i < ITEM_VALUES; i++) {
        p->values[i] += round + i;
        acc += p->values[i];
    }
    return acc;
}

static long walk_table(Item *items, int count, int seed) {
    long acc = seed;
    for (int i = 0; i < count; i++) {
        Item *it = &items[i];
        acc += inspect_item_stack(it, seed + i);
        acc ^= mutate_item_deep(it, i);
        if ((acc & 0xff) == 0x42) {
            continue;
        }
        if (acc > 90000000L) {
            break;
        }
    }
    return acc;
}

static long run_system(SystemState *sys, int seed) {
    SystemState *s = sys;
    long acc = seed + s->checksum;
    for (int r = 0; r < ROUND_COUNT; r++) {
        for (int i = 0; i < 8; i++) {
            acc += process_context(&s->contexts[i], seed + r + i);
            acc ^= device_mix(&s->devices[i], &s->items[(i + r) % TABLE_COUNT], seed + r);
        }
        acc += walk_table(s->items, TABLE_COUNT, seed + r);
        s->checksum ^= acc;
    }
    return acc + s->checksum;
}

static long item_probe_000(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 0;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 0;
    p->values[0] += p->id + bias;
    p->history[0] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 0) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 0) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_001(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 1;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 1;
    p->values[1] += p->id + bias;
    p->history[1] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 1) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 1) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_002(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 2;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 2;
    p->values[2] += p->id + bias;
    p->history[2] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 2) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 2) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_003(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 3;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 3;
    p->values[3] += p->id + bias;
    p->history[3] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 3) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 3) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_004(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 4;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 4;
    p->values[4] += p->id + bias;
    p->history[4] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 4) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 4) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_005(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 5;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 5;
    p->values[5] += p->id + bias;
    p->history[5] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 5) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 5) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_006(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 6;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 6;
    p->values[6] += p->id + bias;
    p->history[6] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 6) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 6) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_007(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 7;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 7;
    p->values[7] += p->id + bias;
    p->history[7] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 7) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 7) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_008(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 8;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 8;
    p->values[8] += p->id + bias;
    p->history[8] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 8) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 8) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_009(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 9;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 9;
    p->values[9] += p->id + bias;
    p->history[9] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 9) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 9) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_010(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 10;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 10;
    p->values[10] += p->id + bias;
    p->history[10] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 10) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 10) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_011(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 11;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 11;
    p->values[11] += p->id + bias;
    p->history[11] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 11) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 11) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_012(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 12;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 12;
    p->values[0] += p->id + bias;
    p->history[12] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 12) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 12) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_013(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 13;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 13;
    p->values[1] += p->id + bias;
    p->history[13] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 13) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 13) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_014(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 14;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 14;
    p->values[2] += p->id + bias;
    p->history[14] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 14) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 14) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_015(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 15;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 15;
    p->values[3] += p->id + bias;
    p->history[15] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 15) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 15) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_016(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 16;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 16;
    p->values[4] += p->id + bias;
    p->history[0] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 16) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 16) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_017(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 17;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 17;
    p->values[5] += p->id + bias;
    p->history[1] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 17) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 17) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_018(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 18;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 18;
    p->values[6] += p->id + bias;
    p->history[2] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 18) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 18) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_019(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 19;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 19;
    p->values[7] += p->id + bias;
    p->history[3] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 19) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 19) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_020(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 20;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 20;
    p->values[8] += p->id + bias;
    p->history[4] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 20) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 20) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_021(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 21;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 21;
    p->values[9] += p->id + bias;
    p->history[5] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 21) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 21) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_022(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 22;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 22;
    p->values[10] += p->id + bias;
    p->history[6] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 22) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 22) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_023(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 23;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 23;
    p->values[11] += p->id + bias;
    p->history[7] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 23) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 23) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_024(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 24;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 24;
    p->values[0] += p->id + bias;
    p->history[8] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 24) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 24) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_025(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 25;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 25;
    p->values[1] += p->id + bias;
    p->history[9] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 25) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 25) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_026(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 26;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 26;
    p->values[2] += p->id + bias;
    p->history[10] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 26) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 26) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_027(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 27;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 27;
    p->values[3] += p->id + bias;
    p->history[11] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 27) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 27) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_028(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 28;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 28;
    p->values[4] += p->id + bias;
    p->history[12] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 28) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 28) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_029(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 29;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 29;
    p->values[5] += p->id + bias;
    p->history[13] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 29) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 29) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_030(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 30;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 30;
    p->values[6] += p->id + bias;
    p->history[14] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 30) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 30) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_031(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 31;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 31;
    p->values[7] += p->id + bias;
    p->history[15] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 31) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 31) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_032(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 32;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 32;
    p->values[8] += p->id + bias;
    p->history[0] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 32) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 32) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_033(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 33;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 33;
    p->values[9] += p->id + bias;
    p->history[1] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 33) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 33) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_034(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 34;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 34;
    p->values[10] += p->id + bias;
    p->history[2] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 34) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 34) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

static long item_probe_035(Item *it, int bias) {
    Item *p = it;
    long acc = bias + 35;
    acc += p->id;
    acc += p->score;
    acc += p->flag;
    p->score += bias + 35;
    p->values[11] += p->id + bias;
    p->history[3] ^= p->score + acc;
    for (int i = 0; i < ITEM_VALUES; i++) {
        if (((i + 35) & 1) == 0) acc += p->values[i];
        else acc -= p->values[i];
    }
    for (int i = 0; i < NODE_HISTORY; i++) {
        if (((i + 35) % 3) == 0) acc ^= p->history[i];
        else acc += p->history[i];
    }
    return acc;
}

typedef long (*ItemProbeFn)(Item *it, int bias);
static ItemProbeFn item_probe_table[36] = {
    item_probe_000,
    item_probe_001,
    item_probe_002,
    item_probe_003,
    item_probe_004,
    item_probe_005,
    item_probe_006,
    item_probe_007,
    item_probe_008,
    item_probe_009,
    item_probe_010,
    item_probe_011,
    item_probe_012,
    item_probe_013,
    item_probe_014,
    item_probe_015,
    item_probe_016,
    item_probe_017,
    item_probe_018,
    item_probe_019,
    item_probe_020,
    item_probe_021,
    item_probe_022,
    item_probe_023,
    item_probe_024,
    item_probe_025,
    item_probe_026,
    item_probe_027,
    item_probe_028,
    item_probe_029,
    item_probe_030,
    item_probe_031,
    item_probe_032,
    item_probe_033,
    item_probe_034,
    item_probe_035
};

static long dispatch_item_probes(Item *it, int seed) {
    long acc = seed;
    for (int i = 0; i < 36; i++) {
        acc += item_probe_table[i](it, seed + i);
    }
    return acc;
}

static long final_pass(SystemState *sys, int seed) {
    long acc = run_system(sys, seed);
    for (int i = 0; i < TABLE_COUNT; i++) {
        acc += dispatch_item_probes(&sys->items[i], seed + i);
    }
    for (int i = 0; i < 8; i++) {
        acc += process_context(&sys->contexts[i], seed + i);
    }
    return acc;
}

int main(void) {
    SystemState sys;
    init_system(&sys, 404);
    long result = final_pass(&sys, 1337);
    printf("hephaestus_param_layout_1k result=%ld checksum=%ld\n", result, sys.checksum);
    return (int)(result & 0xff);
}
