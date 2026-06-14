
#include <stdint.h>
#include <stdio.h>

#define ITEM_COUNT 7
#define VALUE_COUNT 5
#define HISTORY_COUNT 4

typedef struct {
  int x;
  int y;
} Point;

typedef struct {
  uint8_t tag;
  int code;
  long weight;
} Meta;

typedef struct {
  int id;
  long score;
  char flag;
  int values[VALUE_COUNT];
  Point pos;
  Meta meta;
} Item;

typedef struct {
  Item items[ITEM_COUNT];
  int count;
  long checksum;
  char state;
  int history[HISTORY_COUNT];
} Store;

typedef int (*ScoreFn)(Item *item, int bias);

static int abs_i(int x) {
  if (x < 0) {
    return -x;
  }
  return x;
}

int recursive_fold(int n) {
  if (n <= 0) {
    return 1;
  }

  if (n == 1) {
    return 2;
  }

  if ((n & 1) == 0) {
    return n + recursive_fold(n - 2);
  }

  return n + recursive_fold(n - 1);
}

void init_item(Item *item, int seed) {
  item->id = seed;
  item->score = seed * 111L + 17;
  item->flag = (char)(seed % 6);
  item->pos.x = seed * 3;
  item->pos.y = seed - 4;
  item->meta.tag = (uint8_t)(seed + 1);
  item->meta.code = seed * 10;
  item->meta.weight = seed * 1000L + 33;

  for (int i = 0; i < VALUE_COUNT; i++) {
    item->values[i] = seed + i;
  }

  if (seed == 3) {
    item->values[2] = -seed;
  }

  if (seed == 5) {
    item->flag = 9;
  }
}

void init_store(Store *store) {
  store->count = ITEM_COUNT;
  store->checksum = 0;
  store->state = 'S';

  for (int i = 0; i < HISTORY_COUNT; i++) {
    store->history[i] = i * 7;
  }

  for (int i = 0; i < ITEM_COUNT; i++) {
    init_item(&store->items[i], i + 1);
  }
}

int score_basic(Item *item, int bias) {
  int total = bias;

  total += item->id;
  total += (int)(item->score % 101);
  total += item->flag;
  total += item->pos.x;
  total -= item->pos.y;
  total += item->meta.tag;
  total += item->meta.code;
  total += (int)(item->meta.weight % 97);

  for (int i = 0; i < VALUE_COUNT; i++) {
    total += item->values[i];
  }

  return total;
}

int score_weird(Item *item, int bias) {
  int total = bias;

  for (int i = VALUE_COUNT - 1; i >= 0; i--) {
    int v = item->values[i];

    if (v == 0) {
      continue;
    }

    if (v < 0) {
      total += abs_i(v) * (i + 1);
    } else {
      total += v - i;
    }
  }

  if (item->flag & 1) {
    total += item->id * 3;
  } else {
    total -= item->id;
  }

  total += (int)(item->score & 0xff);
  total += item->meta.code;
  return total;
}

int classify_item(Item *item) {
  int out = 0;

  switch (item->flag) {
  case 0:
    out = item->id + 10;
    break;
  case 1:
    out = item->values[0] + 20;
    break;
  case 2:
    out = item->values[1] + 30;
    break;
  case 3:
    out = item->pos.x + 40;
    break;
  case 4:
    out = item->pos.y + 50;
    break;
  case 5:
    out = item->meta.code + 60;
    break;
  default:
    out = (int)(item->score % 100);
    break;
  }

  return out;
}

int process_one(Item *item, ScoreFn fn, int bias) {
  int score = fn(item, bias);
  int bucket = classify_item(item);

  if (score > 250) {
    score -= recursive_fold(item->id);
  } else if (score < 80) {
    score += recursive_fold(item->flag);
  } else {
    score += bucket;
  }

  return score;
}

void mutate_alias(Item *a, Item *b) {
  a->values[0] += 1;
  b->values[1] += 2;

  if (a == b) {
    a->score += 5;
    a->meta.weight += 11;
    return;
  }

  if (a->id < b->id) {
    a->pos.x += b->pos.y;
    b->pos.y -= a->flag;
    a->meta.code += b->meta.tag;
  } else {
    b->pos.x += a->pos.y;
    a->pos.y -= b->flag;
    b->meta.code += a->meta.tag;
  }
}

long update_checksum(Store *store) {
  long acc = 0;

  for (int i = 0; i < store->count; i++) {
    Item *item = &store->items[i];

    acc += item->id;
    acc += item->score;
    acc += item->flag;
    acc += item->pos.x;
    acc += item->pos.y;
    acc += item->meta.tag;
    acc += item->meta.code;
    acc += item->meta.weight;

    for (int j = 0; j < VALUE_COUNT; j++) {
      acc += item->values[j];
    }
  }

  for (int k = 0; k < HISTORY_COUNT; k++) {
    acc += store->history[k];
  }

  store->checksum = acc;
  return acc;
}

int scan_store(Store *store, int limit) {
  int result = 0;

  for (int i = 0; i < store->count; i++) {
    Item *item = &store->items[i];

    if (item->id == 2) {
      continue;
    }

    if (item->id > limit) {
      break;
    }

    ScoreFn fn;

    if (item->flag & 1) {
      fn = score_weird;
    } else {
      fn = score_basic;
    }

    result += process_one(item, fn, i * 5);

    if (result > 700) {
      result -= classify_item(item);
    }
  }

  return result;
}

long pointer_walk(Store *store) {
  long total = 0;
  Item *begin = &store->items[0];
  Item *end = &store->items[store->count];

  for (Item *p = begin; p < end; p++) {
    total += p->id;
    total += p->score;
    total += p->meta.weight;

    if (p->flag == 9) {
      total += p->values[VALUE_COUNT - 1];
    }
  }

  return total;
}

int nested_branches(Store *store) {
  int out = 0;

  for (int i = 0; i < store->count; i++) {
    Item *item = &store->items[i];

    if (item->flag == 0) {
      out += item->id;
    } else if (item->flag == 1) {
      if (item->values[0] > 3) {
        out += item->values[0];
      } else {
        out -= item->values[1];
      }
    } else if (item->flag == 2) {
      for (int j = 0; j < VALUE_COUNT; j++) {
        if (j == 2) {
          continue;
        }
        out += item->values[j];
      }
    } else if (item->flag == 3) {
      int local = 0;
      for (int j = 0; j < HISTORY_COUNT; j++) {
        local += store->history[j];
      }
      out += local;
    } else {
      out += classify_item(item);
    }
  }

  return out;
}

int mixed_memory_sizes(Store *store) {
  int total = 0;

  for (int i = 0; i < store->count; i++) {
    Item *item = &store->items[i];

    total += item->id;
    total += item->flag;
    total += item->meta.tag;
    total += item->meta.code;
    total += (int)(item->meta.weight % 13);
  }

  return total;
}

int dispatch_score(Store *store, int mode) {
  int result = 0;

  switch (mode) {
  case 0:
    result = scan_store(store, 6);
    break;
  case 1:
    result = nested_branches(store);
    break;
  case 2:
    result = mixed_memory_sizes(store);
    break;
  case 3:
    result = (int)(pointer_walk(store) % 1000);
    break;
  default:
    result = recursive_fold(mode);
    break;
  }

  return result;
}

int main(void) {
  Store store;
  init_store(&store);

  mutate_alias(&store.items[0], &store.items[1]);
  mutate_alias(&store.items[2], &store.items[2]);
  mutate_alias(&store.items[3], &store.items[5]);

  long checksum = update_checksum(&store);
  int scan = scan_store(&store, 6);
  long walk = pointer_walk(&store);
  int branches = nested_branches(&store);
  int mixed = mixed_memory_sizes(&store);
  int dispatch0 = dispatch_score(&store, 0);
  int dispatch1 = dispatch_score(&store, 1);
  int dispatch2 = dispatch_score(&store, 2);
  int dispatch9 = dispatch_score(&store, 9);

  printf("checksum=%ld\n", checksum);
  printf("scan=%d\n", scan);
  printf("walk=%ld\n", walk);
  printf("branches=%d\n", branches);
  printf("mixed=%d\n", mixed);
  printf("dispatch=%d,%d,%d,%d\n", dispatch0, dispatch1, dispatch2, dispatch9);

  if (scan > branches) {
    printf("scan-heavy %d\n", scan - branches);
  } else if (branches > mixed) {
    printf("branch-heavy %d\n", branches - mixed);
  } else {
    printf("mixed-heavy %d\n", mixed - scan);
  }

  return 0;
}
