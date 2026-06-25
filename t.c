#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct Packet {
  uint32_t flags;
  uint32_t len;
  const char *data;
} Packet;

static uint32_t mix32(uint32_t x) {
  x ^= x >> 16;
  x *= 0x7feb352dU;
  x ^= x >> 15;
  x *= 0x846ca68bU;
  x ^= x >> 16;
  return x;
}

static int score_packet(const Packet *p) {
  uint32_t acc = p->flags ^ p->len;

  for (uint32_t i = 0; i < p->len; i++) {
    acc += (unsigned char)p->data[i];
    acc = mix32(acc);
  }

  if ((p->flags & 1U) && p->len > 4) {
    return (int)(acc & 0xff);
  }

  if (p->len == 0) {
    return -7;
  }

  return -(int)(acc & 0x7f);
}

static int classify(int score) {
  if (score > 100) {
    printf("positive:%d\n", score);
    return score;
  }

  if (score < 0) {
    printf("negative:%d\n", score);
    return -score;
  }

  printf("neutral:%d\n", score);
  return score + 3;
}

int main(int argc, char **argv) {
  const char *input = "default";
  uint32_t flags = 0x2aU;

  if (argc > 1) {
    input = argv[1];
    flags ^= 1U;
  }

  if (argc > 2) {
    flags ^= (uint32_t)strlen(argv[2]);
  }

  Packet p;
  p.flags = flags;
  p.len = (uint32_t)strlen(input);
  p.data = input;

  int score = score_packet(&p);
  int result = classify(score);

  return result & 0xff;
}