#include <stdint.h>
#include <stdio.h>
#include <string.h>

static uint32_t checksum(const char *s) {
  uint32_t acc = 5381;

  for (size_t i = 0; s[i] != '\0'; i++) {
    acc = ((acc << 5) + acc) ^ (unsigned char)s[i];
  }

  return acc;
}

int main(int argc, char **argv) {
  const char *input = argc > 1 ? argv[1] : "";

  uint32_t h = checksum(input);

  if ((h & 1) == 0) {
    printf("even:%u\n", h & 255);
  } else {
    printf("odd:%u\n", h & 255);
  }

  return h & 255;
}