// Run the phone script against one synthetic quota response and print the
// AppMessages it sends. Usage: node phone.js <index.js> < response.json, where
// the response is {"status": 200, "body": "..."} or {"error": true}.
"use strict";
const fs = require("fs");
const vm = require("vm");

const response = JSON.parse(fs.readFileSync(0, "utf8"));
const listeners = {};
const requests = [];
const sent = [];

function FakeRequest() {
  this.open = function () {};
  this.setRequestHeader = function () {};
  this.send = function () {
    requests.push(this);
  };
}

const context = vm.createContext({
  console: { log: function () {} },
  localStorage: { getItem: function () { return null; }, setItem: function () {} },
  setInterval: function () {},
  XMLHttpRequest: FakeRequest,
  Pebble: {
    addEventListener: function (name, handler) {
      listeners[name] = handler;
    },
    sendAppMessage: function (message) {
      sent.push(message);
    },
    openURL: function () {},
  },
});
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context);
listeners.ready();
for (const request of requests) {
  if (response.error) {
    request.onerror();
  } else {
    request.status = response.status;
    request.responseText = response.body;
    request.onload();
  }
}
process.stdout.write(JSON.stringify(sent));
