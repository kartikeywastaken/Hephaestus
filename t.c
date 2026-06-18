#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  uint32_t id;
  int32_t score;
  uint8_t flags;
  uint8_t level;
  uint16_t weight;
} Item;

static uint32_t rotl32(uint32_t x, unsigned r) {
  r &= 31;
  return (x << r) | (x >> ((32 - r) & 31));
}

static int mix_score(int a, int b, uint32_t flags) {
  int result = 0;

  if (a == 0) {
    result += 11;
  } else {
    result += a * 3;
  }

  if (b != 0) {
    result -= b * 2;
  } else {
    result += 7;
  }

  if (flags & (1u << 3)) {
    result ^= 0x55;
  }

  if ((flags & (1u << 7)) == 0) {
    result += 19;
  }

  if ((uint32_t)a < flags) {
    result += 5;
  } else {
    result -= 5;
  }

  return result;
}

static int scan_items(Item *items, int n, uint32_t seed) {
  if (items == NULL) {
    return -1000;
  }

  if (n <= 0) {
    return -2000;
  }

  int total = 0;
  int i = 0;
  uint32_t state = seed;

  while (i < n) {
    Item *it = &items[i];

    if (it->id == 0) {
      total -= 3;
      i++;
      continue;
    }

    if (it->flags & 1u) {
      total += it->score;
    } else {
      total -= it->score;
    }

    if (it->flags & (1u << 2)) {
      total += mix_score(it->score, it->level, it->flags);
    }

    if ((it->flags & (1u << 5)) == 0) {
      total += it->weight;
    } else {
      total -= it->weight;
    }

    switch (it->level & 3u) {
    case 0:
      total += 10;
      break;
    case 1:
      total += 20;
      break;
    case 2:
      total -= 30;
      break;
    default:
      total ^= 0x33;
      break;
    }

    state = rotl32(state ^ it->id ^ (uint32_t)total, (unsigned)(it->level + 1));

    if ((state & 0xffu) == 0x42u) {
      break;
    }

    i++;
  }

  return total ^ (int)(state & 0x7fffffff);
}

static int nested_control(int x, int y, int z) {
  int acc = 0;

  for (int i = 0; i < x; i++) {
    int inner = y;

    while (inner > 0) {
      if ((inner & 1) != 0) {
        acc += i ^ inner;
      } else {
        acc -= i + inner;
      }

      if (z != 0 && (acc % z) == 0) {
        acc += z * 3;
      }

      if (acc > 5000) {
        return acc;
      }

      inner--;
    }
  }

  return acc;
}

static int pointer_walk(uint8_t *buf, size_t len, uint8_t key) {
  if (!buf) {
    return -1;
  }

  int hits = 0;
  size_t i = 0;

  while (i < len) {
    uint8_t v = buf[i];

    if (v == key) {
      hits++;
    }

    if ((v & 0x80u) != 0) {
      hits += 2;
    }

    if ((v & 0x08u) == 0) {
      hits--;
    }

    if (i + 3 < len) {
      uint32_t chunk = ((uint32_t)buf[i] << 24) | ((uint32_t)buf[i + 1] << 16) |
                       ((uint32_t)buf[i + 2] << 8) | ((uint32_t)buf[i + 3]);

      if ((chunk ^ 0xA5A5A5A5u) < 0x01000000u) {
        hits += 9;
      }
    }

    i++;
  }

  return hits;
}

int main(int argc, char **argv) {
  uint32_t seed = 0x12345678u;

  if (argc > 1) {
    seed ^= (uint32_t)strlen(argv[1]);
  }

  Item items[8];

  for (int i = 0; i < 8; i++) {
    items[i].id = (uint32_t)(i * 17 + 3);
    items[i].score = (i % 2 == 0) ? i * 11 : -i * 7;
    items[i].flags = (uint8_t)((i * 29) ^ seed);
    items[i].level = (uint8_t)(i & 7);
    items[i].weight = (uint16_t)(100 + i * 13);
  }

  items[3].id = 0;
  items[5].flags |= (1u << 5);

  uint8_t buffer[16];

  for (int i = 0; i < 16; i++) {
    buffer[i] = (uint8_t)((seed >> (i % 8)) ^ (i * 31));
  }

  int a = scan_items(items, 8, seed);
  int b = nested_control(5, 7, 3);
  int c = pointer_walk(buffer, sizeof(buffer), buffer[2]);

  int final = a + b + c;

  if (final == 0) {
    puts("zero");
  } else if (final < 0) {
    printf("negative:%d\n", final);
  } else {
    printf("positive:%d\n", final);
  }

  return final & 255;
}