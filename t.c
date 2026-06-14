/*
 * hephaestus_2k_torture.c
 * Heavy C torture target for Hephaestus Phase 1-4 testing.
 * Build: clang -O0 -g hephaestus_2k_torture.c -o hephaestus_2k_torture
 */
#include <stdio.h>
#include <stdint.h>
#include <stddef.h>

#define NODE_COUNT 64
#define VALUE_COUNT 16
#define MATRIX_N 16
#define HISTORY_N 32
#define MIX_ROUNDS 48

typedef struct { int x; int y; int z; } Vec3;
typedef struct { uint8_t tag; uint16_t flags; int code; long weight; } Meta;
typedef struct {
    int id;
    long score;
    char state;
    int values[VALUE_COUNT];
    Vec3 pos;
    Meta meta;
} Node;

typedef struct {
    Node nodes[NODE_COUNT];
    int matrix[MATRIX_N][MATRIX_N];
    long history[HISTORY_N];
    int count;
    long checksum;
    char mode;
} Store;

typedef int (*NodeScoreFn)(Node *node, int bias);

static int abs_i(int x) {
    if (x < 0) return -x;
    return x;
}

static long clamp_l(long v, long lo, long hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

static int recursive_mix(int n, int seed) {
    if (n <= 0) return seed ^ 0x55aa;
    if (n == 1) return seed + 3;
    if ((n & 1) == 0) return recursive_mix(n - 1, seed + n) ^ recursive_mix(n - 2, seed - n);
    return recursive_mix(n - 1, seed ^ n) + recursive_mix(n - 3, seed + 7);
}

static void init_node(Node *node, int id, int seed) {
    node->id = id;
    node->score = (long)(seed * 13 + id * 17);
    node->state = (char)((id + seed) & 0x7f);
    node->pos.x = id + seed;
    node->pos.y = id - seed;
    node->pos.z = id * seed;
    node->meta.tag = (uint8_t)(id & 0xff);
    node->meta.flags = (uint16_t)((seed << 1) ^ id);
    node->meta.code = seed ^ (id * 31);
    node->meta.weight = (long)seed * 97L + id;
    for (int i = 0; i < VALUE_COUNT; i++) {
        int v = seed + id * (i + 1);
        if ((i & 1) == 0) node->values[i] = v ^ (i * 3);
        else node->values[i] = v - (i * 5);
    }
}

static void init_store(Store *store, int seed) {
    store->count = NODE_COUNT;
    store->checksum = 0;
    store->mode = (char)(seed & 7);
    for (int i = 0; i < NODE_COUNT; i++) init_node(&store->nodes[i], i, seed + i);
    for (int r = 0; r < MATRIX_N; r++) {
        for (int c = 0; c < MATRIX_N; c++) {
            int base = r * MATRIX_N + c + seed;
            if ((r + c) % 3 == 0) store->matrix[r][c] = base * 2;
            else if ((r ^ c) & 1) store->matrix[r][c] = base - r;
            else store->matrix[r][c] = base + c;
        }
    }
    for (int i = 0; i < HISTORY_N; i++) store->history[i] = (long)(seed + i) * (long)(i + 11);
}

static int score_a(Node *node, int bias) {
    int acc = bias + node->id + node->pos.x - node->pos.y;
    for (int i = 0; i < VALUE_COUNT; i++) {
        if ((node->values[i] & 1) == 0) acc += node->values[i] / (i + 1);
        else acc -= node->values[i] % (i + 3);
    }
    return acc + (int)(node->meta.weight % 101);
}

static int score_b(Node *node, int bias) {
    int acc = bias ^ node->meta.code;
    int i = 0;
    while (i < VALUE_COUNT) {
        acc += (node->values[i] ^ node->id) & 0xff;
        if (acc % 17 == 0) { i += 2; continue; }
        if (acc > 5000) break;
        i++;
    }
    return acc;
}

static int score_c(Node *node, int bias) {
    int acc = bias;
    switch (node->state & 7) {
        case 0: acc += node->id; break;
        case 1: acc -= node->pos.z; break;
        case 2: acc ^= node->meta.flags; break;
        case 3: acc += node->values[3]; break;
        case 4: acc -= node->values[4]; break;
        case 5: acc += recursive_mix(4, node->id); break;
        case 6: acc ^= (int)node->meta.weight; break;
        default: acc += node->values[0] + node->values[VALUE_COUNT - 1]; break;
    }
    return acc;
}

static int dispatch_score(Node *node, int bias, int selector) {
    NodeScoreFn fn;
    if ((selector % 3) == 0) fn = score_a;
    else if ((selector % 3) == 1) fn = score_b;
    else fn = score_c;
    return fn(node, bias);
}

static void mutate_node(Node *node, int round) {
    node->score += round + node->id;
    node->state = (char)((node->state + round) & 0x7f);
    node->pos.x += round % 5;
    node->pos.y -= round % 7;
    node->pos.z ^= round * 9;
    for (int i = 0; i < VALUE_COUNT; i++) {
        int old = node->values[i];
        if ((old + round) & 1) node->values[i] = old + node->id + round;
        else node->values[i] = old - node->id + i;
    }
    node->meta.code ^= round + node->values[round % VALUE_COUNT];
    node->meta.weight += node->meta.code;
}

static long matrix_walk(Store *store, int seed) {
    long acc = seed;
    for (int r = 0; r < MATRIX_N; r++) {
        for (int c = 0; c < MATRIX_N; c++) {
            int v = store->matrix[r][c];
            if ((r == c) || ((r + c) % 5 == 0)) acc += v;
            else if ((v & 3) == 0) acc ^= (long)(v + r - c);
            else acc -= (long)(v % 11);
        }
    }
    return acc;
}

static long history_fold(Store *store, int seed) {
    long acc = seed;
    for (int i = 0; i < HISTORY_N; i++) {
        long h = store->history[i];
        switch (i & 7) {
            case 0: acc += h; break;
            case 1: acc -= h; break;
            case 2: acc ^= h; break;
            case 3: acc += h * 3; break;
            case 4: acc -= h / 2; break;
            case 5: acc ^= (h << 1); break;
            case 6: acc += clamp_l(h, -100000, 100000); break;
            default: acc -= clamp_l(h, -50000, 50000); break;
        }
    }
    return acc;
}

static long pointer_chase(Store *store, int step) {
    long acc = 0;
    Node *p = &store->nodes[0];
    Node *end = &store->nodes[store->count];
    int index = 0;
    while (p < end) {
        acc += p->score + p->id + p->meta.weight;
        if ((index % step) == 0) mutate_node(p, index);
        if ((p->state & 15) == 13) acc ^= recursive_mix(3, p->id);
        p++;
        index++;
    }
    return acc;
}

static long scan_store(Store *store, int seed) {
    long acc = seed;
    for (int round = 0; round < MIX_ROUNDS; round++) {
        for (int i = 0; i < store->count; i++) {
            Node *node = &store->nodes[i];
            int s = dispatch_score(node, seed + round, i + round);
            if ((s & 1) == 0) { acc += s; node->score += s; }
            else { acc -= s; node->score -= s; }
            if ((i + round) % 9 == 0) { mutate_node(node, round); continue; }
            if ((acc & 0xff) == 0x42) break;
        }
        store->history[round % HISTORY_N] ^= acc + round;
        store->checksum += acc ^ matrix_walk(store, round + seed);
    }
    return acc + store->checksum;
}

static int micro_kernel_000(Store *store, int seed) {
    int acc = seed + 0;
    int pivot = (seed ^ 3) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 0) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 0; break;
            case 1: acc -= node->values[1] - 0; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 50000) break;
    }
    return acc;
}

static int micro_kernel_001(Store *store, int seed) {
    int acc = seed + 1;
    int pivot = (seed ^ 20) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 1) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 1; break;
            case 1: acc -= node->values[1] - 1; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 50031) break;
    }
    return acc;
}

static int micro_kernel_002(Store *store, int seed) {
    int acc = seed + 2;
    int pivot = (seed ^ 37) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 2) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 2; break;
            case 1: acc -= node->values[1] - 2; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 50062) break;
    }
    return acc;
}

static int micro_kernel_003(Store *store, int seed) {
    int acc = seed + 3;
    int pivot = (seed ^ 54) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 3) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 3; break;
            case 1: acc -= node->values[1] - 3; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 50093) break;
    }
    return acc;
}

static int micro_kernel_004(Store *store, int seed) {
    int acc = seed + 4;
    int pivot = (seed ^ 71) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 4) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 4; break;
            case 1: acc -= node->values[1] - 4; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 15) == 0) continue;
        if (acc > 50124) break;
    }
    return acc;
}

static int micro_kernel_005(Store *store, int seed) {
    int acc = seed + 5;
    int pivot = (seed ^ 88) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 5) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 5; break;
            case 1: acc -= node->values[1] - 5; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 16) == 0) continue;
        if (acc > 50155) break;
    }
    return acc;
}

static int micro_kernel_006(Store *store, int seed) {
    int acc = seed + 6;
    int pivot = (seed ^ 105) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 6) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 6; break;
            case 1: acc -= node->values[1] - 6; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 17) == 0) continue;
        if (acc > 50186) break;
    }
    return acc;
}

static int micro_kernel_007(Store *store, int seed) {
    int acc = seed + 7;
    int pivot = (seed ^ 122) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 7) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 7; break;
            case 1: acc -= node->values[1] - 7; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 18) == 0) continue;
        if (acc > 50217) break;
    }
    return acc;
}

static int micro_kernel_008(Store *store, int seed) {
    int acc = seed + 8;
    int pivot = (seed ^ 139) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 8) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 8; break;
            case 1: acc -= node->values[1] - 8; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 19) == 0) continue;
        if (acc > 50248) break;
    }
    return acc;
}

static int micro_kernel_009(Store *store, int seed) {
    int acc = seed + 9;
    int pivot = (seed ^ 156) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 9) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 9; break;
            case 1: acc -= node->values[1] - 9; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 20) == 0) continue;
        if (acc > 50279) break;
    }
    return acc;
}

static int micro_kernel_010(Store *store, int seed) {
    int acc = seed + 10;
    int pivot = (seed ^ 173) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 10) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 10; break;
            case 1: acc -= node->values[1] - 10; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 21) == 0) continue;
        if (acc > 50310) break;
    }
    return acc;
}

static int micro_kernel_011(Store *store, int seed) {
    int acc = seed + 11;
    int pivot = (seed ^ 190) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 11) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 11; break;
            case 1: acc -= node->values[1] - 11; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 22) == 0) continue;
        if (acc > 50341) break;
    }
    return acc;
}

static int micro_kernel_012(Store *store, int seed) {
    int acc = seed + 12;
    int pivot = (seed ^ 207) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 12) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 12; break;
            case 1: acc -= node->values[1] - 12; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 23) == 0) continue;
        if (acc > 50372) break;
    }
    return acc;
}

static int micro_kernel_013(Store *store, int seed) {
    int acc = seed + 13;
    int pivot = (seed ^ 224) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 13) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 13; break;
            case 1: acc -= node->values[1] - 13; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 50403) break;
    }
    return acc;
}

static int micro_kernel_014(Store *store, int seed) {
    int acc = seed + 14;
    int pivot = (seed ^ 241) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 14) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 14; break;
            case 1: acc -= node->values[1] - 14; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 50434) break;
    }
    return acc;
}

static int micro_kernel_015(Store *store, int seed) {
    int acc = seed + 15;
    int pivot = (seed ^ 258) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 15) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 15; break;
            case 1: acc -= node->values[1] - 15; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 50465) break;
    }
    return acc;
}

static int micro_kernel_016(Store *store, int seed) {
    int acc = seed + 16;
    int pivot = (seed ^ 275) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 16) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 16; break;
            case 1: acc -= node->values[1] - 16; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 50496) break;
    }
    return acc;
}

static int micro_kernel_017(Store *store, int seed) {
    int acc = seed + 17;
    int pivot = (seed ^ 292) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 17) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 17; break;
            case 1: acc -= node->values[1] - 17; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 15) == 0) continue;
        if (acc > 50527) break;
    }
    return acc;
}

static int micro_kernel_018(Store *store, int seed) {
    int acc = seed + 18;
    int pivot = (seed ^ 309) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 18) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 18; break;
            case 1: acc -= node->values[1] - 18; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 16) == 0) continue;
        if (acc > 50558) break;
    }
    return acc;
}

static int micro_kernel_019(Store *store, int seed) {
    int acc = seed + 19;
    int pivot = (seed ^ 326) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 19) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 19; break;
            case 1: acc -= node->values[1] - 19; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 17) == 0) continue;
        if (acc > 50589) break;
    }
    return acc;
}

static int micro_kernel_020(Store *store, int seed) {
    int acc = seed + 20;
    int pivot = (seed ^ 343) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 20) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 20; break;
            case 1: acc -= node->values[1] - 20; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 18) == 0) continue;
        if (acc > 50620) break;
    }
    return acc;
}

static int micro_kernel_021(Store *store, int seed) {
    int acc = seed + 21;
    int pivot = (seed ^ 360) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 21) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 21; break;
            case 1: acc -= node->values[1] - 21; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 19) == 0) continue;
        if (acc > 50651) break;
    }
    return acc;
}

static int micro_kernel_022(Store *store, int seed) {
    int acc = seed + 22;
    int pivot = (seed ^ 377) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 22) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 22; break;
            case 1: acc -= node->values[1] - 22; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 20) == 0) continue;
        if (acc > 50682) break;
    }
    return acc;
}

static int micro_kernel_023(Store *store, int seed) {
    int acc = seed + 23;
    int pivot = (seed ^ 394) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 23) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 23; break;
            case 1: acc -= node->values[1] - 23; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 21) == 0) continue;
        if (acc > 50713) break;
    }
    return acc;
}

static int micro_kernel_024(Store *store, int seed) {
    int acc = seed + 24;
    int pivot = (seed ^ 411) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 24) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 24; break;
            case 1: acc -= node->values[1] - 24; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 22) == 0) continue;
        if (acc > 50744) break;
    }
    return acc;
}

static int micro_kernel_025(Store *store, int seed) {
    int acc = seed + 25;
    int pivot = (seed ^ 428) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 25) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 25; break;
            case 1: acc -= node->values[1] - 25; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 23) == 0) continue;
        if (acc > 50775) break;
    }
    return acc;
}

static int micro_kernel_026(Store *store, int seed) {
    int acc = seed + 26;
    int pivot = (seed ^ 445) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 26) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 26; break;
            case 1: acc -= node->values[1] - 26; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 50806) break;
    }
    return acc;
}

static int micro_kernel_027(Store *store, int seed) {
    int acc = seed + 27;
    int pivot = (seed ^ 462) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 27) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 27; break;
            case 1: acc -= node->values[1] - 27; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 50837) break;
    }
    return acc;
}

static int micro_kernel_028(Store *store, int seed) {
    int acc = seed + 28;
    int pivot = (seed ^ 479) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 28) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 28; break;
            case 1: acc -= node->values[1] - 28; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 50868) break;
    }
    return acc;
}

static int micro_kernel_029(Store *store, int seed) {
    int acc = seed + 29;
    int pivot = (seed ^ 496) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 29) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 29; break;
            case 1: acc -= node->values[1] - 29; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 50899) break;
    }
    return acc;
}

static int micro_kernel_030(Store *store, int seed) {
    int acc = seed + 30;
    int pivot = (seed ^ 513) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 30) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 30; break;
            case 1: acc -= node->values[1] - 30; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 15) == 0) continue;
        if (acc > 50930) break;
    }
    return acc;
}

static int micro_kernel_031(Store *store, int seed) {
    int acc = seed + 31;
    int pivot = (seed ^ 530) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 31) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 31; break;
            case 1: acc -= node->values[1] - 31; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 16) == 0) continue;
        if (acc > 50961) break;
    }
    return acc;
}

static int micro_kernel_032(Store *store, int seed) {
    int acc = seed + 32;
    int pivot = (seed ^ 547) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 32) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 32; break;
            case 1: acc -= node->values[1] - 32; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 17) == 0) continue;
        if (acc > 50992) break;
    }
    return acc;
}

static int micro_kernel_033(Store *store, int seed) {
    int acc = seed + 33;
    int pivot = (seed ^ 564) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 33) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 33; break;
            case 1: acc -= node->values[1] - 33; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 18) == 0) continue;
        if (acc > 51023) break;
    }
    return acc;
}

static int micro_kernel_034(Store *store, int seed) {
    int acc = seed + 34;
    int pivot = (seed ^ 581) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 34) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 34; break;
            case 1: acc -= node->values[1] - 34; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 19) == 0) continue;
        if (acc > 51054) break;
    }
    return acc;
}

static int micro_kernel_035(Store *store, int seed) {
    int acc = seed + 35;
    int pivot = (seed ^ 598) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 35) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 35; break;
            case 1: acc -= node->values[1] - 35; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 20) == 0) continue;
        if (acc > 51085) break;
    }
    return acc;
}

static int micro_kernel_036(Store *store, int seed) {
    int acc = seed + 36;
    int pivot = (seed ^ 615) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 36) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 36; break;
            case 1: acc -= node->values[1] - 36; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 21) == 0) continue;
        if (acc > 51116) break;
    }
    return acc;
}

static int micro_kernel_037(Store *store, int seed) {
    int acc = seed + 37;
    int pivot = (seed ^ 632) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 37) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 37; break;
            case 1: acc -= node->values[1] - 37; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 22) == 0) continue;
        if (acc > 51147) break;
    }
    return acc;
}

static int micro_kernel_038(Store *store, int seed) {
    int acc = seed + 38;
    int pivot = (seed ^ 649) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 38) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 38; break;
            case 1: acc -= node->values[1] - 38; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 23) == 0) continue;
        if (acc > 51178) break;
    }
    return acc;
}

static int micro_kernel_039(Store *store, int seed) {
    int acc = seed + 39;
    int pivot = (seed ^ 666) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 39) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 39; break;
            case 1: acc -= node->values[1] - 39; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 51209) break;
    }
    return acc;
}

static int micro_kernel_040(Store *store, int seed) {
    int acc = seed + 40;
    int pivot = (seed ^ 683) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 40) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 40; break;
            case 1: acc -= node->values[1] - 40; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 51240) break;
    }
    return acc;
}

static int micro_kernel_041(Store *store, int seed) {
    int acc = seed + 41;
    int pivot = (seed ^ 700) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 41) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 41; break;
            case 1: acc -= node->values[1] - 41; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 51271) break;
    }
    return acc;
}

static int micro_kernel_042(Store *store, int seed) {
    int acc = seed + 42;
    int pivot = (seed ^ 717) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 42) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 42; break;
            case 1: acc -= node->values[1] - 42; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 51302) break;
    }
    return acc;
}

static int micro_kernel_043(Store *store, int seed) {
    int acc = seed + 43;
    int pivot = (seed ^ 734) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 43) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 43; break;
            case 1: acc -= node->values[1] - 43; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 15) == 0) continue;
        if (acc > 51333) break;
    }
    return acc;
}

static int micro_kernel_044(Store *store, int seed) {
    int acc = seed + 44;
    int pivot = (seed ^ 751) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 44) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 44; break;
            case 1: acc -= node->values[1] - 44; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 16) == 0) continue;
        if (acc > 51364) break;
    }
    return acc;
}

static int micro_kernel_045(Store *store, int seed) {
    int acc = seed + 45;
    int pivot = (seed ^ 768) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 45) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 45; break;
            case 1: acc -= node->values[1] - 45; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 17) == 0) continue;
        if (acc > 51395) break;
    }
    return acc;
}

static int micro_kernel_046(Store *store, int seed) {
    int acc = seed + 46;
    int pivot = (seed ^ 785) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 46) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 46; break;
            case 1: acc -= node->values[1] - 46; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 18) == 0) continue;
        if (acc > 51426) break;
    }
    return acc;
}

static int micro_kernel_047(Store *store, int seed) {
    int acc = seed + 47;
    int pivot = (seed ^ 802) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 47) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 47; break;
            case 1: acc -= node->values[1] - 47; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 19) == 0) continue;
        if (acc > 51457) break;
    }
    return acc;
}

static int micro_kernel_048(Store *store, int seed) {
    int acc = seed + 48;
    int pivot = (seed ^ 819) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 48) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 48; break;
            case 1: acc -= node->values[1] - 48; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 20) == 0) continue;
        if (acc > 51488) break;
    }
    return acc;
}

static int micro_kernel_049(Store *store, int seed) {
    int acc = seed + 49;
    int pivot = (seed ^ 836) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 49) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 49; break;
            case 1: acc -= node->values[1] - 49; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 21) == 0) continue;
        if (acc > 51519) break;
    }
    return acc;
}

static int micro_kernel_050(Store *store, int seed) {
    int acc = seed + 50;
    int pivot = (seed ^ 853) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 50) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 50; break;
            case 1: acc -= node->values[1] - 50; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 22) == 0) continue;
        if (acc > 51550) break;
    }
    return acc;
}

static int micro_kernel_051(Store *store, int seed) {
    int acc = seed + 51;
    int pivot = (seed ^ 870) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 51) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 51; break;
            case 1: acc -= node->values[1] - 51; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 23) == 0) continue;
        if (acc > 51581) break;
    }
    return acc;
}

static int micro_kernel_052(Store *store, int seed) {
    int acc = seed + 52;
    int pivot = (seed ^ 887) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 52) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 52; break;
            case 1: acc -= node->values[1] - 52; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 51612) break;
    }
    return acc;
}

static int micro_kernel_053(Store *store, int seed) {
    int acc = seed + 53;
    int pivot = (seed ^ 904) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 53) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 53; break;
            case 1: acc -= node->values[1] - 53; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 51643) break;
    }
    return acc;
}

static int micro_kernel_054(Store *store, int seed) {
    int acc = seed + 54;
    int pivot = (seed ^ 921) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 54) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 54; break;
            case 1: acc -= node->values[1] - 54; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 51674) break;
    }
    return acc;
}

static int micro_kernel_055(Store *store, int seed) {
    int acc = seed + 55;
    int pivot = (seed ^ 938) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 55) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 55; break;
            case 1: acc -= node->values[1] - 55; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 51705) break;
    }
    return acc;
}

static int micro_kernel_056(Store *store, int seed) {
    int acc = seed + 56;
    int pivot = (seed ^ 955) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 56) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 56; break;
            case 1: acc -= node->values[1] - 56; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 15) == 0) continue;
        if (acc > 51736) break;
    }
    return acc;
}

static int micro_kernel_057(Store *store, int seed) {
    int acc = seed + 57;
    int pivot = (seed ^ 972) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 57) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 57; break;
            case 1: acc -= node->values[1] - 57; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 16) == 0) continue;
        if (acc > 51767) break;
    }
    return acc;
}

static int micro_kernel_058(Store *store, int seed) {
    int acc = seed + 58;
    int pivot = (seed ^ 989) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 58) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 58; break;
            case 1: acc -= node->values[1] - 58; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 17) == 0) continue;
        if (acc > 51798) break;
    }
    return acc;
}

static int micro_kernel_059(Store *store, int seed) {
    int acc = seed + 59;
    int pivot = (seed ^ 1006) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 59) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 59; break;
            case 1: acc -= node->values[1] - 59; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 18) == 0) continue;
        if (acc > 51829) break;
    }
    return acc;
}

static int micro_kernel_060(Store *store, int seed) {
    int acc = seed + 60;
    int pivot = (seed ^ 1023) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 60) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 60; break;
            case 1: acc -= node->values[1] - 60; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 19) == 0) continue;
        if (acc > 51860) break;
    }
    return acc;
}

static int micro_kernel_061(Store *store, int seed) {
    int acc = seed + 61;
    int pivot = (seed ^ 1040) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 61) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 61; break;
            case 1: acc -= node->values[1] - 61; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 20) == 0) continue;
        if (acc > 51891) break;
    }
    return acc;
}

static int micro_kernel_062(Store *store, int seed) {
    int acc = seed + 62;
    int pivot = (seed ^ 1057) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 62) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 62; break;
            case 1: acc -= node->values[1] - 62; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 21) == 0) continue;
        if (acc > 51922) break;
    }
    return acc;
}

static int micro_kernel_063(Store *store, int seed) {
    int acc = seed + 63;
    int pivot = (seed ^ 1074) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 63) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 63; break;
            case 1: acc -= node->values[1] - 63; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 22) == 0) continue;
        if (acc > 51953) break;
    }
    return acc;
}

static int micro_kernel_064(Store *store, int seed) {
    int acc = seed + 64;
    int pivot = (seed ^ 1091) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 64) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 64; break;
            case 1: acc -= node->values[1] - 64; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 23) == 0) continue;
        if (acc > 51984) break;
    }
    return acc;
}

static int micro_kernel_065(Store *store, int seed) {
    int acc = seed + 65;
    int pivot = (seed ^ 1108) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 65) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 65; break;
            case 1: acc -= node->values[1] - 65; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 52015) break;
    }
    return acc;
}

static int micro_kernel_066(Store *store, int seed) {
    int acc = seed + 66;
    int pivot = (seed ^ 1125) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 66) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 66; break;
            case 1: acc -= node->values[1] - 66; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 52046) break;
    }
    return acc;
}

static int micro_kernel_067(Store *store, int seed) {
    int acc = seed + 67;
    int pivot = (seed ^ 1142) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 67) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 67; break;
            case 1: acc -= node->values[1] - 67; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 52077) break;
    }
    return acc;
}

static int micro_kernel_068(Store *store, int seed) {
    int acc = seed + 68;
    int pivot = (seed ^ 1159) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 68) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 68; break;
            case 1: acc -= node->values[1] - 68; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 52108) break;
    }
    return acc;
}

static int micro_kernel_069(Store *store, int seed) {
    int acc = seed + 69;
    int pivot = (seed ^ 1176) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 69) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 69; break;
            case 1: acc -= node->values[1] - 69; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 15) == 0) continue;
        if (acc > 52139) break;
    }
    return acc;
}

static int micro_kernel_070(Store *store, int seed) {
    int acc = seed + 70;
    int pivot = (seed ^ 1193) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 70) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 70; break;
            case 1: acc -= node->values[1] - 70; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 16) == 0) continue;
        if (acc > 52170) break;
    }
    return acc;
}

static int micro_kernel_071(Store *store, int seed) {
    int acc = seed + 71;
    int pivot = (seed ^ 1210) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 71) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 71; break;
            case 1: acc -= node->values[1] - 71; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 17) == 0) continue;
        if (acc > 52201) break;
    }
    return acc;
}

static int micro_kernel_072(Store *store, int seed) {
    int acc = seed + 72;
    int pivot = (seed ^ 1227) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 72) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 72; break;
            case 1: acc -= node->values[1] - 72; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 18) == 0) continue;
        if (acc > 52232) break;
    }
    return acc;
}

static int micro_kernel_073(Store *store, int seed) {
    int acc = seed + 73;
    int pivot = (seed ^ 1244) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 73) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 73; break;
            case 1: acc -= node->values[1] - 73; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 19) == 0) continue;
        if (acc > 52263) break;
    }
    return acc;
}

static int micro_kernel_074(Store *store, int seed) {
    int acc = seed + 74;
    int pivot = (seed ^ 1261) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 74) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 74; break;
            case 1: acc -= node->values[1] - 74; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 20) == 0) continue;
        if (acc > 52294) break;
    }
    return acc;
}

static int micro_kernel_075(Store *store, int seed) {
    int acc = seed + 75;
    int pivot = (seed ^ 1278) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 75) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 75; break;
            case 1: acc -= node->values[1] - 75; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 21) == 0) continue;
        if (acc > 52325) break;
    }
    return acc;
}

static int micro_kernel_076(Store *store, int seed) {
    int acc = seed + 76;
    int pivot = (seed ^ 1295) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 76) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 76; break;
            case 1: acc -= node->values[1] - 76; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 22) == 0) continue;
        if (acc > 52356) break;
    }
    return acc;
}

static int micro_kernel_077(Store *store, int seed) {
    int acc = seed + 77;
    int pivot = (seed ^ 1312) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 77) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 77; break;
            case 1: acc -= node->values[1] - 77; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 23) == 0) continue;
        if (acc > 52387) break;
    }
    return acc;
}

static int micro_kernel_078(Store *store, int seed) {
    int acc = seed + 78;
    int pivot = (seed ^ 1329) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 78) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 78; break;
            case 1: acc -= node->values[1] - 78; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 52418) break;
    }
    return acc;
}

static int micro_kernel_079(Store *store, int seed) {
    int acc = seed + 79;
    int pivot = (seed ^ 1346) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 79) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 79; break;
            case 1: acc -= node->values[1] - 79; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 52449) break;
    }
    return acc;
}

static int micro_kernel_080(Store *store, int seed) {
    int acc = seed + 80;
    int pivot = (seed ^ 1363) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 80) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 80; break;
            case 1: acc -= node->values[1] - 80; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 52480) break;
    }
    return acc;
}

static int micro_kernel_081(Store *store, int seed) {
    int acc = seed + 81;
    int pivot = (seed ^ 1380) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 81) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 81; break;
            case 1: acc -= node->values[1] - 81; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 52511) break;
    }
    return acc;
}

static int micro_kernel_082(Store *store, int seed) {
    int acc = seed + 82;
    int pivot = (seed ^ 1397) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 82) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 82; break;
            case 1: acc -= node->values[1] - 82; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 15) == 0) continue;
        if (acc > 52542) break;
    }
    return acc;
}

static int micro_kernel_083(Store *store, int seed) {
    int acc = seed + 83;
    int pivot = (seed ^ 1414) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 83) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 83; break;
            case 1: acc -= node->values[1] - 83; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 16) == 0) continue;
        if (acc > 52573) break;
    }
    return acc;
}

static int micro_kernel_084(Store *store, int seed) {
    int acc = seed + 84;
    int pivot = (seed ^ 1431) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 84) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 84; break;
            case 1: acc -= node->values[1] - 84; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 17) == 0) continue;
        if (acc > 52604) break;
    }
    return acc;
}

static int micro_kernel_085(Store *store, int seed) {
    int acc = seed + 85;
    int pivot = (seed ^ 1448) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 85) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 85; break;
            case 1: acc -= node->values[1] - 85; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 18) == 0) continue;
        if (acc > 52635) break;
    }
    return acc;
}

static int micro_kernel_086(Store *store, int seed) {
    int acc = seed + 86;
    int pivot = (seed ^ 1465) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 86) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 86; break;
            case 1: acc -= node->values[1] - 86; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 19) == 0) continue;
        if (acc > 52666) break;
    }
    return acc;
}

static int micro_kernel_087(Store *store, int seed) {
    int acc = seed + 87;
    int pivot = (seed ^ 1482) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 87) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 87; break;
            case 1: acc -= node->values[1] - 87; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 20) == 0) continue;
        if (acc > 52697) break;
    }
    return acc;
}

static int micro_kernel_088(Store *store, int seed) {
    int acc = seed + 88;
    int pivot = (seed ^ 1499) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 88) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 88; break;
            case 1: acc -= node->values[1] - 88; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 21) == 0) continue;
        if (acc > 52728) break;
    }
    return acc;
}

static int micro_kernel_089(Store *store, int seed) {
    int acc = seed + 89;
    int pivot = (seed ^ 1516) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 89) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 89; break;
            case 1: acc -= node->values[1] - 89; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 22) == 0) continue;
        if (acc > 52759) break;
    }
    return acc;
}

static int micro_kernel_090(Store *store, int seed) {
    int acc = seed + 90;
    int pivot = (seed ^ 1533) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 90) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 90; break;
            case 1: acc -= node->values[1] - 90; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 23) == 0) continue;
        if (acc > 52790) break;
    }
    return acc;
}

static int micro_kernel_091(Store *store, int seed) {
    int acc = seed + 91;
    int pivot = (seed ^ 1550) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 91) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 91; break;
            case 1: acc -= node->values[1] - 91; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 52821) break;
    }
    return acc;
}

static int micro_kernel_092(Store *store, int seed) {
    int acc = seed + 92;
    int pivot = (seed ^ 1567) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 92) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 92; break;
            case 1: acc -= node->values[1] - 92; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 52852) break;
    }
    return acc;
}

static int micro_kernel_093(Store *store, int seed) {
    int acc = seed + 93;
    int pivot = (seed ^ 1584) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 93) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 93; break;
            case 1: acc -= node->values[1] - 93; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 52883) break;
    }
    return acc;
}

static int micro_kernel_094(Store *store, int seed) {
    int acc = seed + 94;
    int pivot = (seed ^ 1601) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 94) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 94; break;
            case 1: acc -= node->values[1] - 94; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 52914) break;
    }
    return acc;
}

static int micro_kernel_095(Store *store, int seed) {
    int acc = seed + 95;
    int pivot = (seed ^ 1618) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 95) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 95; break;
            case 1: acc -= node->values[1] - 95; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 15) == 0) continue;
        if (acc > 52945) break;
    }
    return acc;
}

static int micro_kernel_096(Store *store, int seed) {
    int acc = seed + 96;
    int pivot = (seed ^ 1635) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 96) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 96; break;
            case 1: acc -= node->values[1] - 96; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 16) == 0) continue;
        if (acc > 52976) break;
    }
    return acc;
}

static int micro_kernel_097(Store *store, int seed) {
    int acc = seed + 97;
    int pivot = (seed ^ 1652) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 97) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 97; break;
            case 1: acc -= node->values[1] - 97; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 17) == 0) continue;
        if (acc > 53007) break;
    }
    return acc;
}

static int micro_kernel_098(Store *store, int seed) {
    int acc = seed + 98;
    int pivot = (seed ^ 1669) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 98) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 98; break;
            case 1: acc -= node->values[1] - 98; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 18) == 0) continue;
        if (acc > 53038) break;
    }
    return acc;
}

static int micro_kernel_099(Store *store, int seed) {
    int acc = seed + 99;
    int pivot = (seed ^ 1686) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 99) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 99; break;
            case 1: acc -= node->values[1] - 99; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 19) == 0) continue;
        if (acc > 53069) break;
    }
    return acc;
}

static int micro_kernel_100(Store *store, int seed) {
    int acc = seed + 100;
    int pivot = (seed ^ 1703) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 100) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 100; break;
            case 1: acc -= node->values[1] - 100; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 20) == 0) continue;
        if (acc > 53100) break;
    }
    return acc;
}

static int micro_kernel_101(Store *store, int seed) {
    int acc = seed + 101;
    int pivot = (seed ^ 1720) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 101) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 101; break;
            case 1: acc -= node->values[1] - 101; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 21) == 0) continue;
        if (acc > 53131) break;
    }
    return acc;
}

static int micro_kernel_102(Store *store, int seed) {
    int acc = seed + 102;
    int pivot = (seed ^ 1737) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 102) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 102; break;
            case 1: acc -= node->values[1] - 102; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 22) == 0) continue;
        if (acc > 53162) break;
    }
    return acc;
}

static int micro_kernel_103(Store *store, int seed) {
    int acc = seed + 103;
    int pivot = (seed ^ 1754) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 103) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 103; break;
            case 1: acc -= node->values[1] - 103; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 23) == 0) continue;
        if (acc > 53193) break;
    }
    return acc;
}

static int micro_kernel_104(Store *store, int seed) {
    int acc = seed + 104;
    int pivot = (seed ^ 1771) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 104) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 104; break;
            case 1: acc -= node->values[1] - 104; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 53224) break;
    }
    return acc;
}

static int micro_kernel_105(Store *store, int seed) {
    int acc = seed + 105;
    int pivot = (seed ^ 1788) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 105) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 105; break;
            case 1: acc -= node->values[1] - 105; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 53255) break;
    }
    return acc;
}

static int micro_kernel_106(Store *store, int seed) {
    int acc = seed + 106;
    int pivot = (seed ^ 1805) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 106) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 106; break;
            case 1: acc -= node->values[1] - 106; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 53286) break;
    }
    return acc;
}

static int micro_kernel_107(Store *store, int seed) {
    int acc = seed + 107;
    int pivot = (seed ^ 1822) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 107) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 107; break;
            case 1: acc -= node->values[1] - 107; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 53317) break;
    }
    return acc;
}

static int micro_kernel_108(Store *store, int seed) {
    int acc = seed + 108;
    int pivot = (seed ^ 1839) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 108) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 108; break;
            case 1: acc -= node->values[1] - 108; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 15) == 0) continue;
        if (acc > 53348) break;
    }
    return acc;
}

static int micro_kernel_109(Store *store, int seed) {
    int acc = seed + 109;
    int pivot = (seed ^ 1856) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 109) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 109; break;
            case 1: acc -= node->values[1] - 109; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 16) == 0) continue;
        if (acc > 53379) break;
    }
    return acc;
}

static int micro_kernel_110(Store *store, int seed) {
    int acc = seed + 110;
    int pivot = (seed ^ 1873) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 110) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 110; break;
            case 1: acc -= node->values[1] - 110; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 17) == 0) continue;
        if (acc > 53410) break;
    }
    return acc;
}

static int micro_kernel_111(Store *store, int seed) {
    int acc = seed + 111;
    int pivot = (seed ^ 1890) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 111) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 111; break;
            case 1: acc -= node->values[1] - 111; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 18) == 0) continue;
        if (acc > 53441) break;
    }
    return acc;
}

static int micro_kernel_112(Store *store, int seed) {
    int acc = seed + 112;
    int pivot = (seed ^ 1907) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 112) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 112; break;
            case 1: acc -= node->values[1] - 112; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 19) == 0) continue;
        if (acc > 53472) break;
    }
    return acc;
}

static int micro_kernel_113(Store *store, int seed) {
    int acc = seed + 113;
    int pivot = (seed ^ 1924) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 113) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 113; break;
            case 1: acc -= node->values[1] - 113; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 20) == 0) continue;
        if (acc > 53503) break;
    }
    return acc;
}

static int micro_kernel_114(Store *store, int seed) {
    int acc = seed + 114;
    int pivot = (seed ^ 1941) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 114) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 114; break;
            case 1: acc -= node->values[1] - 114; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 21) == 0) continue;
        if (acc > 53534) break;
    }
    return acc;
}

static int micro_kernel_115(Store *store, int seed) {
    int acc = seed + 115;
    int pivot = (seed ^ 1958) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 115) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 115; break;
            case 1: acc -= node->values[1] - 115; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 22) == 0) continue;
        if (acc > 53565) break;
    }
    return acc;
}

static int micro_kernel_116(Store *store, int seed) {
    int acc = seed + 116;
    int pivot = (seed ^ 1975) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 116) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 116; break;
            case 1: acc -= node->values[1] - 116; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 23) == 0) continue;
        if (acc > 53596) break;
    }
    return acc;
}

static int micro_kernel_117(Store *store, int seed) {
    int acc = seed + 117;
    int pivot = (seed ^ 1992) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 117) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 117; break;
            case 1: acc -= node->values[1] - 117; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 53627) break;
    }
    return acc;
}

static int micro_kernel_118(Store *store, int seed) {
    int acc = seed + 118;
    int pivot = (seed ^ 2009) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 118) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 118; break;
            case 1: acc -= node->values[1] - 118; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 53658) break;
    }
    return acc;
}

static int micro_kernel_119(Store *store, int seed) {
    int acc = seed + 119;
    int pivot = (seed ^ 2026) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 119) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 119; break;
            case 1: acc -= node->values[1] - 119; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 53689) break;
    }
    return acc;
}

static int micro_kernel_120(Store *store, int seed) {
    int acc = seed + 120;
    int pivot = (seed ^ 2043) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 120) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 120; break;
            case 1: acc -= node->values[1] - 120; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 53720) break;
    }
    return acc;
}

static int micro_kernel_121(Store *store, int seed) {
    int acc = seed + 121;
    int pivot = (seed ^ 2060) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 121) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 121; break;
            case 1: acc -= node->values[1] - 121; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 15) == 0) continue;
        if (acc > 53751) break;
    }
    return acc;
}

static int micro_kernel_122(Store *store, int seed) {
    int acc = seed + 122;
    int pivot = (seed ^ 2077) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 122) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 122; break;
            case 1: acc -= node->values[1] - 122; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 16) == 0) continue;
        if (acc > 53782) break;
    }
    return acc;
}

static int micro_kernel_123(Store *store, int seed) {
    int acc = seed + 123;
    int pivot = (seed ^ 2094) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 123) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 123; break;
            case 1: acc -= node->values[1] - 123; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 17) == 0) continue;
        if (acc > 53813) break;
    }
    return acc;
}

static int micro_kernel_124(Store *store, int seed) {
    int acc = seed + 124;
    int pivot = (seed ^ 2111) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 124) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 124; break;
            case 1: acc -= node->values[1] - 124; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 18) == 0) continue;
        if (acc > 53844) break;
    }
    return acc;
}

static int micro_kernel_125(Store *store, int seed) {
    int acc = seed + 125;
    int pivot = (seed ^ 2128) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 125) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 125; break;
            case 1: acc -= node->values[1] - 125; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 19) == 0) continue;
        if (acc > 53875) break;
    }
    return acc;
}

static int micro_kernel_126(Store *store, int seed) {
    int acc = seed + 126;
    int pivot = (seed ^ 2145) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 126) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 126; break;
            case 1: acc -= node->values[1] - 126; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 20) == 0) continue;
        if (acc > 53906) break;
    }
    return acc;
}

static int micro_kernel_127(Store *store, int seed) {
    int acc = seed + 127;
    int pivot = (seed ^ 2162) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 127) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 127; break;
            case 1: acc -= node->values[1] - 127; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 21) == 0) continue;
        if (acc > 53937) break;
    }
    return acc;
}

static int micro_kernel_128(Store *store, int seed) {
    int acc = seed + 128;
    int pivot = (seed ^ 2179) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 128) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 128; break;
            case 1: acc -= node->values[1] - 128; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 22) == 0) continue;
        if (acc > 53968) break;
    }
    return acc;
}

static int micro_kernel_129(Store *store, int seed) {
    int acc = seed + 129;
    int pivot = (seed ^ 2196) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 129) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 129; break;
            case 1: acc -= node->values[1] - 129; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 23) == 0) continue;
        if (acc > 53999) break;
    }
    return acc;
}

static int micro_kernel_130(Store *store, int seed) {
    int acc = seed + 130;
    int pivot = (seed ^ 2213) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 130) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 130; break;
            case 1: acc -= node->values[1] - 130; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 54030) break;
    }
    return acc;
}

static int micro_kernel_131(Store *store, int seed) {
    int acc = seed + 131;
    int pivot = (seed ^ 2230) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 131) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 131; break;
            case 1: acc -= node->values[1] - 131; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 54061) break;
    }
    return acc;
}

static int micro_kernel_132(Store *store, int seed) {
    int acc = seed + 132;
    int pivot = (seed ^ 2247) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 132) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 132; break;
            case 1: acc -= node->values[1] - 132; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 54092) break;
    }
    return acc;
}

static int micro_kernel_133(Store *store, int seed) {
    int acc = seed + 133;
    int pivot = (seed ^ 2264) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 133) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 133; break;
            case 1: acc -= node->values[1] - 133; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 54123) break;
    }
    return acc;
}

static int micro_kernel_134(Store *store, int seed) {
    int acc = seed + 134;
    int pivot = (seed ^ 2281) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 134) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 134; break;
            case 1: acc -= node->values[1] - 134; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 15) == 0) continue;
        if (acc > 54154) break;
    }
    return acc;
}

static int micro_kernel_135(Store *store, int seed) {
    int acc = seed + 135;
    int pivot = (seed ^ 2298) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 135) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 135; break;
            case 1: acc -= node->values[1] - 135; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 16) == 0) continue;
        if (acc > 54185) break;
    }
    return acc;
}

static int micro_kernel_136(Store *store, int seed) {
    int acc = seed + 136;
    int pivot = (seed ^ 2315) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 136) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 136; break;
            case 1: acc -= node->values[1] - 136; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 17) == 0) continue;
        if (acc > 54216) break;
    }
    return acc;
}

static int micro_kernel_137(Store *store, int seed) {
    int acc = seed + 137;
    int pivot = (seed ^ 2332) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 137) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 137; break;
            case 1: acc -= node->values[1] - 137; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 18) == 0) continue;
        if (acc > 54247) break;
    }
    return acc;
}

static int micro_kernel_138(Store *store, int seed) {
    int acc = seed + 138;
    int pivot = (seed ^ 2349) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 138) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 138; break;
            case 1: acc -= node->values[1] - 138; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 19) == 0) continue;
        if (acc > 54278) break;
    }
    return acc;
}

static int micro_kernel_139(Store *store, int seed) {
    int acc = seed + 139;
    int pivot = (seed ^ 2366) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 139) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 139; break;
            case 1: acc -= node->values[1] - 139; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 20) == 0) continue;
        if (acc > 54309) break;
    }
    return acc;
}

static int micro_kernel_140(Store *store, int seed) {
    int acc = seed + 140;
    int pivot = (seed ^ 2383) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 140) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 140; break;
            case 1: acc -= node->values[1] - 140; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 21) == 0) continue;
        if (acc > 54340) break;
    }
    return acc;
}

static int micro_kernel_141(Store *store, int seed) {
    int acc = seed + 141;
    int pivot = (seed ^ 2400) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 141) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 141; break;
            case 1: acc -= node->values[1] - 141; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 22) == 0) continue;
        if (acc > 54371) break;
    }
    return acc;
}

static int micro_kernel_142(Store *store, int seed) {
    int acc = seed + 142;
    int pivot = (seed ^ 2417) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 142) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 142; break;
            case 1: acc -= node->values[1] - 142; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 23) == 0) continue;
        if (acc > 54402) break;
    }
    return acc;
}

static int micro_kernel_143(Store *store, int seed) {
    int acc = seed + 143;
    int pivot = (seed ^ 2434) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 143) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 143; break;
            case 1: acc -= node->values[1] - 143; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 54433) break;
    }
    return acc;
}

static int micro_kernel_144(Store *store, int seed) {
    int acc = seed + 144;
    int pivot = (seed ^ 2451) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 144) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 144; break;
            case 1: acc -= node->values[1] - 144; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 54464) break;
    }
    return acc;
}

static int micro_kernel_145(Store *store, int seed) {
    int acc = seed + 145;
    int pivot = (seed ^ 2468) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 145) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 145; break;
            case 1: acc -= node->values[1] - 145; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 54495) break;
    }
    return acc;
}

static int micro_kernel_146(Store *store, int seed) {
    int acc = seed + 146;
    int pivot = (seed ^ 2485) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 146) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 146; break;
            case 1: acc -= node->values[1] - 146; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 54526) break;
    }
    return acc;
}

static int micro_kernel_147(Store *store, int seed) {
    int acc = seed + 147;
    int pivot = (seed ^ 2502) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 147) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 147; break;
            case 1: acc -= node->values[1] - 147; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 15) == 0) continue;
        if (acc > 54557) break;
    }
    return acc;
}

static int micro_kernel_148(Store *store, int seed) {
    int acc = seed + 148;
    int pivot = (seed ^ 2519) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 148) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 148; break;
            case 1: acc -= node->values[1] - 148; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 16) == 0) continue;
        if (acc > 54588) break;
    }
    return acc;
}

static int micro_kernel_149(Store *store, int seed) {
    int acc = seed + 149;
    int pivot = (seed ^ 2536) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 149) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 149; break;
            case 1: acc -= node->values[1] - 149; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 17) == 0) continue;
        if (acc > 54619) break;
    }
    return acc;
}

static int micro_kernel_150(Store *store, int seed) {
    int acc = seed + 150;
    int pivot = (seed ^ 2553) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 150) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 150; break;
            case 1: acc -= node->values[1] - 150; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 18) == 0) continue;
        if (acc > 54650) break;
    }
    return acc;
}

static int micro_kernel_151(Store *store, int seed) {
    int acc = seed + 151;
    int pivot = (seed ^ 2570) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 151) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 151; break;
            case 1: acc -= node->values[1] - 151; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 19) == 0) continue;
        if (acc > 54681) break;
    }
    return acc;
}

static int micro_kernel_152(Store *store, int seed) {
    int acc = seed + 152;
    int pivot = (seed ^ 2587) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 152) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 0) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 152; break;
            case 1: acc -= node->values[1] - 152; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 20) == 0) continue;
        if (acc > 54712) break;
    }
    return acc;
}

static int micro_kernel_153(Store *store, int seed) {
    int acc = seed + 153;
    int pivot = (seed ^ 2604) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 153) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 1) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 153; break;
            case 1: acc -= node->values[1] - 153; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 21) == 0) continue;
        if (acc > 54743) break;
    }
    return acc;
}

static int micro_kernel_154(Store *store, int seed) {
    int acc = seed + 154;
    int pivot = (seed ^ 2621) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 154) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 2) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 154; break;
            case 1: acc -= node->values[1] - 154; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 22) == 0) continue;
        if (acc > 54774) break;
    }
    return acc;
}

static int micro_kernel_155(Store *store, int seed) {
    int acc = seed + 155;
    int pivot = (seed ^ 2638) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 155) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 3) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 155; break;
            case 1: acc -= node->values[1] - 155; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 23) == 0) continue;
        if (acc > 54805) break;
    }
    return acc;
}

static int micro_kernel_156(Store *store, int seed) {
    int acc = seed + 156;
    int pivot = (seed ^ 2655) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 156) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 4) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 156; break;
            case 1: acc -= node->values[1] - 156; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 11) == 0) continue;
        if (acc > 54836) break;
    }
    return acc;
}

static int micro_kernel_157(Store *store, int seed) {
    int acc = seed + 157;
    int pivot = (seed ^ 2672) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 157) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 5) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 157; break;
            case 1: acc -= node->values[1] - 157; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 12) == 0) continue;
        if (acc > 54867) break;
    }
    return acc;
}

static int micro_kernel_158(Store *store, int seed) {
    int acc = seed + 158;
    int pivot = (seed ^ 2689) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 158) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 6) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 158; break;
            case 1: acc -= node->values[1] - 158; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 13) == 0) continue;
        if (acc > 54898) break;
    }
    return acc;
}

static int micro_kernel_159(Store *store, int seed) {
    int acc = seed + 159;
    int pivot = (seed ^ 2706) & 15;
    for (int i = 0; i < NODE_COUNT; i++) {
        Node *node = &store->nodes[i];
        int local = node->values[(i + pivot) % VALUE_COUNT];
        if (((local + i + 159) & 3) == 0) {
            acc += local + node->id;
        } else if (((local ^ acc) & 7) == 7) {
            acc ^= node->meta.code;
        } else {
            acc -= node->pos.x - node->pos.y;
        }
        switch ((i + pivot) & 7) {
            case 0: acc += node->values[0] + 159; break;
            case 1: acc -= node->values[1] - 159; break;
            case 2: acc ^= node->values[2]; break;
            case 3: acc += (int)(node->score & 0xff); break;
            case 4: acc -= (int)(node->meta.weight & 0x7f); break;
            case 5: acc += abs_i(node->pos.z); break;
            case 6: acc ^= recursive_mix(2, node->id); break;
            default: acc += node->meta.flags; break;
        }
        if ((acc % 14) == 0) continue;
        if (acc > 54929) break;
    }
    return acc;
}

typedef int (*KernelFn)(Store *store, int seed);
static KernelFn kernel_table[160] = {
    micro_kernel_000,
    micro_kernel_001,
    micro_kernel_002,
    micro_kernel_003,
    micro_kernel_004,
    micro_kernel_005,
    micro_kernel_006,
    micro_kernel_007,
    micro_kernel_008,
    micro_kernel_009,
    micro_kernel_010,
    micro_kernel_011,
    micro_kernel_012,
    micro_kernel_013,
    micro_kernel_014,
    micro_kernel_015,
    micro_kernel_016,
    micro_kernel_017,
    micro_kernel_018,
    micro_kernel_019,
    micro_kernel_020,
    micro_kernel_021,
    micro_kernel_022,
    micro_kernel_023,
    micro_kernel_024,
    micro_kernel_025,
    micro_kernel_026,
    micro_kernel_027,
    micro_kernel_028,
    micro_kernel_029,
    micro_kernel_030,
    micro_kernel_031,
    micro_kernel_032,
    micro_kernel_033,
    micro_kernel_034,
    micro_kernel_035,
    micro_kernel_036,
    micro_kernel_037,
    micro_kernel_038,
    micro_kernel_039,
    micro_kernel_040,
    micro_kernel_041,
    micro_kernel_042,
    micro_kernel_043,
    micro_kernel_044,
    micro_kernel_045,
    micro_kernel_046,
    micro_kernel_047,
    micro_kernel_048,
    micro_kernel_049,
    micro_kernel_050,
    micro_kernel_051,
    micro_kernel_052,
    micro_kernel_053,
    micro_kernel_054,
    micro_kernel_055,
    micro_kernel_056,
    micro_kernel_057,
    micro_kernel_058,
    micro_kernel_059,
    micro_kernel_060,
    micro_kernel_061,
    micro_kernel_062,
    micro_kernel_063,
    micro_kernel_064,
    micro_kernel_065,
    micro_kernel_066,
    micro_kernel_067,
    micro_kernel_068,
    micro_kernel_069,
    micro_kernel_070,
    micro_kernel_071,
    micro_kernel_072,
    micro_kernel_073,
    micro_kernel_074,
    micro_kernel_075,
    micro_kernel_076,
    micro_kernel_077,
    micro_kernel_078,
    micro_kernel_079,
    micro_kernel_080,
    micro_kernel_081,
    micro_kernel_082,
    micro_kernel_083,
    micro_kernel_084,
    micro_kernel_085,
    micro_kernel_086,
    micro_kernel_087,
    micro_kernel_088,
    micro_kernel_089,
    micro_kernel_090,
    micro_kernel_091,
    micro_kernel_092,
    micro_kernel_093,
    micro_kernel_094,
    micro_kernel_095,
    micro_kernel_096,
    micro_kernel_097,
    micro_kernel_098,
    micro_kernel_099,
    micro_kernel_100,
    micro_kernel_101,
    micro_kernel_102,
    micro_kernel_103,
    micro_kernel_104,
    micro_kernel_105,
    micro_kernel_106,
    micro_kernel_107,
    micro_kernel_108,
    micro_kernel_109,
    micro_kernel_110,
    micro_kernel_111,
    micro_kernel_112,
    micro_kernel_113,
    micro_kernel_114,
    micro_kernel_115,
    micro_kernel_116,
    micro_kernel_117,
    micro_kernel_118,
    micro_kernel_119,
    micro_kernel_120,
    micro_kernel_121,
    micro_kernel_122,
    micro_kernel_123,
    micro_kernel_124,
    micro_kernel_125,
    micro_kernel_126,
    micro_kernel_127,
    micro_kernel_128,
    micro_kernel_129,
    micro_kernel_130,
    micro_kernel_131,
    micro_kernel_132,
    micro_kernel_133,
    micro_kernel_134,
    micro_kernel_135,
    micro_kernel_136,
    micro_kernel_137,
    micro_kernel_138,
    micro_kernel_139,
    micro_kernel_140,
    micro_kernel_141,
    micro_kernel_142,
    micro_kernel_143,
    micro_kernel_144,
    micro_kernel_145,
    micro_kernel_146,
    micro_kernel_147,
    micro_kernel_148,
    micro_kernel_149,
    micro_kernel_150,
    micro_kernel_151,
    micro_kernel_152,
    micro_kernel_153,
    micro_kernel_154,
    micro_kernel_155,
    micro_kernel_156,
    micro_kernel_157,
    micro_kernel_158,
    micro_kernel_159
};

static long run_kernel_table(Store *store, int seed) {
    long acc = seed;
    for (int i = 0; i < 160; i++) {
        KernelFn fn = kernel_table[i];
        int v = fn(store, seed + i);
        if ((v & 1) == 0) acc += v;
        else acc -= v;
        if ((i % 17) == 0) acc ^= pointer_chase(store, (i % 5) + 1);
    }
    return acc;
}

static long final_mix(Store *store, int seed) {
    long acc = scan_store(store, seed);
    acc += matrix_walk(store, seed + 11);
    acc ^= history_fold(store, seed + 23);
    acc += pointer_chase(store, 3);
    acc ^= run_kernel_table(store, seed + 37);
    for (int i = 0; i < store->count; i++) {
        Node *node = &store->nodes[i];
        acc += node->score;
        acc ^= node->meta.weight;
        acc += node->values[i % VALUE_COUNT];
    }
    return acc;
}

int main(void) {
    Store store;
    init_store(&store, 1337);
    long result = final_mix(&store, 9001);
    printf("hephaestus_2k_torture result=%ld checksum=%ld count=%d mode=%d\n",
           result, store.checksum, store.count, (int)store.mode);
    return (int)(result & 0xff);
}
