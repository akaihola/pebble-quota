#include <pebble.h>

#include "gauges.h"

#define BAR_X 12
#define BAR_W 176

// Vertical layout for emery (200x228). Regions stack top to bottom.
#define TIME_BAND_H 56
#define CAL_TOP TIME_BAND_H
#define CAL_HEADER_H 14
#define CAL_GRID_TOP (CAL_TOP + CAL_HEADER_H)
#define CAL_GRID_H 66            // 3 week rows of 22px
#define CAL_WEEKS 3
#define CAL_DAYS 7
#define PACE_TOP (CAL_GRID_TOP + CAL_GRID_H)
#define TEMP_BAND_W 52          // right slice of the time band reserved for temperature

static Window *s_window;
static Layer *s_canvas;
static char s_time[8];

// Static: these are too large for the callbacks' stacks.
static QuotaMessage s_quota;     // the last valid message
static QuotaMessage s_incoming;  // decoding scratch; replaces s_quota only when valid
static Field s_fields[MESSAGE_FIELDS];
static Gauge s_gauges[MAX_GAUGES];

// Message keys in decode_message's field order.
static const uint32_t *const s_keys[MESSAGE_FIELDS] = {
  &MESSAGE_KEY_COLLECTED_AT, &MESSAGE_KEY_ROW_COUNT, &MESSAGE_KEY_TEMP, &MESSAGE_KEY_UNAVAILABLE,
  &MESSAGE_KEY_S0, &MESSAGE_KEY_W0, &MESSAGE_KEY_U0, &MESSAGE_KEY_R0, &MESSAGE_KEY_D0, &MESSAGE_KEY_O0, &MESSAGE_KEY_E0,
  &MESSAGE_KEY_S1, &MESSAGE_KEY_W1, &MESSAGE_KEY_U1, &MESSAGE_KEY_R1, &MESSAGE_KEY_D1, &MESSAGE_KEY_O1, &MESSAGE_KEY_E1,
  &MESSAGE_KEY_S2, &MESSAGE_KEY_W2, &MESSAGE_KEY_U2, &MESSAGE_KEY_R2, &MESSAGE_KEY_D2, &MESSAGE_KEY_O2, &MESSAGE_KEY_E2,
  &MESSAGE_KEY_S3, &MESSAGE_KEY_W3, &MESSAGE_KEY_U3, &MESSAGE_KEY_R3, &MESSAGE_KEY_D3, &MESSAGE_KEY_O3, &MESSAGE_KEY_E3,
  &MESSAGE_KEY_S4, &MESSAGE_KEY_W4, &MESSAGE_KEY_U4, &MESSAGE_KEY_R4, &MESSAGE_KEY_D4, &MESSAGE_KEY_O4, &MESSAGE_KEY_E4,
};

static int clamp_int(int value, int low, int high) {
  return value < low ? low : (value > high ? high : value);
}

static GColor state_color(RowState state) {
  if (state == ROW_GREEN) return GColorGreen;
  if (state == ROW_YELLOW) return GColorYellow;
  if (state == ROW_RED) return GColorRed;
  return GColorDarkGray;  // stale usage never gets a reassuring pace color
}

// ---- Calendar -------------------------------------------------------------

// Copy struct tm out of localtime's static buffer. Anchor at local noon so the
// +/- day arithmetic avoids ordinary overnight DST transitions.
static struct tm relative_day(int days_from_today) {
  time_t now = time(NULL);
  struct tm base = *localtime(&now);
  base.tm_hour = 12;
  base.tm_min = 0;
  base.tm_sec = 0;
  time_t stamp = mktime(&base) + (time_t)days_from_today * 86400;
  struct tm *result = localtime(&stamp);
  struct tm out = *result;
  return out;
}

// Monday-first column index: Mon->0 .. Sun->6.
static int monday_index(int tm_wday) {
  return (tm_wday + 6) % 7;
}

static void draw_cell_number(GContext *ctx, int mday, GRect cell, GColor color, bool bold) {
  char buffer[4];
  snprintf(buffer, sizeof(buffer), "%d", mday);
  GFont font = fonts_get_system_font(bold ? FONT_KEY_GOTHIC_18_BOLD : FONT_KEY_GOTHIC_18);
  GSize size = graphics_text_layout_get_content_size(
      buffer, font, cell, GTextOverflowModeFill, GTextAlignmentCenter);
  int top = cell.origin.y + (cell.size.h - size.h) / 2;
  graphics_context_set_text_color(ctx, color);
  graphics_draw_text(ctx, buffer, font,
                     GRect(cell.origin.x, top, cell.size.w, size.h + 2),
                     GTextOverflowModeFill, GTextAlignmentCenter, NULL);
}

static void draw_calendar(GContext *ctx, int w) {
  const int cell_w = w / CAL_DAYS;                 // 28
  const int grid_left = (w - cell_w * CAL_DAYS) / 2;
  const int cell_h = CAL_GRID_H / CAL_WEEKS;       // 22

  struct tm today = relative_day(0);
  const int i_today = CAL_DAYS + monday_index(today.tm_wday);  // middle week

  // Weekday header, Monday-first. Weekend letters echo the weekend color.
  static const char *labels[CAL_DAYS] = {"M", "T", "W", "T", "F", "S", "S"};
  GFont hfont = fonts_get_system_font(FONT_KEY_GOTHIC_14);
  for (int c = 0; c < CAL_DAYS; ++c) {
    graphics_context_set_text_color(ctx, (c >= 5) ? GColorRed : GColorLightGray);
    graphics_draw_text(ctx, labels[c], hfont,
                       GRect(grid_left + c * cell_w, CAL_TOP - 1, cell_w, CAL_HEADER_H + 2),
                       GTextOverflowModeFill, GTextAlignmentCenter, NULL);
  }

  // Today highlight box.
  int tcol = i_today % CAL_DAYS;
  int trow = i_today / CAL_DAYS;
  graphics_context_set_fill_color(ctx, GColorWhite);
  graphics_fill_rect(ctx,
      GRect(grid_left + tcol * cell_w, CAL_GRID_TOP + trow * cell_h, cell_w, cell_h),
      2, GCornersAll);

  for (int i = 0; i < CAL_WEEKS * CAL_DAYS; ++i) {
    struct tm d = relative_day(i - i_today);
    bool is_today = (i == i_today);
    bool weekend = (d.tm_wday == 0 || d.tm_wday == 6);
    bool other_month = (d.tm_mon != today.tm_mon);

    GColor color;
    if (is_today) {
      color = GColorBlack;                                   // on white box
    } else if (weekend) {
      color = other_month ? GColorDarkCandyAppleRed : GColorRed;
    } else {
      color = other_month ? GColorDarkGray : GColorWhite;
    }

    int col = i % CAL_DAYS;
    int row = i / CAL_DAYS;
    GRect cell = GRect(grid_left + col * cell_w, CAL_GRID_TOP + row * cell_h, cell_w, cell_h);
    draw_cell_number(ctx, d.tm_mday, cell, color, is_today || weekend);
  }
}

// ---- Pace rows ------------------------------------------------------------

static void draw_bar(GContext *ctx, const QuotaRow *row, RowState state, int y, int h) {
  if (!row || state == ROW_EXPIRED) {
    // No usage is known for the current window: a dim, empty track.
    graphics_context_set_fill_color(ctx, GColorDarkGray);
    graphics_fill_rect(ctx, GRect(BAR_X, y, BAR_W, h), 2, GCornersAll);
    return;
  }
  // Remaining quota is a bright gray track; the used portion is a vivid pace color
  // drawn on top. Bright-gray-vs-saturated-color gives far stronger separation on
  // the 64-color display than the old dark-gray-on-black track did.
  graphics_context_set_fill_color(ctx, GColorLightGray);
  graphics_fill_rect(ctx, GRect(BAR_X, y, BAR_W, h), 2, GCornersAll);
  graphics_context_set_fill_color(ctx, state_color(state));
  graphics_fill_rect(ctx, GRect(BAR_X, y, BAR_W * clamp_int(row->used, 0, 100) / 100, h),
                     2, GCornersAll);
}

static void draw_marker(GContext *ctx, int x, int top, int bottom) {
  // Ideal-pace marker: white core with a black halo so it stays readable over the
  // light-gray track, over any pace color, and against the black background.
  GPoint marker_top = GPoint(x, top);
  GPoint marker_bottom = GPoint(x, bottom);
  graphics_context_set_stroke_color(ctx, GColorBlack);
  graphics_context_set_stroke_width(ctx, 4);
  graphics_draw_line(ctx, marker_top, marker_bottom);
  graphics_context_set_stroke_color(ctx, GColorWhite);
  graphics_context_set_stroke_width(ctx, 2);
  graphics_draw_line(ctx, marker_top, marker_bottom);
}

static void draw_gauge_label(GContext *ctx, const char *title, const char *status, int y) {
  GFont font = fonts_get_system_font(FONT_KEY_GOTHIC_14);
  int status_w = 0;
  if (status[0]) {
    // Status shares the title row, right-aligned; the title gets whatever
    // width is left, with an ellipsis if it ever collides.
    GSize size = graphics_text_layout_get_content_size(status, font,
        GRect(BAR_X, y - 1, BAR_W, 16), GTextOverflowModeFill, GTextAlignmentLeft);
    status_w = size.w + 6;
    graphics_context_set_text_color(ctx, GColorLightGray);
    graphics_draw_text(ctx, status, font, GRect(BAR_X, y - 1, BAR_W, 16),
                       GTextOverflowModeFill, GTextAlignmentRight, NULL);
  }
  graphics_context_set_text_color(ctx, GColorWhite);
  graphics_draw_text(ctx, title, font, GRect(BAR_X, y - 1, BAR_W - status_w, 16),
                     GTextOverflowModeTrailingEllipsis, GTextAlignmentLeft, NULL);
}

static void draw_gauge(GContext *ctx, const Gauge *gauge, int y, int rh) {
  draw_gauge_label(ctx, gauge->title, gauge->status, y);
  int top, bottom;
  if (gauge->rows[1]) {
    // Two bars with a 1px gap share the first row's marker.
    int bar_h = clamp_int((rh - 17 - 1) / 2, 3, 10);
    int first_y = y + rh - 2 * bar_h - 2;
    int second_y = first_y + bar_h + 1;
    draw_bar(ctx, gauge->rows[0], gauge->states[0], first_y, bar_h);
    draw_bar(ctx, gauge->rows[1], gauge->states[1], second_y, bar_h);
    top = first_y - 2;
    bottom = second_y + bar_h + 2;
  } else {
    // The bar fills with the *used* fraction.
    int bar_h = clamp_int(rh - 17, 4, 10);
    int bar_y = y + rh - bar_h - 1;
    draw_bar(ctx, gauge->rows[0], gauge->states[0], bar_y, bar_h);
    top = bar_y - 3;
    bottom = bar_y + bar_h + 3;
  }
  if (gauge->marker) draw_marker(ctx, BAR_X + BAR_W * gauge->elapsed / 100, top, bottom);
}

static void canvas_update(Layer *layer, GContext *ctx) {
  GRect bounds = layer_get_bounds(layer);
  int w = bounds.size.w;
  int h = bounds.size.h;
  time_t now = time(NULL);

  graphics_context_set_fill_color(ctx, GColorBlack);
  graphics_fill_rect(ctx, bounds, 0, GCornerNone);

  // Large black-on-white time band (Clean Calendar style).
  graphics_context_set_fill_color(ctx, GColorWhite);
  graphics_fill_rect(ctx, GRect(0, 0, w, TIME_BAND_H), 0, GCornerNone);
  graphics_context_set_text_color(ctx, GColorBlack);
  // When a fresh temperature is present, centre the time in the left part of the
  // band and place the reading in the reserved right slice; otherwise use the
  // full width so absent-temperature layout is unchanged.
  bool temp = show_temperature(&s_quota, now);
  int time_w = temp ? w - TEMP_BAND_W : w;
  graphics_draw_text(ctx, s_time, fonts_get_system_font(FONT_KEY_LECO_42_NUMBERS),
                     GRect(0, 3, time_w, TIME_BAND_H - 3), GTextOverflowModeFill,
                     GTextAlignmentCenter, NULL);
  if (temp) {
    char temp_text[8];
    // Round tenths to nearest whole degree, ties away from zero, e.g. "22°".
    int tenths = s_quota.temp_tenths;
    int deg = (tenths >= 0 ? tenths + 5 : tenths - 5) / 10;
    snprintf(temp_text, sizeof(temp_text), "%d°", deg);
    graphics_draw_text(ctx, temp_text, fonts_get_system_font(FONT_KEY_GOTHIC_28_BOLD),
                       GRect(w - TEMP_BAND_W, 13, TEMP_BAND_W - 4, 30),
                       GTextOverflowModeFill, GTextAlignmentRight, NULL);
  }

  // Middle: colored Monday-first three-week calendar.
  draw_calendar(ctx, w);

  // Bottom: compact pace bars. The first gauge's title row carries the sync
  // status unless that gauge has a state of its own to show.
  int avail = h - PACE_TOP;
  int count = plan_gauges(&s_quota, now, s_gauges);
  if (count == 0) {
    graphics_context_set_text_color(ctx, GColorLightGray);
    graphics_draw_text(ctx, "Waiting for quota data",
                       fonts_get_system_font(FONT_KEY_GOTHIC_18_BOLD),
                       GRect(12, PACE_TOP + 8, w - 24, avail - 8),
                       GTextOverflowModeWordWrap, GTextAlignmentCenter, NULL);
    return;
  }
  int rh = avail / count;
  for (int i = 0; i < count; ++i) draw_gauge(ctx, &s_gauges[i], PACE_TOP + i * rh, rh);
}

static void update_time(void) {
  time_t now = time(NULL);
  struct tm *local = localtime(&now);
  strftime(s_time, sizeof(s_time), clock_is_24h_style() ? "%H:%M" : "%I:%M", local);
  if (s_canvas) layer_mark_dirty(s_canvas);
}

static void tick_handler(struct tm *tick_time, TimeUnits units_changed) {
  // Each minute also re-ages the rows, so they turn stale without a new message.
  update_time();
}

static Field tuple_field(DictionaryIterator *iter, uint32_t key) {
  Tuple *tuple = dict_find(iter, key);
  if (!tuple) return (Field){FIELD_MISSING, 0, NULL};
  FieldType type = tuple->type == TUPLE_CSTRING ? FIELD_STRING
                 : tuple->type == TUPLE_UINT ? FIELD_UINT
                 : tuple->type == TUPLE_INT ? FIELD_INT : FIELD_BYTES;
  return (Field){type, tuple->length, tuple->value};
}

static void inbox_received(DictionaryIterator *iter, void *context) {
  for (int i = 0; i < MESSAGE_FIELDS; ++i) s_fields[i] = tuple_field(iter, *s_keys[i]);
  // A malformed message changes nothing; the shown rows keep aging.
  if (!decode_message(s_fields, &s_incoming)) {
    APP_LOG(APP_LOG_LEVEL_WARNING, "Rejected malformed quota message");
    return;
  }
  s_quota = s_incoming;
  layer_mark_dirty(s_canvas);
}

static void request_sync(void) {
  DictionaryIterator *iter;
  if (app_message_outbox_begin(&iter) == APP_MSG_OK) {
    dict_write_uint8(iter, MESSAGE_KEY_REQUEST_SYNC, 1);
    app_message_outbox_send();
  }
}

static void window_load(Window *window) {
  Layer *root = window_get_root_layer(window);
  s_canvas = layer_create(layer_get_bounds(root));
  layer_set_update_proc(s_canvas, canvas_update);
  layer_add_child(root, s_canvas);
}

static void window_unload(Window *window) {
  layer_destroy(s_canvas);
}

static void init(void) {
  s_window = window_create();
  window_set_background_color(s_window, GColorBlack);
  window_set_window_handlers(s_window, (WindowHandlers){.load = window_load, .unload = window_unload});
  window_stack_push(s_window, false);

  app_message_register_inbox_received(inbox_received);
  app_message_open(2048, 128);
  tick_timer_service_subscribe(MINUTE_UNIT, tick_handler);
  update_time();
  request_sync();
}

static void deinit(void) {
  tick_timer_service_unsubscribe();
  app_message_deregister_callbacks();
  window_destroy(s_window);
}

int main(void) {
  init();
  app_event_loop();
  deinit();
}
