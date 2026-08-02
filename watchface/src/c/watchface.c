#include <pebble.h>

#define MAX_ROWS 4
#define BAR_X 12
#define BAR_W 176

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

static void draw_row(GContext *ctx, const QuotaRow *row, int y, time_t now) {
  char label[16];
  char value[16];
  int used = clamp_int(row->used, 0, 100);
  int pace = clamp_int(row->pace, -999, 999);
  snprintf(label, sizeof(label), "%c %.7s", row->service[0], row->window);
  snprintf(value, sizeof(value), "%d%% %c%d", 100 - used,
           pace >= 0 ? '+' : '-', abs(pace));

  graphics_context_set_text_color(ctx, GColorWhite);
  graphics_draw_text(ctx, label, fonts_get_system_font(FONT_KEY_GOTHIC_18_BOLD),
                     GRect(BAR_X, y, 58, 22), GTextOverflowModeTrailingEllipsis,
                     GTextAlignmentLeft, NULL);
  graphics_draw_text(ctx, value, fonts_get_system_font(FONT_KEY_GOTHIC_18_BOLD),
                     GRect(70, y, 118, 22), GTextOverflowModeTrailingEllipsis,
                     GTextAlignmentRight, NULL);

  int bar_y = y + 22;
  graphics_context_set_fill_color(ctx, GColorDarkGray);
  graphics_fill_rect(ctx, GRect(BAR_X, bar_y, BAR_W, 8), 2, GCornersAll);
  graphics_context_set_fill_color(ctx, pace_color(row->pace));
  graphics_fill_rect(ctx, GRect(BAR_X, bar_y, BAR_W * clamp_int(row->used, 0, 100) / 100, 8),
                     2, GCornersAll);

  int marker_x = BAR_X + BAR_W * elapsed_percent(row, now) / 100;
  graphics_context_set_stroke_color(ctx, GColorWhite);
  graphics_context_set_stroke_width(ctx, 2);
  graphics_draw_line(ctx, GPoint(marker_x, bar_y - 2), GPoint(marker_x, bar_y + 10));
}

static void canvas_update(Layer *layer, GContext *ctx) {
  GRect bounds = layer_get_bounds(layer);
  time_t now = time(NULL);

  graphics_context_set_fill_color(ctx, GColorBlack);
  graphics_fill_rect(ctx, bounds, 0, GCornerNone);
  graphics_context_set_text_color(ctx, GColorWhite);
  graphics_draw_text(ctx, s_time, fonts_get_system_font(FONT_KEY_LECO_32_BOLD_NUMBERS),
                     GRect(0, 4, bounds.size.w, 42), GTextOverflowModeFill,
                     GTextAlignmentCenter, NULL);

  if (s_row_count == 0) {
    graphics_context_set_text_color(ctx, GColorLightGray);
    graphics_draw_text(ctx, "Waiting for quota data", fonts_get_system_font(FONT_KEY_GOTHIC_24_BOLD),
                       GRect(20, 80, bounds.size.w - 40, 60), GTextOverflowModeWordWrap,
                       GTextAlignmentCenter, NULL);
  } else {
    for (int i = 0; i < s_row_count; ++i) draw_row(ctx, &s_rows[i], 48 + i * 38, now);
  }

  char footer[32];
  if (s_collected_at > 0) {
    int age_minutes = (int)(now - s_collected_at) / 60;
    if (age_minutes < 0) age_minutes = 0;
    snprintf(footer, sizeof(footer), "updated %dm ago", age_minutes);
  } else {
    snprintf(footer, sizeof(footer), "phone sync pending");
  }
  graphics_context_set_text_color(ctx, GColorLightGray);
  graphics_draw_text(ctx, footer, fonts_get_system_font(FONT_KEY_GOTHIC_14),
                     GRect(0, bounds.size.h - 22, bounds.size.w, 18),
                     GTextOverflowModeFill, GTextAlignmentCenter, NULL);
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

  const uint32_t service_keys[] = {MESSAGE_KEY_S0, MESSAGE_KEY_S1, MESSAGE_KEY_S2, MESSAGE_KEY_S3};
  const uint32_t window_keys[] = {MESSAGE_KEY_W0, MESSAGE_KEY_W1, MESSAGE_KEY_W2, MESSAGE_KEY_W3};
  const uint32_t used_keys[] = {MESSAGE_KEY_U0, MESSAGE_KEY_U1, MESSAGE_KEY_U2, MESSAGE_KEY_U3};
  const uint32_t reset_keys[] = {MESSAGE_KEY_R0, MESSAGE_KEY_R1, MESSAGE_KEY_R2, MESSAGE_KEY_R3};
  const uint32_t duration_keys[] = {MESSAGE_KEY_D0, MESSAGE_KEY_D1, MESSAGE_KEY_D2, MESSAGE_KEY_D3};
  const uint32_t pace_keys[] = {MESSAGE_KEY_P0, MESSAGE_KEY_P1, MESSAGE_KEY_P2, MESSAGE_KEY_P3};

  for (int i = 0; i < s_row_count; ++i) {
    tuple_string(iter, service_keys[i], s_rows[i].service, sizeof(s_rows[i].service));
    tuple_string(iter, window_keys[i], s_rows[i].window, sizeof(s_rows[i].window));
    s_rows[i].used = tuple_int(iter, used_keys[i], 0);
    s_rows[i].resets_at = tuple_int(iter, reset_keys[i], 0);
    s_rows[i].duration = tuple_int(iter, duration_keys[i], 0);
    s_rows[i].pace = tuple_int(iter, pace_keys[i], 0);
  }
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
