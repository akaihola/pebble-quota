// The phone cannot reach gogo through its loopback interface. Keep the tailnet
// endpoint as the default; saved phone settings in localStorage override it.
var DEFAULT_ENDPOINT = "https://gogo.crane-boa.ts.net:8450/v1/watch";
var DEFAULT_TOKEN = "test-only-token";
var REFRESH_MS = 15 * 60 * 1000;

function setting(name, fallback) {
  return localStorage.getItem(name) || fallback;
}

// Wire limits shared with the collector and the watch; see docs/collector.md.
var WIRE_VERSION = 1;
var MAX_LINES = 5;  // rows plus one line per unavailable provider
var INT_MAX = 2147483647;
var MAX_DURATION = 21474836;  // keeps the watch's duration * 100 within int32

function isInt(value, low, high) {
  return typeof value === "number" && Math.floor(value) === value && value >= low && value <= high;
}

function isText(value, pattern) {
  return typeof value === "string" && pattern.test(value);
}

// Checks the whole payload before building its AppMessage and throws on the
// first problem, so a bad payload changes nothing on the watch.
function quotaMessage(data) {
  if (!data || data.v !== WIRE_VERSION) {
    throw new Error("unsupported version " + JSON.stringify(data && data.v));
  }
  // Providers without rows; an older collector omits it.
  var unavailable = data.n === undefined ? "" : data.n;
  if (!isInt(data.at, 0, INT_MAX)) throw new Error("invalid at");
  if (!isText(unavailable, /^[A-Z]{0,3}$/)) throw new Error("invalid n");
  if (data.t !== undefined && !isInt(data.t, -INT_MAX, INT_MAX)) throw new Error("invalid t");
  if (!Array.isArray(data.q) || data.q.length + unavailable.length > MAX_LINES) {
    throw new Error("invalid q");
  }
  var message = {
    COLLECTED_AT: data.at,
    ROW_COUNT: data.q.length,
    UNAVAILABLE: unavailable,
  };
  // Outside temperature in tenths of degC; only sent when the collector had it.
  if (data.t !== undefined) message["TEMP"] = data.t;
  data.q.forEach(function (row, index) {
    if (!row || !isText(row.s, /^[A-Z]$/) || !isText(row.w, /^[ -~]{1,7}$/)
        || !isInt(row.u, 0, 100) || !isInt(row.r, 0, INT_MAX) || !isInt(row.d, 1, MAX_DURATION)
        || !(row.o === undefined || isInt(row.o, 0, INT_MAX))
        || !(row.e === undefined || isInt(row.e, 0, 1))) {
      throw new Error("invalid row " + index);
    }
    message["S" + index] = row.s;
    message["W" + index] = row.w;
    message["U" + index] = row.u;
    message["R" + index] = row.r;
    message["D" + index] = row.d;
    // Each row's own reading time; an older collector sends only the pass time.
    message["O" + index] = row.o === undefined ? data.at : row.o;
    message["E" + index] = row.e || 0;
  });
  return message;
}

// Only the latest refresh may forward data. Settings changes start a new
// timestamp history; a collector clock reset can recover after one interval.
var refreshSequence = 0;
var currentEndpoint;
var currentToken;
var lastCollectedAt;
var lastForwardedAt;

function sendQuota(message) {
  var onSent = function () {
    console.log("Quota data sent");
  };
  var onFailed = function (error) {
    console.log("AppMessage failed; deferred until next refresh: " + JSON.stringify(error));
  };
  Pebble.sendAppMessage(message, onSent, onFailed);
}

function refresh() {
  var sequence = ++refreshSequence;
  var endpoint = setting("endpoint", DEFAULT_ENDPOINT);
  var token = setting("token", DEFAULT_TOKEN);
  if (endpoint !== currentEndpoint || token !== currentToken) {
    lastCollectedAt = undefined;
    currentEndpoint = endpoint;
    currentToken = token;
  }
  var request = new XMLHttpRequest();
  request.open("GET", endpoint, true);
  request.setRequestHeader("Authorization", "Bearer " + token);
  request.timeout = 15000;
  request.onload = function () {
    if (sequence !== refreshSequence) return;
    if (request.status >= 200 && request.status < 300) {
      var message;
      try {
        message = quotaMessage(JSON.parse(request.responseText));
      } catch (error) {
        console.log("Rejected quota data: " + error.message);
        return;
      }
      var now = Date.now();
      var age = now - lastForwardedAt;
      // Do not let a bad timestamp poison this generation indefinitely. Invalid
      // or backward phone clocks also bypass the bounded timestamp comparison.
      if (age >= 0 && age < REFRESH_MS && message.COLLECTED_AT < lastCollectedAt) {
        console.log("Rejected older quota data");
        return;
      }
      lastCollectedAt = message.COLLECTED_AT;
      lastForwardedAt = now;
      // No immediate retry: the next ready/watch/timer/settings refresh retries
      // delivery with its own current response, including equal timestamps.
      sendQuota(message);
    } else {
      console.log("Quota HTTP status " + request.status);
    }
  };
  request.onerror = function () {
    console.log("Quota request failed");
  };
  request.ontimeout = function () {
    console.log("Quota request timed out");
  };
  request.send();
}

function configUrl() {
  var endpoint = setting("endpoint", DEFAULT_ENDPOINT);
  var base = endpoint.replace(/\/v1\/watch\/?$/, "");
  return base + "/config?endpoint=" + encodeURIComponent(endpoint)
    + "&token=" + encodeURIComponent(setting("token", DEFAULT_TOKEN));
}

Pebble.addEventListener("showConfiguration", function () {
  Pebble.openURL(configUrl());
});

Pebble.addEventListener("webviewclosed", function (event) {
  if (!event.response) return;
  try {
    var settings = JSON.parse(decodeURIComponent(event.response));
    if (settings.endpoint) localStorage.setItem("endpoint", settings.endpoint);
    if (settings.token) localStorage.setItem("token", settings.token);
    refresh();
  } catch (error) {
    console.log("Invalid settings JSON: " + error);
  }
});

Pebble.addEventListener("ready", function () {
  refresh();
  setInterval(refresh, REFRESH_MS);
});

Pebble.addEventListener("appmessage", function (event) {
  if (event.payload.REQUEST_SYNC) refresh();
});
