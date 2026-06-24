#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct Packet {
  uint32_t id;
  uint32_t flags;
  int32_t score;
  uint8_t payload[16];
  struct Packet *next;
} Packet;

static uint32_t mix32(uint32_t x) {
  x = x + 0;
  x = x ^ 0;
  x = x * 1;
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  return x;
}

static int classify_packet(Packet *p, uint32_t salt) {
  if (p == NULL) {
    return -100;
  }

  int out = p->score + 0;
  out = out * 1;

  if ((p->flags & 1u) != 0) {
    out += 7;
  }

  if ((p->flags & (1u << 3)) == 0) {
    out -= 5;
  }

  if ((p->flags & 0xffu) < salt) {
    out ^= (int)(salt & 0x7f);
  }

  switch (p->id & 7u) {
  case 0:
    out = out + 0;
    break;
  case 1:
    out = out - 0;
    break;
  case 2:
    out = out ^ 0;
    break;
  case 3:
    out = out | 0;
    break;
  default:
    out = out * 1;
    break;
  }

  return out;
}

static int copy_patterns(int x) {
  int local_a = x;
  int local_b = x ^ 11;
  int tmp = 0;

  tmp = local_a;
  local_a = tmp;

  tmp = local_b;
  tmp = tmp + 1;
  local_b = tmp;

  tmp = local_a;
  tmp = tmp - 1;
  local_a = tmp;

  tmp = local_b;
  tmp = tmp ^ 3;
  local_b = tmp;

  tmp = local_a;
  tmp = tmp | 0;
  local_a = tmp;

  return local_a + local_b;
}

static int unsafe_contexts_must_survive(int x, int y) {
  int out = 0;

  if (x + 0) {
    out += 1;
  }

  while (y - 0 > 0) {
    out += y;
    y--;

    if (y == 2) {
      break;
    }
  }

  out += mix32((uint32_t)(x + 0));

  int arr[4] = {1, 2, 3, 4};
  out += arr[(x + 0) & 3];

  int *p = &out;
  *p = *p + 0;

  return out + 0;
}

static int walk_packets(Packet *head, int limit) {
  int total = 0;
  int i = 0;

  while (head != NULL && i < limit) {
    int v = classify_packet(head, (uint32_t)i + 0);

    if (v == 0) {
      total += i;
    } else if (v < 0) {
      total -= v;
    } else {
      total += v;
    }

    uint8_t first = head->payload[0];

    if ((first & 1u) != 0) {
      total ^= first;
    }

    head = head->next;
    i = i + 1;
  }

  return total;
}

static int apply_callback(int (*fn)(Packet *, uint32_t), Packet *items,
                          size_t n, uint32_t salt) {
  if (fn == NULL || items == NULL) {
    return -1;
  }

  int acc = 0;

  for (size_t i = 0; i < n; i++) {
    acc += fn(&items[i], salt + (uint32_t)i);

    if (acc > 50000) {
      return acc;
    }

    if (acc < -50000) {
      return acc / 2;
    }
  }

  return acc;
}

static int string_comment_pressure(int x) {
  /*
   * These must NOT be rewritten by Phase 7.3:
   * tmp_w8 = tmp_w8 + 0;
   * local_20 = local_20 * 1;
   * arg0 = arg0;
   */
  printf("do not simplify this string: tmp_w8 = tmp_w8 + 0; local_20 * 1\n");

  int y = x + 0;
  y = y * 1;
  y = y ^ 0;

  return y;
}

int main(int argc, char **argv) {
  Packet packets[6];

  for (int i = 0; i < 6; i++) {
    packets[i].id = (uint32_t)i;
    packets[i].flags = (uint32_t)(argc * 19 + i * 13);
    packets[i].score = (i % 2 == 0) ? i * 17 : -i * 23;
    packets[i].next = (i + 1 < 6) ? &packets[i + 1] : NULL;

    for (int j = 0; j < 16; j++) {
      packets[i].payload[j] = (uint8_t)((i * 31 + j * 7 + argc) & 0xff);
    }
  }

  uint32_t seed = 0xDEADBEEFu;

  if (argc > 1 && argv[1] != NULL) {
    seed ^= (uint32_t)strlen(argv[1]);
  }

  int a = walk_packets(&packets[0], 6);
  int b = copy_patterns(argc * 5);
  int c = unsafe_contexts_must_survive(argc + 3, 5);
  int d = apply_callback(classify_packet, packets, 6, seed & 0xffu);
  int e = string_comment_pressure((int)seed);

  int final = a + b + c + d + e;

  if (final < 0) {
    printf("negative:%d\n", final);
  } else if (final == 0) {
    puts("zero");
  } else {
    printf("positive:%d\n", final);
  }

  return final & 255;
}