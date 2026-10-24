#include "gauges.h"

#include <stdio.h>
#include <string.h>

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

int plan_gauges(const QuotaRow *rows, int row_count, const char *unavailable,
                time_t collected_at, time_t now, Gauge *gauges) {
  if (row_count <= 0) return 0;
  // Pair weekly Claude/Fable rows by identity. This assumes equal resets and
  // durations; the pairing does not check them.
  int claude_7d = find_row(rows, row_count, 'C', "7d");
  int fable_7d = find_row(rows, row_count, 'F', "7d");
  bool paired = claude_7d >= 0 && fable_7d >= 0;
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
  for (const char *code = unavailable; code && *code && count < MAX_GAUGES; ++code) {
    Gauge *gauge = &gauges[count++];
    memset(gauge, 0, sizeof(*gauge));
    const char *name = provider_name(*code);
    if (name) snprintf(gauge->title, sizeof(gauge->title), "%s", name);
    else snprintf(gauge->title, sizeof(gauge->title), "%c", *code);
    snprintf(gauge->status, sizeof(gauge->status), "unavailable");
    gauge->states[0] = ROW_UNAVAILABLE;
  }
  // A fresh first gauge carries the sync status instead of its own.
  if (!gauges[0].status[0]) {
    if (collected_at > 0) {
      time_t age = now - collected_at;
      snprintf(gauges[0].status, sizeof(gauges[0].status), "updated %dm ago",
               age > 0 ? (int)(age / 60) : 0);
    } else {
      snprintf(gauges[0].status, sizeof(gauges[0].status), "phone sync pending");
    }
  }
  return count;
}

bool show_temperature(bool has_temp, time_t collected_at, time_t now) {
  return has_temp && now - collected_at <= FRESH_SECONDS && !from_future(collected_at, now);
}
