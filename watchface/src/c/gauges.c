#include "gauges.h"

#include <stdio.h>
#include <string.h>

// Integers may arrive as signed or unsigned tuples of 1, 2 or 4 bytes.
static bool field_int(const Field *field, int32_t low, int32_t high, int32_t *out) {
  union { int8_t i8; uint8_t u8; int16_t i16; uint16_t u16; int32_t i32; uint32_t u32; } value;
  if ((field->type != FIELD_INT && field->type != FIELD_UINT)
      || (field->length != 1 && field->length != 2 && field->length != 4)) {
    return false;
  }
  memcpy(&value, field->data, field->length);
  bool is_signed = field->type == FIELD_INT;
  int64_t number = field->length == 1 ? (is_signed ? value.i8 : value.u8)
                 : field->length == 2 ? (is_signed ? value.i16 : value.u16)
                 : (is_signed ? value.i32 : (int64_t)value.u32);
  if (number < low || number > high) return false;
  *out = (int32_t)number;
  return true;
}

// A terminated string of min to max characters, each from low to high.
static bool field_string(const Field *field, size_t min, size_t max, char low, char high,
                         char *out) {
  if (field->type != FIELD_STRING || field->length == 0) return false;
  const char *text = field->data;
  const char *end = memchr(text, '\0', field->length);
  if (!end) return false;
  size_t length = (size_t)(end - text);
  if (length < min || length > max) return false;
  for (size_t i = 0; i < length; ++i) {
    if (text[i] < low || text[i] > high) return false;
    out[i] = text[i];
  }
  out[length] = '\0';
  return true;
}

bool decode_message(const Field *fields, QuotaMessage *out) {
  memset(out, 0, sizeof(*out));
  int32_t value;
  if (!field_int(&fields[KEY_COLLECTED_AT], 0, INT32_MAX, &value)) return false;
  out->collected_at = value;
  if (!field_int(&fields[KEY_ROW_COUNT], 0, MAX_ROWS, &value)) return false;
  out->row_count = value;
  if (!field_string(&fields[KEY_UNAVAILABLE], 0, MAX_UNAVAILABLE, 'A', 'Z', out->unavailable)
      || out->row_count + (int)strlen(out->unavailable) > MAX_GAUGES) {
    return false;
  }
  out->has_temp = fields[KEY_TEMP].type != FIELD_MISSING;
  if (out->has_temp) {
    if (!field_int(&fields[KEY_TEMP], INT32_MIN, INT32_MAX, &value)) return false;
    out->temp_tenths = value;
  }
  for (int i = 0; i < out->row_count; ++i) {
    const Field *field = &fields[KEY_ROWS + i * ROW_KEYS];
    QuotaRow *row = &out->rows[i];
    int32_t used, resets_at, duration, observed_at, failed;
    if (!field_string(&field[KEY_S], 1, 1, 'A', 'Z', row->service)
        || !field_string(&field[KEY_W], 1, MAX_WINDOW, ' ', '~', row->window)
        || !field_int(&field[KEY_U], 0, 100, &used)
        || !field_int(&field[KEY_R], 0, INT32_MAX, &resets_at)
        || !field_int(&field[KEY_D], 1, MAX_DURATION_SECONDS, &duration)
        || !field_int(&field[KEY_O], 0, INT32_MAX, &observed_at)
        || !field_int(&field[KEY_E], 0, 1, &failed)) {
      return false;
    }
    row->used = used;
    row->resets_at = resets_at;
    row->duration = duration;
    row->observed_at = observed_at;
    row->failed = failed != 0;
  }
  return true;
}

int elapsed_percent(const QuotaRow *row, time_t now) {
  if (row->duration <= 0) return 0;
  time_t remaining = row->resets_at - now;
  if (remaining < 0) remaining = 0;
  if (remaining > row->duration) remaining = row->duration;
  return 100 - ((int)remaining * 100 / row->duration);
}

// Further ahead than the skew allows, one of the clocks is wrong.
static bool from_future(time_t stamp, time_t now) {
  return stamp - now > FUTURE_SKEW_SECONDS;
}

RowState row_state(const QuotaRow *row, int elapsed, time_t now) {
  if (now >= row->resets_at) return ROW_EXPIRED;
  if (row->failed || now - row->observed_at > FRESH_SECONDS || from_future(row->observed_at, now)) {
    return ROW_STALE;
  }
  // Same elapsed value as the marker, so colour and marker always agree.
  int pace = elapsed - row->used;
  if (pace >= 0) return ROW_GREEN;
  if (pace >= -10) return ROW_YELLOW;
  return ROW_RED;
}

static void row_status(const QuotaRow *row, RowState state, time_t now, char *out, size_t size) {
  out[0] = '\0';
  if (state == ROW_EXPIRED) {
    snprintf(out, size, "reset ?");
  } else if (state == ROW_STALE && from_future(row->observed_at, now)) {
    snprintf(out, size, "clock skew");
  } else if (state == ROW_STALE) {
    time_t age = now - row->observed_at;
    int minutes = age > 0 ? (int)(age / 60) : 0;
    if (minutes < 60) snprintf(out, size, "stale %dm", minutes);
    else if (minutes < 48 * 60) snprintf(out, size, "stale %dh", minutes / 60);
    else snprintf(out, size, "stale %dd", minutes / (24 * 60));
  }
}

static const char *provider_name(char service) {
  if (service == 'C') return "Claude";
  if (service == 'F') return "Fable";
  if (service == 'X') return "Codex";
  return NULL;
}

static void gauge_title(char service, const char *window, char *out, size_t size) {
  const char *name = provider_name(service);
  if (name) snprintf(out, size, "%s %s", name, window);
  else snprintf(out, size, "%c %s", service, window);
}

static int find_row(const QuotaRow *rows, int count, char service, const char *window) {
  for (int i = 0; i < count; ++i) {
    if (rows[i].service[0] == service && strcmp(rows[i].window, window) == 0) return i;
  }
  return -1;
}

int plan_gauges(const QuotaMessage *quota, time_t now, Gauge *gauges) {
  const QuotaRow *rows = quota->rows;
  int row_count = quota->row_count;
  // Weekly Claude and Fable rows share a gauge only when they describe the same
  // window; otherwise each takes its own line.
  int claude_7d = find_row(rows, row_count, 'C', "7d");
  int fable_7d = find_row(rows, row_count, 'F', "7d");
  bool paired = claude_7d >= 0 && fable_7d >= 0
      && rows[claude_7d].resets_at == rows[fable_7d].resets_at
      && rows[claude_7d].duration == rows[fable_7d].duration;
  int count = 0;
  for (int i = 0; i < row_count; ++i) {
    if (paired && i == fable_7d) continue;
    Gauge *gauge = &gauges[count++];
    memset(gauge, 0, sizeof(*gauge));
    gauge->rows[0] = &rows[i];
    gauge->elapsed = elapsed_percent(&rows[i], now);
    gauge->states[0] = row_state(&rows[i], gauge->elapsed, now);
    gauge->marker = gauge->states[0] != ROW_EXPIRED;
    row_status(&rows[i], gauge->states[0], now, gauge->status, sizeof(gauge->status));
    if (paired && i == claude_7d) {
      snprintf(gauge->title, sizeof(gauge->title), "Claude+Fable 7d");
      // Both bars share Claude's marker, so both colours use its elapsed value.
      gauge->rows[1] = &rows[fable_7d];
      gauge->states[1] = row_state(gauge->rows[1], gauge->elapsed, now);
      if (!gauge->status[0]) {
        row_status(gauge->rows[1], gauge->states[1], now, gauge->status, sizeof(gauge->status));
      }
    } else {
      gauge_title(rows[i].service[0], rows[i].window, gauge->title, sizeof(gauge->title));
    }
  }
  for (const char *code = quota->unavailable; *code && count < MAX_GAUGES; ++code) {
    Gauge *gauge = &gauges[count++];
    memset(gauge, 0, sizeof(*gauge));
    const char *name = provider_name(*code);
    if (name) snprintf(gauge->title, sizeof(gauge->title), "%s", name);
    else snprintf(gauge->title, sizeof(gauge->title), "%c", *code);
    snprintf(gauge->status, sizeof(gauge->status), "unavailable");
    gauge->states[0] = ROW_UNAVAILABLE;
  }
  if (count == 0) return 0;
  // A fresh first gauge carries the sync status instead of its own.
  if (!gauges[0].status[0]) {
    if (quota->collected_at > 0) {
      time_t age = now - quota->collected_at;
      snprintf(gauges[0].status, sizeof(gauges[0].status), "updated %dm ago",
               age > 0 ? (int)(age / 60) : 0);
    } else {
      snprintf(gauges[0].status, sizeof(gauges[0].status), "phone sync pending");
    }
  }
  return count;
}

bool show_temperature(const QuotaMessage *quota, time_t now) {
  return quota->has_temp && now - quota->collected_at <= FRESH_SECONDS
      && !from_future(quota->collected_at, now);
}
