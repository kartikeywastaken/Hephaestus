#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct Node {
  int32_t value;
  uint32_t flags;
  struct Node *next;
} Node;

typedef struct Context {
  Node *head;
  uint32_t seed;
  int32_t bias;
  uint8_t table[32];
} Context;

static uint32_t scramble(uint32_t x) {
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  return x;
}

static int recursive_sum(Node *n, int depth) {
  if (n == NULL) {
    return 0;
  }

  if (depth <= 0) {
    return n->value;
  }

  int base = n->value;

  if ((n->flags & (1u << 2)) != 0) {
    base += 7;
  }

  if ((n->flags & (1u << 5)) == 0) {
    base -= 3;
  }

  return base + recursive_sum(n->next, depth - 1);
}

static int odd_path(int x);

static int even_path(int x) {
  if (x <= 0) {
    return 1;
  }

  if ((x & 1) != 0) {
    return odd_path(x - 1) + x;
  }

  return even_path(x - 2) + 2;
}

static int odd_path(int x) {
  if (x <= 1) {
    return x + 3;
  }

  if ((x & 2) != 0) {
    return even_path(x - 1) - x;
  }

  return odd_path(x - 2) + 1;
}

static int classify_value(int x, uint32_t flags) {
  int out = 0;

  switch ((unsigned)x & 7u) {
  case 0:
    out = x + 10;
    break;
  case 1:
    out = x - 11;
    break;
  case 2:
  case 3:
    out = x ^ 0x55;
    break;
  case 4:
    out = -x;
    break;
  default:
    out = x * 3;
    break;
  }

  if (flags == 0) {
    out += 100;
  }

  if (flags != 0) {
    out -= 9;
  }

  if ((flags & 0xffu) < (uint32_t)x) {
    out += 5;
  }

  if ((flags & (1u << 31)) != 0) {
    out ^= 0x7f;
  }

  return out;
}

static int table_walk(Context *ctx, int limit) {
  if (ctx == NULL) {
    return -100;
  }

  if (limit < 0) {
    return -200;
  }

  int total = 0;
  uint32_t state = ctx->seed;

  for (int i = 0; i < limit && i < 32; i++) {
    uint8_t v = ctx->table[i];

    if (v == 0) {
      total += i;
      continue;
    }

    if ((v & 1u) != 0) {
      total += v;
    } else {
      total -= v;
    }

    if ((v & 8u) == 0) {
      total ^= i * 3;
    }

    state = scramble(state ^ v ^ (uint32_t)i);

    if ((state & 0xffffu) == 0xbeefu) {
      break;
    }
  }

  return total + (int)(state & 0x3ffu);
}

static int apply_callback(int (*fn)(int, uint32_t), int *values, size_t n,
                          uint32_t flags) {
  if (fn == NULL || values == NULL) {
    return -1;
  }

  int acc = 0;

  for (size_t i = 0; i < n; i++) {
    int v = values[i];

    if ((unsigned)v > flags) {
      acc += fn(v, flags);
    } else {
      acc -= fn(v + 1, flags ^ (uint32_t)i);
    }

    if (acc > 10000) {
      return acc;
    }

    if (acc < -10000) {
      return acc / 2;
    }
  }

  return acc;
}

static int pointer_churn(uint8_t *buf, size_t len) {
  if (!buf) {
    return -9;
  }

  int score = 0;
  uint8_t *p = buf;
  uint8_t *end = buf + len;

  while (p < end) {
    uint8_t v = *p;

    if ((v & 0x80u) != 0) {
      score += 4;
    }

    if ((v & 0x10u) == 0) {
      score -= 2;
    }

    if ((size_t)(end - p) >= 4) {
      uint32_t word = ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
                      ((uint32_t)p[2] << 8) | ((uint32_t)p[3]);

      if ((word ^ 0x41424344u) == 0) {
        score += 100;
      }
    }

    p++;
  }

  return score;
}

int main(int argc, char **argv) {
  Node nodes[6];

  for (int i = 0; i < 6; i++) {
    nodes[i].value = (i % 2 == 0) ? i * 13 : -i * 17;
    nodes[i].flags = (uint32_t)(i * 37 + argc);
    nodes[i].next = (i + 1 < 6) ? &nodes[i + 1] : NULL;
  }

  Context ctx;
  ctx.head = &nodes[0];
  ctx.seed = 0xC001D00Du ^ (uint32_t)argc;
  ctx.bias = argc * 3;

  for (int i = 0; i < 32; i++) {
    ctx.table[i] = (uint8_t)((i * 11) ^ (ctx.seed >> (i & 7)));
  }

  if (argc > 1 && argv[1] != NULL) {
    ctx.seed ^= (uint32_t)strlen(argv[1]);
  }

  int values[10];

  for (int i = 0; i < 10; i++) {
    values[i] = (int)((ctx.seed >> (i & 15)) & 0xff) - 100;
  }

  uint8_t bytes[20];

  for (int i = 0; i < 20; i++) {
    bytes[i] = (uint8_t)(values[i % 10] + i * 7);
  }

  int a = recursive_sum(ctx.head, 5);
  int b = even_path(9);
  int c = table_walk(&ctx, 32);
  int d = apply_callback(classify_value, values, 10, ctx.seed & 0xffu);
  int e = pointer_churn(bytes, sizeof(bytes));

  int final = a + b + c + d + e + ctx.bias;

  if (final == 0) {
    puts("zero");
  } else if (final < 0) {
    printf("negative:%d\n", final);
  } else {
    printf("positive:%d\n", final);
  }

  return final & 255;
}