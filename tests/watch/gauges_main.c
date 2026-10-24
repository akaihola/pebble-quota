// Host driver for the watch's message and gauge rules. Usage: gauges <now>.
// Stdin holds AppMessages separated by blank lines, one tuple per line:
//   KEY<TAB>TYPE<TAB>VALUE
// KEY is a package.json message key. TYPE is i1, i2, i4 or i8 (u1, u2, u4 for
// unsigned) for an integer tuple of that many bytes, s for a C string, z for one
// without its terminator, or b for a byte array holding VALUE's characters.
// Prints accepted or rejected per message, then, for the last accepted message,
// the temperature decision and one tab-separated line per gauge:
//   title status state0 state1 marker elapsed
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "gauges.h"

static char names[MESSAGE_FIELDS][16];
static unsigned char values[MESSAGE_FIELDS][64];

static const char *state_name(const QuotaRow *row, RowState state) {
  static const char *labels[] = {"green", "yellow", "red", "stale", "expired", "unavailable"};
  return row || state == ROW_UNAVAILABLE ? labels[state] : "-";
}

static bool set_field(Field *fields, char *line) {
  char *type = strchr(line, '\t');
  char *value = type ? strchr(type + 1, '\t') : NULL;
  if (!value) return false;
  *type++ = '\0';
  *value++ = '\0';
  int index = 0;
  while (index < MESSAGE_FIELDS && strcmp(names[index], line) != 0) ++index;
  size_t size = strlen(value);
  if (index == MESSAGE_FIELDS || size >= sizeof(values[0])) return false;
  Field *field = &fields[index];
  field->data = values[index];
  if (type[0] == 'i' || type[0] == 'u') {
    long long number = strtoll(value, NULL, 10);
    field->type = type[0] == 'i' ? FIELD_INT : FIELD_UINT;
    field->length = (uint16_t)atoi(type + 1);
    if (field->length > sizeof(number)) return false;
    memcpy(values[index], &number, field->length);  // little-endian, like the watch
  } else if (strcmp(type, "s") == 0 || strcmp(type, "z") == 0 || strcmp(type, "b") == 0) {
    field->type = type[0] == 'b' ? FIELD_BYTES : FIELD_STRING;
    field->length = (uint16_t)(size + (type[0] == 's'));
    memcpy(values[index], value, size + 1);
  } else {
    return false;
  }
  return true;
}

int main(int argc, char **argv) {
  if (argc != 2) return 2;
  time_t now = atol(argv[1]);
  snprintf(names[KEY_COLLECTED_AT], sizeof(names[0]), "COLLECTED_AT");
  snprintf(names[KEY_ROW_COUNT], sizeof(names[0]), "ROW_COUNT");
  snprintf(names[KEY_TEMP], sizeof(names[0]), "TEMP");
  snprintf(names[KEY_UNAVAILABLE], sizeof(names[0]), "UNAVAILABLE");
  for (int row = 0; row < MAX_ROWS; ++row) {
    for (int key = 0; key < ROW_KEYS; ++key) {
      snprintf(names[KEY_ROWS + row * ROW_KEYS + key], sizeof(names[0]), "%c%d", "SWURDOE"[key], row);
    }
  }
  static QuotaMessage shown, incoming;  // shown starts empty, as on the watch
  Field fields[MESSAGE_FIELDS];
  memset(fields, 0, sizeof(fields));
  bool pending = false;
  char line[256];
  for (;;) {
    bool end = !fgets(line, sizeof(line), stdin);
    if (end || line[0] == '\n') {
      if (pending) {
        bool valid = decode_message(fields, &incoming);
        if (valid) shown = incoming;
        puts(valid ? "accepted" : "rejected");
        memset(fields, 0, sizeof(fields));
        pending = false;
      }
      if (end) break;
      continue;
    }
    line[strcspn(line, "\n")] = '\0';
    if (!set_field(fields, line)) return 2;
    pending = true;
  }
  printf("%s\n", show_temperature(&shown, now) ? "shown" : "hidden");
  Gauge gauges[MAX_GAUGES];
  int planned = plan_gauges(&shown, now, gauges);
  for (int i = 0; i < planned; ++i) {
    const Gauge *gauge = &gauges[i];
    printf("%s\t%s\t%s\t%s\t%d\t%d\n", gauge->title, gauge->status,
           state_name(gauge->rows[0], gauge->states[0]),
           state_name(gauge->rows[1], gauge->states[1]), gauge->marker, gauge->elapsed);
  }
  return 0;
}
