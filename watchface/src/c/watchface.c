#include <pebble.h>
#include <string.h>

#define MAX_ROWS 5
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
static time_t s_collected_at;

typedef struct {
  char service[2];
  char window[8];
  int used;
  time_t resets_at;
  int duration;
  int pace;
} QuotaRow;

static QuotaRow s_rows[MAX_ROWS];
static int s_row_count;
static int s_temp_tenths;   // outside temperature, tenths of degC
static bool s_has_temp;     // false until the phone sends a temperature

static int clamp_int(int value, int low, int high) {
  return value < low ? low : (value > high ? high : value);
}

static int elapsed_percent(const QuotaRow *row, time_t now) {
  if (row->duration <= 0) return 0;
  int remaining = clamp_int((int)(row->resets_at - now), 0, row->duration);
  return 100 - (remaining * 100 / row->duration);
}

static GColor pace_color(int pace) {
  if (pace >= 0) return GColorGreen;
  if (pace >= -10) return GColorYellow;
  return GColorRed;
}

// ---- Calendar -------------------------------------------------------------

// Copy struct tm out of localtime's static buffer. Anchor at local noon so the
// +/- day arithmetic never lands on a DST discontinuity (localtime(3)).
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

static int find_row(char service, const char *window) {
  for (int i = 0; i < s_row_count; ++i) {
    if (s_rows[i].service[0] == service && strcmp(s_rows[i].window, window) == 0) return i;
  }
  return -1;
}

static void gauge_title(char service, const char *window, char *out, size_t size) {
  const char *name = NULL;
  if (service == 'C') name = "Claude";
  else if (service == 'F') name = "Fable";
  else if (service == 'X') name = "Codex";
  if (name) snprintf(out, size, "%s %s", name, window);
  else snprintf(out, size, "%c %s", service, window);
}

static void draw_bar_fill(GContext *ctx, int used, int pace, int x, int y, int w, int h) {
  // Remaining quota is a bright gray track; the used portion is a vivid pace color
  // drawn on top. Bright-gray-vs-saturated-color gives far stronger separation on
  // the 64-color display than the old dark-gray-on-black track did.
  graphics_context_set_fill_color(ctx, GColorLightGray);
  graphics_fill_rect(ctx, GRect(x, y, w, h), 2, GCornersAll);
  graphics_context_set_fill_color(ctx, pace_color(pace));
  graphics_fill_rect(ctx, GRect(x, y, w * used / 100, h), 2, GCornersAll);
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
  if (status) {
    // Sync status shares the title row, right-aligned; the title gets
    // whatever width is left, with an ellipsis if it ever collides.
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

static void draw_single_gauge(GContext *ctx, const QuotaRow *row, const char *title,
                              const char *status, int y, int rh, time_t now) {
  draw_gauge_label(ctx, title, status, y);

  int bar_h = clamp_int(rh - 17, 4, 10);
  int bar_y = y + rh - bar_h - 1;
  // The colored bar fills with the *used* fraction.
  draw_bar_fill(ctx, clamp_int(row->used, 0, 100), row->pace, BAR_X, bar_y, BAR_W, bar_h);

  int marker_x = BAR_X + BAR_W * elapsed_percent(row, now) / 100;
  draw_marker(ctx, marker_x, bar_y - 3, bar_y + bar_h + 3);
}

static void draw_combined_gauge(GContext *ctx, const QuotaRow *first, const QuotaRow *second,
                                const char *title, const char *status, int y, int rh, time_t now) {
  draw_gauge_label(ctx, title, status, y);

  // Two color bars share one gauge with a 1px gap; one window marker spans both
  // because both windows reset together.
  int bar_h = clamp_int((rh - 17 - 1) / 2, 3, 10);
  int first_y = y + rh - 2 * bar_h - 2;
  int second_y = first_y + bar_h + 1;
  draw_bar_fill(ctx, clamp_int(first->used, 0, 100), first->pace,
                BAR_X, first_y, BAR_W, bar_h);
  draw_bar_fill(ctx, clamp_int(second->used, 0, 100), second->pace,
                BAR_X, second_y, BAR_W, bar_h);

  int marker_x = BAR_X + BAR_W * elapsed_percent(first, now) / 100;
  draw_marker(ctx, marker_x, first_y - 2, second_y + bar_h + 2);
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
  // When a temperature is present, centre the time in the left part of the band
  // and place the reading in the reserved right slice; otherwise use the full
  // width so absent-temperature layout is unchanged.
  int time_w = s_has_temp ? w - TEMP_BAND_W : w;
  graphics_draw_text(ctx, s_time, fonts_get_system_font(FONT_KEY_LECO_42_NUMBERS),
                     GRect(0, 3, time_w, TIME_BAND_H - 3), GTextOverflowModeFill,
                     GTextAlignmentCenter, NULL);
  if (s_has_temp) {
    char temp[8];
    // Round tenths to whole degrees, away from zero, and show e.g. "22°".
    int deg = (s_temp_tenths >= 0 ? s_temp_tenths + 5 : s_temp_tenths - 5) / 10;
    snprintf(temp, sizeof(temp), "%d°", deg);
    graphics_draw_text(ctx, temp, fonts_get_system_font(FONT_KEY_GOTHIC_28_BOLD),
                       GRect(w - TEMP_BAND_W, 13, TEMP_BAND_W - 4, 30),
                       GTextOverflowModeFill, GTextAlignmentRight, NULL);
  }

  // Middle: colored Monday-first three-week calendar.
  draw_calendar(ctx, w);

  // Bottom: compact pace bars. The sync status rides on the first gauge's
  // title row, right-aligned, so four gauges fit with no footer.
  int region_bottom = h;
  int avail = region_bottom - PACE_TOP;
  char status[32];
  if (s_collected_at > 0) {
    int age_minutes = (int)(now - s_collected_at) / 60;
    if (age_minutes < 0) age_minutes = 0;
    snprintf(status, sizeof(status), "updated %dm ago", age_minutes);
  } else {
    snprintf(status, sizeof(status), "phone sync pending");
  }
  if (s_row_count == 0) {
    graphics_context_set_text_color(ctx, GColorLightGray);
    graphics_draw_text(ctx, "Waiting for quota data",
                       fonts_get_system_font(FONT_KEY_GOTHIC_18_BOLD),
                       GRect(12, PACE_TOP + 8, w - 24, avail - 8),
                       GTextOverflowModeWordWrap, GTextAlignmentCenter, NULL);
  } else {
    // The Claude 7d and Fable 7d rows share one gauge: two color bars with one
    // window marker, since both windows reset together.
    int claude_7d = find_row('C', "7d");
    int fable_7d = find_row('F', "7d");
    bool paired = claude_7d >= 0 && fable_7d >= 0;
    int rh = avail / (s_row_count - (paired ? 1 : 0));
    char title[24];
    for (int i = 0, gi = 0; i < s_row_count; ++i) {
      if (paired && i == fable_7d) continue;
      if (paired && i == claude_7d) {
        draw_combined_gauge(ctx, &s_rows[claude_7d], &s_rows[fable_7d],
                            "Claude+Fable 7d", gi == 0 ? status : NULL,
                            PACE_TOP + gi * rh, rh, now);
      } else {
        gauge_title(s_rows[i].service[0], s_rows[i].window, title, sizeof(title));
        draw_single_gauge(ctx, &s_rows[i], title, gi == 0 ? status : NULL,
                          PACE_TOP + gi * rh, rh, now);
      }
      ++gi;
    }
  }

}

static void update_time(void) {
  time_t now = time(NULL);
  struct tm *local = localtime(&now);
  strftime(s_time, sizeof(s_time), clock_is_24h_style() ? "%H:%M" : "%I:%M", local);
  if (s_canvas) layer_mark_dirty(s_canvas);
}

static void tick_handler(struct tm *tick_time, TimeUnits units_changed) {
  update_time();
}

static int32_t tuple_int(DictionaryIterator *iter, uint32_t key, int32_t fallback) {
  Tuple *tuple = dict_find(iter, key);
  return tuple ? tuple->value->int32 : fallback;
}

static void tuple_string(DictionaryIterator *iter, uint32_t key, char *target, size_t size) {
  Tuple *tuple = dict_find(iter, key);
  if (tuple && tuple->type == TUPLE_CSTRING) snprintf(target, size, "%s", tuple->value->cstring);
}

static void inbox_received(DictionaryIterator *iter, void *context) {
  s_collected_at = tuple_int(iter, MESSAGE_KEY_COLLECTED_AT, s_collected_at);
  s_row_count = clamp_int(tuple_int(iter, MESSAGE_KEY_ROW_COUNT, 0), 0, MAX_ROWS);

  const uint32_t service_keys[] = {MESSAGE_KEY_S0, MESSAGE_KEY_S1, MESSAGE_KEY_S2, MESSAGE_KEY_S3, MESSAGE_KEY_S4};
  const uint32_t window_keys[] = {MESSAGE_KEY_W0, MESSAGE_KEY_W1, MESSAGE_KEY_W2, MESSAGE_KEY_W3, MESSAGE_KEY_W4};
  const uint32_t used_keys[] = {MESSAGE_KEY_U0, MESSAGE_KEY_U1, MESSAGE_KEY_U2, MESSAGE_KEY_U3, MESSAGE_KEY_U4};
  const uint32_t reset_keys[] = {MESSAGE_KEY_R0, MESSAGE_KEY_R1, MESSAGE_KEY_R2, MESSAGE_KEY_R3, MESSAGE_KEY_R4};
  const uint32_t duration_keys[] = {MESSAGE_KEY_D0, MESSAGE_KEY_D1, MESSAGE_KEY_D2, MESSAGE_KEY_D3, MESSAGE_KEY_D4};
  const uint32_t pace_keys[] = {MESSAGE_KEY_P0, MESSAGE_KEY_P1, MESSAGE_KEY_P2, MESSAGE_KEY_P3, MESSAGE_KEY_P4};

  for (int i = 0; i < s_row_count; ++i) {
    tuple_string(iter, service_keys[i], s_rows[i].service, sizeof(s_rows[i].service));
    tuple_string(iter, window_keys[i], s_rows[i].window, sizeof(s_rows[i].window));
    s_rows[i].used = tuple_int(iter, used_keys[i], 0);
    s_rows[i].resets_at = tuple_int(iter, reset_keys[i], 0);
    s_rows[i].duration = tuple_int(iter, duration_keys[i], 0);
    s_rows[i].pace = tuple_int(iter, pace_keys[i], 0);
  }

  // Temperature is optional: absent key -> hide it (handled at draw time).
  Tuple *temp_tuple = dict_find(iter, MESSAGE_KEY_TEMP);
  s_has_temp = (temp_tuple != NULL);
  if (s_has_temp) s_temp_tenths = temp_tuple->value->int32;

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
