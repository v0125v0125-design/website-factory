/* 접수 어댑터 — 폼 하나를 실제로 어딘가에 보낸다.
   WEBSITE FACTORY · 자동 생성 (storefront/templates/submit.js.j2)

   받는 곳은 storefront.json 의 submission 블록에서만 옵니다. 여기에 업체
   이름이 박히지 않게 해서, 나중에 받는 곳을 바꿔도 이 파일만 다시 찍으면
   되도록 했습니다.

   가장 중요한 규칙: **받는 곳이 없으면 보낸 척하지 않는다.**
   provider 가 비어 있으면 제출 버튼이 아예 눌리지 않고, 다른 연락 방법을
   안내합니다. 성공 화면은 서버가 2xx 로 답했을 때만 뜹니다. */
(function (global) {
  "use strict";

  var CONFIG = {
    provider: "",
    endpoint: "",
    successUrl: "",
    version: "ORDER_FLOW_V1"
  };

  /* 우리 backend 의 주소 — kind 하나당 한 길. 주소는 CONFIG.endpoint 에서만 옵니다. */
  var PATHS = { order: "/api/orders", recommend: "/api/orders", material: "/api/materials" };

  /* 사람이 3초 안에 다 채우고 보낼 수는 없다. 그보다 빠르면 기계다. */
  var MIN_FILL_MS = 3000;

  function ready() {
    return !!(CONFIG.provider && CONFIG.endpoint);
  }

  /* 폼 하나를 평평한 사전으로. 이름이 a.b 나 a[] 면 중첩으로 편다. */
  function collect(form) {
    var out = {};
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.disabled || el.name.charAt(0) === "_") { return; }
      if (el.type === "checkbox" && !el.checked) { return; }
      if (el.type === "radio" && !el.checked) { return; }
      if (el.type === "file") { return; }
      var value = (el.value || "").trim();
      if (!value) { return; }
      var slot = out;
      var path = el.name.split(".");
      var last = path.pop();
      path.forEach(function (key) {
        slot[key] = slot[key] || {};
        slot = slot[key];
      });
      if (last.slice(-2) === "[]") {
        last = last.slice(0, -2);
        slot[last] = slot[last] || [];
        slot[last].push(value);
      } else {
        slot[last] = value;
      }
    });
    return out;
  }

  /* 줄 단위로 반복되는 칸(서비스 1·2·3 …)을 배열로 모은다. */
  function rows(form, selector) {
    return Array.prototype.map.call(form.querySelectorAll(selector), function (row) {
      var one = {};
      Array.prototype.forEach.call(row.querySelectorAll("[data-field]"), function (el) {
        var value = (el.value || "").trim();
        if (value) { one[el.getAttribute("data-field")] = value; }
      });
      return one;
    }).filter(function (one) { return Object.keys(one).length > 0; });
  }

  function summarize(payload, fields) {
    return fields.map(function (pair) {
      return pair[0] + ": " + pair[1];
    }).join("\n");
  }

  /* 실제 전송. 서버가 받았다고 답하면 그 답을 돌려주고, 아니면 예외를 던집니다. */
  function send(payload, files) {
    if (!ready()) { return Promise.reject(fail("no-endpoint")); }

    if (CONFIG.provider === "website_factory") {
      var path = PATHS[payload.data.kind] || PATHS.order;
      return fetch(CONFIG.endpoint.replace(/\/+$/, "") + path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload.data)
      }).then(check);
    }

    if (CONFIG.provider === "formspree") {
      var body = new FormData();
      // 사람이 대시보드에서 바로 읽을 수 있게 평평한 칸도 함께 보냅니다.
      Object.keys(payload.flat || {}).forEach(function (key) {
        body.append(key, payload.flat[key]);
      });
      body.append("_subject", payload.subject);
      body.append("payload", JSON.stringify(payload.data));
      (files || []).forEach(function (file) { body.append(file.name, file.blob, file.filename); });
      return fetch(CONFIG.endpoint, {
        method: "POST", body: body, headers: { "Accept": "application/json" }
      }).then(check);
    }

    if (CONFIG.provider === "post") {
      // text/plain 으로 보냅니다 — 사전 요청(preflight) 없이 가는 가장 단순한 꼴이고
      // 구글 앱스스크립트 웹앱이 그대로 받습니다.
      return fetch(CONFIG.endpoint, {
        method: "POST",
        headers: { "Content-Type": "text/plain;charset=utf-8" },
        body: JSON.stringify(payload.data)
      }).then(check);
    }

    return Promise.reject(fail("unknown-provider"));
  }

  /* 실패를 세 갈래로 나눕니다 — 손님에게 보일 말이 달라집니다.
     rejected: 우리가 보낸 내용이 모자람 (서버가 이유를 한국어로 줍니다)
     server:   서버가 받지 못함
     network:  아예 닿지 못함 */
  function fail(kind, message) {
    var error = new Error(kind);
    error.kind = kind;
    if (message) { error.notice = message; }
    return error;
  }

  function check(response) {
    return response.text().then(function (body) {
      var data = null;
      try { data = JSON.parse(body); } catch (e) { data = null; }
      if (response.ok && (!data || data.ok !== false)) { return data || {}; }
      if (response.status >= 400 && response.status < 500) {
        throw fail("rejected", data && data.error);
      }
      throw fail("server");
    }, function () {
      throw fail("server");
    });
  }

  /* 폼 한 벌에 붙인다.
     opts = { form, build(), onSuccess(payload), onFailure(error), button, note } */
  function attach(opts) {
    var form = opts.form;
    var button = opts.button || form.querySelector("[type=submit]");
    var openedAt = Date.now();
    var sent = false;

    if (!ready()) {
      // 받는 곳이 없다. 버튼을 잠그고 다른 길을 안내한다.
      form.setAttribute("data-closed", "1");
      if (button) {
        button.disabled = true;
        button.setAttribute("aria-disabled", "true");
      }
      var closed = form.querySelector("[data-role=closed]");
      if (closed) { closed.hidden = false; }
      return;
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (sent || form.getAttribute("data-busy")) { return; }
      if (!form.checkValidity()) { form.reportValidity(); return; }

      // 벌집 — 사람 눈에 보이지 않는 칸이 채워져 있으면 기계다.
      var honey = form.querySelector("[name=_gotcha]");
      if (honey && honey.value) { return; }
      if (Date.now() - openedAt < MIN_FILL_MS) {
        var fast = form.querySelector("[data-role=too-fast]");
        if (fast) { fast.hidden = false; }
        return;
      }

      var payload = opts.build();
      // 서버도 다시 봅니다 — 앞단에서 막은 것을 서버가 믿지 않게 하기 위해서입니다.
      payload.data.elapsedMs = Date.now() - openedAt;
      payload.data._gotcha = honey ? honey.value : "";
      form.setAttribute("data-busy", "1");
      if (button) {
        button.dataset.idle = button.textContent;
        button.textContent = button.dataset.sending || "보내는 중…";
        button.disabled = true;
      }

      send(payload, opts.files ? opts.files() : [])
        .then(function (result) {
          sent = true;
          form.setAttribute("data-sent", "1");
          if (opts.onSuccess) { opts.onSuccess(payload, result || {}); }
          if (CONFIG.successUrl) { global.location.href = CONFIG.successUrl; }
        })
        .catch(function (error) {
          if (!error || !error.kind) { error = fail("network"); }
          if (opts.onFailure) { opts.onFailure(error); }
        })
        .then(function () {
          form.removeAttribute("data-busy");
          if (button && !sent) {
            button.textContent = button.dataset.idle;
            button.disabled = false;
          }
        });
    });
  }

  global.WF = {
    config: CONFIG,
    ready: ready,
    fail: fail,
    collect: collect,
    rows: rows,
    summarize: summarize,
    attach: attach
  };
})(window);
