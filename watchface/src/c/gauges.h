#pragma once

// Message validation, row freshness and gauge layout rules. Pebble-free so a
// host test can compile them; watchface.c only reads tuples and draws the plan.

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <time.h>

#define MAX_ROWS 5
#define MAX_GAUGES MAX_ROWS     // rows and unavailable providers share five lines
#define MAX_UNAVAILABLE 3       // service codes in UNAVAILABLE
#define MAX_WINDOW 7            // window label characters
#define MAX_DURATION_SECONDS 21474836  // keeps duration * 100 within int32

// A healthy cycle delivers a reading within about 21 minutes: 300 s collector
// wait plus up to ~37 s of work, a 900 s phone poll and a 15 s request timeout.
#define FRESH_SECONDS (25 * 60)
// Readings this far ahead of the watch clock count as age zero.
#define FUTURE_SKEW_SECONDS (5 * 60)

typedef struct {
  char service[2];
  char window[MAX_WINDOW + 1];
  int used;
  time_t resets_at;
  int duration;
  time_t observed_at;  // the provider reading behind this row
  bool failed;         // the provider's latest attempt failed; the row is retained
} QuotaRow;

typedef struct {
  time_t collected_at;
  QuotaRow rows[MAX_ROWS];
  int row_count;
  char unavailable[MAX_UNAVAILABLE + 1];  // service codes of providers without rows
  bool has_temp;
  int temp_tenths;  // outside temperature, tenths of degC
} QuotaMessage;

// One AppMessage value as its tuple carried it.
typedef enum { FIELD_MISSING, FIELD_BYTES, FIELD_STRING, FIELD_UINT, FIELD_INT } FieldType;

typedef struct {
  FieldType type;
  uint16_t length;  // bytes, including a string's terminator
  const void *data;
} Field;

// Field order: the message-level keys, then S, W, U, R, D, O, E for each row.
enum { KEY_COLLECTED_AT, KEY_ROW_COUNT, KEY_TEMP, KEY_UNAVAILABLE, KEY_ROWS };
enum { KEY_S, KEY_W, KEY_U, KEY_R, KEY_D, KEY_O, KEY_E, ROW_KEYS };
#define MESSAGE_FIELDS (KEY_ROWS + MAX_ROWS * ROW_KEYS)

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

// Fills out from fields (MESSAGE_FIELDS of them) and returns true only for a
// complete, valid message; out is scratch space otherwise.
bool decode_message(const Field *fields, QuotaMessage *out);
int elapsed_percent(const QuotaRow *row, time_t now);
RowState row_state(const QuotaRow *row, int elapsed, time_t now);
int plan_gauges(const QuotaMessage *quota, time_t now, Gauge *gauges);
bool show_temperature(const QuotaMessage *quota, time_t now);
