/**
 * 前端体验层校验（**仅用于提前拦截、提升体验，不能替代后端校验**）。
 *
 * 与后端规则保持一致，但后端在 APP 层还有一份强制校验：
 *   - 密码策略：后端返回 400（详见 docs/VALIDATION-MATRIX.md）
 *   - 用户名格式：后端 Pydantic 返回 422
 *   - 金额必须 > 0 / 最多两位小数：后端返回 400
 */
(function (global) {
  'use strict';

  var PASSWORD_MIN = 8;
  var PASSWORD_MAX = 20;
  var USERNAME_RE = /^[A-Za-z0-9_]{3,20}$/;
  var MAX_AMOUNT = 9999999999.99;

  function checkUsername(username) {
    if (!username) return '请输入用户名';
    if (!USERNAME_RE.test(username)) return '用户名必须为 3-20 位，仅允许字母、数字和下划线';
    return null;
  }

  function checkPassword(password) {
    if (!password) return '请输入密码';
    if (password.length < PASSWORD_MIN || password.length > PASSWORD_MAX) {
      return '密码长度必须为 ' + PASSWORD_MIN + '-' + PASSWORD_MAX + ' 位';
    }
    if (/\s/.test(password)) return '密码不能包含空格';
    if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) return '密码必须同时包含字母和数字';
    return null;
  }

  function checkPasswordConfirm(password, confirm) {
    if (!confirm) return '请再次输入密码';
    if (password !== confirm) return '两次输入的密码不一致';
    return null;
  }

  /** 金额：正数、最多两位小数、不超过后端字段上限 */
  function checkAmount(value) {
    if (value === undefined || value === null || value === '') return '请输入金额';
    var text = String(value).trim();
    if (!/^\d+(\.\d{1,2})?$/.test(text)) return '金额只能为正数，且最多两位小数';
    var num = Number(text);
    if (!isFinite(num) || num <= 0) return '金额必须大于 0';
    if (num > MAX_AMOUNT) return '金额超出上限（最大 ' + MAX_AMOUNT + '）';
    return null;
  }

  /** 输入框实时过滤：只允许数字与一个小数点，小数最多两位 */
  function sanitizeAmountInput(value) {
    var text = String(value || '').replace(/[^\d.]/g, '');
    var firstDot = text.indexOf('.');
    if (firstDot >= 0) {
      text = text.slice(0, firstDot + 1) + text.slice(firstDot + 1).replace(/\./g, '');
      var parts = text.split('.');
      text = parts[0] + '.' + (parts[1] || '').slice(0, 2);
    }
    if (text.charAt(0) === '.') text = '0' + text;
    if (/^0\d/.test(text)) text = text.replace(/^0+/, '') || '0';
    return text.slice(0, 15);
  }

  global.LedgerValidate = {
    PASSWORD_MIN: PASSWORD_MIN,
    PASSWORD_MAX: PASSWORD_MAX,
    checkUsername: checkUsername,
    checkPassword: checkPassword,
    checkPasswordConfirm: checkPasswordConfirm,
    checkAmount: checkAmount,
    sanitizeAmountInput: sanitizeAmountInput
  };
})(window);
