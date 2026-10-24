// Host driver for the watch's gauge rules. Arguments mirror one AppMessage:
//   now collected_at has_temp unavailable
// then seven per row: service window used resets_at duration observed failed.
// Prints the temperature decision, then one tab-separated line per gauge:
//   title status state0 state1 marker elapsed
#include <stdio.h>
#include <stdlib.h>

#include "gauges.h"

static const char *state_name(const QuotaRow *row, RowState state) {
  static const char *names[] = {"green", "yellow", "red", "stale", "expired", "unavailable"};
  return row || state == ROW_UNAVAILABLE ? names[state] : "-";
}

int main(int argc, char **argv) {
  if (argc < 5 || (argc - 5) % 7 != 0 || (argc - 5) / 7 > MAX_ROWS) return 2;
  time_t now = atol(argv[1]);
  time_t collected_at = atol(argv[2]);
  QuotaRow rows[MAX_ROWS];
  int count = (argc - 5) / 7;
  for (int i = 0; i < count; ++i) {
    char **field = argv + 5 + i * 7;
    snprintf(rows[i].service, sizeof(rows[i].service), "%s", field[0]);
    snprintf(rows[i].window, sizeof(rows[i].window), "%s", field[1]);
    rows[i].used = atoi(field[2]);
    rows[i].resets_at = atol(field[3]);
    rows[i].duration = atoi(field[4]);
    rows[i].observed_at = atol(field[5]);
    rows[i].failed = atoi(field[6]) != 0;
  }
  printf("%s\n", show_temperature(atoi(argv[3]) != 0, collected_at, now) ? "shown" : "hidden");
  Gauge gauges[MAX_GAUGES];
  int planned = plan_gauges(rows, count, argv[4], collected_at, now, gauges);
  for (int i = 0; i < planned; ++i) {
    const Gauge *gauge = &gauges[i];
    printf("%s\t%s\t%s\t%s\t%d\t%d\n", gauge->title, gauge->status,
           state_name(gauge->rows[0], gauge->states[0]),
           state_name(gauge->rows[1], gauge->states[1]), gauge->marker, gauge->elapsed);
  }
  return 0;
}
