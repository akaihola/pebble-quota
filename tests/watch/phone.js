// node phone.js <index.js> < fixture.json
// A single {status, body}/{error} completes ready immediately. A {steps: [...]}
// fixture emits events and completes indexed requests in any chosen order.
// An optional "saved" object seeds localStorage.
"use strict";
const fs = require("fs");
const vm = require("vm");

const response = JSON.parse(fs.readFileSync(0, "utf8"));
const listeners = {};
const requests = [];
const sent = [];
const log = [];
const delivered = [];
const settings = Object.assign({}, response.saved);
const requestDetails = [];
const opened = [];
let interval;
let now = 0;
let failMessages = 0;

function FakeRequest() {
  const details = { headers: {} };
  this.open = function (method, url) { details.url = url; };
  this.setRequestHeader = function (name, value) { details.headers[name] = value; };
  this.send = function () {
    requests.push(this);
    requestDetails.push(details);
  };
}

const context = vm.createContext({
  console: { log: function (line) { log.push(String(line)); } },
  localStorage: {
    getItem: function (key) { return settings[key] || null; },
    setItem: function (key, value) { settings[key] = value; },
  },
  Date: { now: function () { return now; } },
  setInterval: function (callback) { interval = callback; },
  setTimeout: function () { throw new Error("Unexpected retry timer"); },
  XMLHttpRequest: FakeRequest,
  Pebble: {
    addEventListener: function (name, handler) {
      listeners[name] = handler;
    },
    sendAppMessage: function (message, onSent, onFailed) {
      sent.push(message);
      if (failMessages > 0) {
        failMessages--;
        onFailed({ error: "busy" });
      } else {
        delivered.push(message);
        onSent();
      }
    },
    openURL: function (url) { opened.push(url); },
  },
});
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context);
function complete(request, result) {
  if (result.error) {
    request.onerror();
  } else if (result.timeout) {
    request.ontimeout();
  } else {
    request.status = result.status;
    request.responseText = result.body;
    request.onload();
  }
}

if (response.steps) {
  for (const step of response.steps) {
    if ("now" in step) now = step.now === null ? NaN : step.now;
    if ("failMessages" in step) failMessages = step.failMessages;
    if (step.event === "timer") interval();
    else if (step.event === "config") {
      // The original Pebble app passes the close payload encoded; the Core app decodes it first.
      const json = JSON.stringify(step.settings);
      listeners.webviewclosed({ response: step.decoded ? json : encodeURIComponent(json) });
    } else if (step.event === "watch") listeners.appmessage({ payload: { REQUEST_SYNC: 1 } });
    else if (step.event) listeners[step.event]();
    if ("request" in step) complete(requests[step.request], step);
  }
} else {
  listeners.ready();
  complete(requests[0], response);
}
process.stdout.write(JSON.stringify({ sent, log, delivered, requests: requestDetails, opened }));
