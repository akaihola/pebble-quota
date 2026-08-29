// The phone cannot reach gogo through its loopback interface. Keep the tailnet
// endpoint as the production default; localStorage still overrides it for tests.
var DEFAULT_ENDPOINT = "https://gogo.crane-boa.ts.net:8450/v1/watch";
var DEFAULT_TOKEN = "test-only-token";
var REFRESH_MS = 15 * 60 * 1000;

function setting(name, fallback) {
  return localStorage.getItem(name) || fallback;
}

function sendQuota(data) {
  var rows = (data.q || []).slice(0, 4);
  var message = { COLLECTED_AT: data.at || 0, ROW_COUNT: rows.length };
  // Outside temperature in tenths of degC; only sent when the collector had it.
  if (typeof data.t === "number") message["TEMP"] = data.t;
  rows.forEach(function (row, index) {
    message["S" + index] = row.s;
    message["W" + index] = row.w;
    message["U" + index] = row.u;
    message["R" + index] = row.r;
    message["D" + index] = row.d;
    message["P" + index] = row.p;
  });
  var onSent = function () {
    console.log("Quota data sent");
  };
  var onFailed = function (error) {
    console.log("AppMessage failed: " + JSON.stringify(error));
  };
  Pebble.sendAppMessage(message, onSent, onFailed);
}

function refresh() {
  var request = new XMLHttpRequest();
  request.open("GET", setting("endpoint", DEFAULT_ENDPOINT), true);
  request.setRequestHeader("Authorization", "Bearer " + setting("token", DEFAULT_TOKEN));
  request.timeout = 15000;
  request.onload = function () {
    if (request.status >= 200 && request.status < 300) {
      try {
        sendQuota(JSON.parse(request.responseText));
      } catch (error) {
        console.log("Invalid quota JSON: " + error);
      }
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

Pebble.addEventListener("ready", function () {
  refresh();
  setInterval(refresh, REFRESH_MS);
});

Pebble.addEventListener("appmessage", function (event) {
  if (event.payload.REQUEST_SYNC) refresh();
});
