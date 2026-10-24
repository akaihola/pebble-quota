#pragma once

// Row freshness and gauge layout rules. Pebble-free so a host test can compile
// them; watchface.c only draws the resulting plan.

#include <stdbool.h>
#include <stddef.h>
#include <time.h>

#define MAX_ROWS 5
#define MAX_GAUGES (MAX_ROWS + 2)  // rows plus one line per unavailable provider

// A healthy cycle delivers a reading within about 21 minutes: 300 s collector
// wait plus up to ~37 s of work, a 900 s phone poll and a 15 s request timeout.
#define FRESH_SECONDS (25 * 60)
// Readings this far ahead of the watch clock count as age zero.
#define FUTURE_SKEW_SECONDS (5 * 60)

typedef struct {
  char service[2];
  char window[8];
  int used;
  time_t resets_at;
  int duration;
  time_t observed_at;  // the provider reading behind this row
  bool failed;         // the provider's latest attempt failed; the row is retained
} QuotaRow;

typedef enum {
  ROW_GREEN,        // fresh, pace surplus zero or more
  ROW_YELLOW,       // fresh, -10 through -1 points
  ROW_RED,          // fresh, below -10 points
  ROW_STALE,        // old, retained after a failure, or from the future
  ROW_EXPIRED,      // the window has reset since the reading
  ROW_UNAVAILABLE,  // the provider has no rows
} RowState;

typedef struct {
  char title[24];
  char status[24];        // right-aligned title-row text; may be empty
  const QuotaRow *rows[2];  // rows[1] for Claude+Fable; both NULL when unavailable
  RowState states[2];
  int elapsed;            // marker position, percent of rows[0]'s window
  bool marker;
} Gauge;

int elapsed_percent(const QuotaRow *row, time_t now);
RowState row_state(const QuotaRow *row, int elapsed, time_t now);
int plan_gauges(const QuotaRow *rows, int row_count, const char *unavailable,
                time_t collected_at, time_t now, Gauge *gauges);
bool show_temperature(bool has_temp, time_t collected_at, time_t now);
