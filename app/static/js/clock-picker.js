/* ================================================================
   clock-picker.js – Android Material Design circular clock picker
   Singleton API: window.ClockPicker.open(anchorEl, options)
   ================================================================ */
(function () {
  'use strict';

  let _overlay = null;
  let _dialog = null;
  let _state = null;

  // Position a number element on the clock face
  // faceSize=260, center=130
  function positionNumber(el, angleDeg, radius) {
    const angleRad = (angleDeg * Math.PI) / 180;
    const x = 130 + radius * Math.cos(angleRad);
    const y = 130 + radius * Math.sin(angleRad);
    el.style.left = (x - 18) + 'px'; // 18 = half of 36px element
    el.style.top  = (y - 18) + 'px';
  }

  // Angle for a clock position (12 at top = -90deg from x-axis)
  // position = 0..11 where 0=12o'clock, 1=1o'clock, etc.
  function clockAngle(position) {
    return position * 30 - 90;
  }

  function pad(n) {
    return String(n).padStart(2, '0');
  }

  function buildUI() {
    // Overlay
    _overlay = document.createElement('div');
    _overlay.className = 'cp-overlay';
    _overlay.addEventListener('click', () => cancel());

    // Dialog
    _dialog = document.createElement('div');
    _dialog.className = 'cp-dialog';
    _dialog.addEventListener('click', e => e.stopPropagation());

    // Header
    const header = document.createElement('div');
    header.className = 'cp-header';

    const hourLabel = document.createElement('span');
    hourLabel.className = 'cp-header-label cp-hour-label';
    hourLabel.addEventListener('click', () => setStage('hour'));

    const sep = document.createElement('span');
    sep.className = 'cp-header-sep';
    sep.textContent = ':';

    const minLabel = document.createElement('span');
    minLabel.className = 'cp-header-label cp-min-label';
    minLabel.addEventListener('click', () => setStage('minute'));

    header.appendChild(hourLabel);
    header.appendChild(sep);
    header.appendChild(minLabel);

    // Clock face
    const faceWrap = document.createElement('div');
    faceWrap.className = 'cp-face-wrap';

    const centerDot = document.createElement('div');
    centerDot.className = 'cp-center-dot';

    const hand = document.createElement('div');
    hand.className = 'cp-hand';

    faceWrap.appendChild(centerDot);
    faceWrap.appendChild(hand);

    // Actions
    const actions = document.createElement('div');
    actions.className = 'cp-actions';

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'cp-btn';
    cancelBtn.textContent = 'Annuleren';
    cancelBtn.addEventListener('click', () => cancel());

    const okBtn = document.createElement('button');
    okBtn.type = 'button';
    okBtn.className = 'cp-btn';
    okBtn.textContent = 'OK';
    okBtn.addEventListener('click', () => confirm());

    actions.appendChild(cancelBtn);
    actions.appendChild(okBtn);

    _dialog.appendChild(header);
    _dialog.appendChild(faceWrap);
    _dialog.appendChild(actions);

    document.body.appendChild(_overlay);
    document.body.appendChild(_dialog);

    _state._faceWrap = faceWrap;
    _state._hand = hand;
    _state._hourLabel = hourLabel;
    _state._minLabel = minLabel;
  }

  function buildNumbersForStage(stage) {
    const faceWrap = _state._faceWrap;
    // Remove existing number elements
    faceWrap.querySelectorAll('.cp-number').forEach(el => el.remove());

    if (stage === 'hour') {
      // Outer ring: 1-12
      for (let h = 1; h <= 12; h++) {
        const el = document.createElement('div');
        el.className = 'cp-number';
        el.textContent = h;
        el.dataset.value = h;
        // position: h at clockAngle(h % 12)
        positionNumber(el, clockAngle(h % 12), 96);
        el.addEventListener('click', () => selectHour(h));
        faceWrap.appendChild(el);
      }
      // Inner ring: 13-24 (0 displayed as 0/24)
      for (let h = 13; h <= 24; h++) {
        const el = document.createElement('div');
        el.className = 'cp-number inner';
        el.textContent = h === 24 ? '0' : h;
        el.dataset.value = h === 24 ? 0 : h;
        positionNumber(el, clockAngle(h % 12), 58);
        el.addEventListener('click', () => selectHour(h === 24 ? 0 : h));
        faceWrap.appendChild(el);
      }
    } else {
      // Minute ring: 0, 5, 10, ..., 55
      for (let i = 0; i < 12; i++) {
        const min = i * 5;
        const el = document.createElement('div');
        el.className = 'cp-number';
        el.textContent = pad(min);
        el.dataset.value = min;
        positionNumber(el, clockAngle(i), 96);
        el.addEventListener('click', () => selectMinute(min));
        faceWrap.appendChild(el);
      }
    }

    updateSelectedHighlight();
    updateHand();
  }

  function updateSelectedHighlight() {
    const stage = _state.stage;
    _state._faceWrap.querySelectorAll('.cp-number').forEach(el => {
      const val = parseInt(el.dataset.value);
      if (stage === 'hour') {
        el.classList.toggle('selected', val === _state.hours);
      } else {
        // For minutes, match nearest 5-min bucket
        const nearMin = Math.round(_state.minutes / 5) * 5 % 60;
        el.classList.toggle('selected', val === nearMin);
      }
    });
  }

  function updateHand() {
    const hand = _state._hand;
    const stage = _state.stage;
    let angleDeg, handHeight, radius;

    if (stage === 'hour') {
      const h = _state.hours % 12; // 0-11
      angleDeg = clockAngle(h === 0 ? 0 : h);
      // Inner ring for 13-24 (hours 0 is inner if was 24, but we store 0..23)
      const isInner = (_state.hours >= 13) || (_state.hours === 0);
      radius = isInner ? 58 : 96;
      handHeight = radius - 4;
    } else {
      const minPos = Math.round(_state.minutes / 5) % 12;
      angleDeg = clockAngle(minPos);
      radius = 96;
      handHeight = radius - 4;
    }

    // CSS: transform rotates from bottom center
    // Clock 12=top means 0deg in our clockAngle = -90deg from x-axis
    // Div bottom is at center, so "straight up" = rotate(0deg) from default
    // We need to rotate by (angleDeg + 90) because CSS 0deg = straight up (element goes up from bottom)
    const cssAngle = angleDeg + 90;
    hand.style.transform = `rotate(${cssAngle}deg)`;
    hand.style.height = handHeight + 'px';
  }

  function updateHeader() {
    _state._hourLabel.textContent = pad(_state.hours);
    _state._minLabel.textContent = pad(_state.minutes);
    _state._hourLabel.classList.toggle('active', _state.stage === 'hour');
    _state._minLabel.classList.toggle('active', _state.stage === 'minute');
  }

  function setStage(stage) {
    _state.stage = stage;
    buildNumbersForStage(stage);
    updateHeader();
  }

  function selectHour(h) {
    _state.hours = h;
    updateSelectedHighlight();
    updateHand();
    updateHeader();
    // Auto-advance to minutes after short delay
    setTimeout(() => {
      if (_state && _state.stage === 'hour') {
        setStage('minute');
      }
    }, 300);
  }

  function selectMinute(m) {
    _state.minutes = m;
    updateSelectedHighlight();
    updateHand();
    updateHeader();
    // Do NOT auto-advance for minutes
  }

  function confirm() {
    const cb = _state && _state.onConfirm;
    const result = { hours: _state.hours, minutes: _state.minutes };
    cleanup();
    if (cb) cb(result);
  }

  function cancel() {
    const cb = _state && _state.onCancel;
    cleanup();
    if (cb) cb();
  }

  function cleanup() {
    if (_overlay) { _overlay.remove(); _overlay = null; }
    if (_dialog)  { _dialog.remove();  _dialog = null; }
    _state = null;
  }

  window.ClockPicker = {
    open(anchorEl, options = {}) {
      // Close any existing instance
      if (_state) cleanup();

      _state = {
        hours:     options.hours     !== undefined ? options.hours     : new Date().getHours(),
        minutes:   options.minutes   !== undefined ? options.minutes   : 0,
        stage:     'hour',
        onConfirm: options.onConfirm || null,
        onCancel:  options.onCancel  || null,
        _faceWrap: null,
        _hand:     null,
        _hourLabel: null,
        _minLabel:  null,
      };

      buildUI();
      updateHeader();
      buildNumbersForStage('hour');
    },

    close() {
      if (_state) cancel();
    }
  };
})();
