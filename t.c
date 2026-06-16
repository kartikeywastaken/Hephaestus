
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

typedef uint64_t (*binop_fn)(uint64_t, uint64_t);
typedef uint64_t (*triop_fn)(uint64_t, uint64_t, uint64_t);

static volatile uint64_t g_sink = 0;
static volatile uint32_t g_guard = 1;

static uint64_t rotmix(uint64_t x) {
  x ^= x >> 33;
  x *= 0xff51afd7ed558ccdULL;
  x ^= x >> 29;
  x *= 0xc4ceb9fe1a85ec53ULL;
  x ^= x >> 32;
  g_sink ^= x;
  return x;
}

static uint64_t op_add(uint64_t a, uint64_t b) {
  uint64_t x = a + b + 0x1111ULL;
  g_sink ^= x;
  return x;
}

static uint64_t op_xor(uint64_t a, uint64_t b) {
  uint64_t x = (a ^ b) + 0x2222ULL;
  g_sink ^= x;
  return x;
}

static uint64_t op_mul(uint64_t a, uint64_t b) {
  uint64_t x = (a * 33ULL) ^ (b + 0x3333ULL);
  g_sink ^= x;
  return x;
}

static uint64_t op_shift(uint64_t a, uint64_t b) {
  uint64_t x = (a << (b & 7)) ^ (b >> ((a & 3) + 1));
  g_sink ^= x;
  return x;
}

static uint64_t op_div(uint64_t a, uint64_t b) {
  uint64_t d = (b | 1ULL);
  uint64_t x = (a / d) + (a % d) + 0x4444ULL;
  g_sink ^= x;
  return x;
}

static uint64_t op_logic(uint64_t a, uint64_t b) {
  uint64_t x = ((a & b) | (a ^ (b << 2))) + 0x5555ULL;
  g_sink ^= x;
  return x;
}

static binop_fn bin_table[6] = {op_add,   op_xor, op_mul,
                                op_shift, op_div, op_logic};

static uint64_t tri_a(uint64_t a, uint64_t b, uint64_t c) {
  uint64_t acc = a ^ (b << 1) ^ (c >> 1);

  for (int i = 0; i < 32; i++) {
    acc = rotmix(acc + (uint64_t)i);

    if ((acc & 7ULL) == 3ULL) {
      continue;
    }

    if ((acc & 63ULL) == 41ULL) {
      break;
    }

    acc ^= op_add(acc, (uint64_t)i);
  }

  return acc;
}

static uint64_t tri_b(uint64_t a, uint64_t b, uint64_t c) {
  uint64_t acc = a + b + c;

  for (int i = 0; i < 24; i++) {
    uint64_t d = ((uint64_t)i + 1ULL) | 1ULL;
    acc += (acc / d);
    acc ^= (acc % d);

    if ((acc & 15ULL) == 9ULL) {
      continue;
    }

    if ((acc & 255ULL) == 0xa5ULL) {
      break;
    }
  }

  g_sink ^= acc;
  return acc;
}

static uint64_t tri_c(uint64_t a, uint64_t b, uint64_t c) {
  uint64_t acc = a;

  for (int i = 0; i < 16; i++) {
    switch ((acc + b + c + (uint64_t)i) & 7ULL) {
    case 0:
      acc += a ^ (uint64_t)i;
      break;
    case 1:
      acc ^= b + (uint64_t)i * 3ULL;
      break;
    case 2:
      acc -= c + (uint64_t)i * 5ULL;
      break;
    case 3:
      acc = (acc << 5) ^ (acc >> 2);
      break;
    case 4:
      if (acc & 1ULL) {
        acc += 0x12345678ULL;
      } else {
        acc ^= 0x87654321ULL;
      }
      break;
    case 5:
      continue;
    case 6:
      acc += rotmix(acc ^ (uint64_t)i);
      break;
    default:
      acc ^= 0xdeadbeefcafebabeULL;
      break;
    }
  }

  return acc;
}

static triop_fn tri_table[3] = {tri_a, tri_b, tri_c};

static uint64_t abi_pressure(uint64_t a0, uint64_t a1, uint64_t a2, uint64_t a3,
                             uint64_t a4, uint64_t a5, uint64_t a6,
                             uint64_t a7) {
  uint64_t acc = a0 ^ (a1 << 1) ^ (a2 >> 1) ^ a3;

  acc += op_add(a4, a5);
  acc ^= op_xor(a6, a7);
  acc += op_mul(acc, a0);
  acc ^= op_shift(a1, acc);
  acc += op_div(acc + 17ULL, a2 | 1ULL);
  acc ^= op_logic(a3, a4);

  for (uint64_t i = 0; i < 24; i++) {
    acc ^= (a0 + i);
    acc += (a1 ^ (i << 2));
    acc ^= (a2 + a3 + a4 + a5 + a6 + a7);

    if ((acc & 7ULL) == 2ULL) {
      continue;
    }

    if ((acc & 127ULL) == 99ULL) {
      break;
    }
  }

  g_sink ^= acc;
  return acc;
}

static uint64_t stack_layout_pressure(uint64_t seed) {
  uint64_t arr64[40];
  uint32_t arr32[80];
  uint16_t arr16[64];
  uint8_t arr8[128];

  uint64_t acc = seed;

  for (int i = 0; i < 40; i++) {
    arr64[i] = rotmix(acc + (uint64_t)i * 17ULL);
  }

  for (int i = 0; i < 80; i++) {
    arr32[i] = (uint32_t)(acc ^ ((uint64_t)i * 33ULL));
  }

  for (int i = 0; i < 64; i++) {
    arr16[i] = (uint16_t)(acc + (uint64_t)i * 11ULL);
  }

  for (int i = 0; i < 128; i++) {
    arr8[i] = (uint8_t)(acc >> (i & 7));
  }

  for (int r = 0; r < 12; r++) {
    for (int j = 0; j < 40; j++) {
      acc ^= arr64[j];
      acc += arr32[(j * 3 + r) % 80];
      acc ^= arr16[(j * 5 + r) % 64];
      acc += arr8[(j * 7 + r) % 128];

      if ((acc & 3ULL) == 1ULL) {
        continue;
      }

      if ((acc & 0x7ffULL) == 0x321ULL) {
        break;
      }

      acc ^= abi_pressure(acc, seed, arr64[j], arr32[j % 80], arr16[j % 64],
                          arr8[j % 128], (uint64_t)r, (uint64_t)j);
    }
  }

  g_sink ^= acc;
  return acc;
}

static uint64_t indirect_pressure(uint64_t seed) {
  uint64_t acc = seed;

  for (uint64_t i = 0; i < 96; i++) {
    binop_fn fn = bin_table[(acc + i) % 6];
    acc ^= fn(acc, i + seed);

    if ((acc & 0xffULL) == 0x42ULL) {
      break;
    }

    if ((acc & 15ULL) == 5ULL) {
      continue;
    }

    triop_fn tfn = tri_table[(acc >> 3) % 3];
    acc += tfn(acc, seed, i);

    binop_fn fn2 = bin_table[((acc >> 5) + i) % 6];
    acc ^= fn2(acc ^ seed, acc + i);
  }

  g_sink ^= acc;
  return acc;
}

static uint64_t cfg_pressure(uint64_t x, uint64_t y) {
  uint64_t acc = x ^ y;

  for (uint64_t i = 0; i < 80; i++) {
    acc ^= i * 1315423911ULL;

    if ((acc & 15ULL) == 9ULL) {
      continue;
    }

    for (uint64_t j = 0; j < 32; j++) {
      uint64_t selector = (acc + i + j) & 7ULL;

      switch (selector) {
      case 0:
        acc ^= stack_layout_pressure(acc + j);
        break;

      case 1:
        acc += indirect_pressure(acc ^ j);
        break;

      case 2:
        acc ^= abi_pressure(acc, x, y, i, j, acc >> 3, acc << 2, 0xfeedfaceULL);
        break;

      case 3:
        acc = (acc << 3) ^ (acc >> 5) ^ j;
        break;

      case 4:
        if ((acc & 1ULL) != 0ULL) {
          acc += tri_a(acc, x, y);
        } else {
          acc ^= tri_b(acc, y, x);
        }
        break;

      case 5:
        continue;

      case 6:
        acc += tri_c(acc, i, j);
        break;

      default:
        acc ^= 0xabcdef1234567890ULL;
        break;
      }

      if ((acc & 0x3ffULL) == 0x155ULL) {
        break;
      }
    }

    if ((acc & 0xffffULL) == 0xbeefULL) {
      break;
    }
  }

  g_sink ^= acc;
  return acc;
}

static uint64_t byte_halfword_pressure(uint64_t seed) {
  uint8_t bytes[257];
  uint16_t halves[129];
  uint64_t acc = seed;

  for (int i = 0; i < 257; i++) {
    bytes[i] = (uint8_t)((seed + (uint64_t)i * 13ULL) & 0xff);
  }

  for (int i = 0; i < 129; i++) {
    halves[i] = (uint16_t)((seed ^ ((uint64_t)i * 97ULL)) & 0xffff);
  }

  for (int round = 0; round < 64; round++) {
    int bi = (int)((acc + (uint64_t)round * 7ULL) % 257ULL);
    int hi = (int)((acc + (uint64_t)round * 5ULL) % 129ULL);

    int8_t signed_b = (int8_t)bytes[bi];
    uint8_t unsigned_b = bytes[(bi + 17) % 257];
    uint16_t unsigned_h = halves[hi];

    acc += (uint64_t)(int64_t)signed_b;
    acc ^= (uint64_t)unsigned_b;
    acc += (uint64_t)unsigned_h;

    if ((acc & 7ULL) == 6ULL) {
      continue;
    }

    if ((acc & 0xfffULL) == 0xabcULL) {
      break;
    }
  }

  g_sink ^= acc;
  return acc;
}

static uint64_t mixed_driver(uint64_t seed) {
  uint64_t acc = seed;

  for (int round = 0; round < 32; round++) {
    acc ^= cfg_pressure(acc + (uint64_t)round, seed ^ (uint64_t)(round * 17));
    acc += stack_layout_pressure(acc ^ (uint64_t)round);
    acc ^= indirect_pressure(acc + (uint64_t)round * 3ULL);
    acc += abi_pressure(acc, seed, (uint64_t)round, acc >> 1, acc << 1, 11, 22,
                        33);
    acc ^= byte_halfword_pressure(acc + (uint64_t)round);

    if ((acc & 0x1fULL) == 0x12ULL) {
      continue;
    }

    if ((acc & 0xfffULL) == 0x777ULL) {
      break;
    }
  }

  return acc;
}

int main(int argc, char **argv) {
  uint64_t acc = (uint64_t)argc;
  uint64_t argmix = 0;

  if (argv != NULL) {
    for (int i = 0; argv[i] != NULL && i < 8; i++) {
      const char *p = argv[i];
      uint64_t local = 0;

      for (int j = 0; p[j] != '\0'; j++) {
        local = (local * 131ULL) + (uint8_t)p[j];

        if ((local & 7ULL) == 4ULL) {
          continue;
        }
      }

      argmix ^= local;
    }
  }

  for (int i = 0; i < 18; i++) {
    acc ^= mixed_driver(acc + argmix + (uint64_t)i);
    acc += cfg_pressure(acc, argmix ^ (uint64_t)i);
    acc ^= indirect_pressure(acc + (uint64_t)i * 9ULL);
    acc += byte_halfword_pressure(acc ^ (uint64_t)i);
  }

  printf("%llu\n", (unsigned long long)(acc ^ g_sink ^ g_guard));
  return (int)((acc ^ g_sink) & 255ULL);
}
