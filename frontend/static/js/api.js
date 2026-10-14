/**
 * 统一接口封装：
 *  - 自动拼接 API 前缀、注入 Authorization 头
 *  - 统一解包 {code, message, data}
 *  - 401 自动清理登录态并跳转登录页
 *  - 422 时把字段级错误拼成可读提示，方便排查
 */
(function (global) {
  'use strict';

  var API_BASE = '/api/v1';
  var TOKEN_KEY = 'ledger_token';
  var USER_KEY = 'ledger_user';

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || '';
  }

  function getStoredUser() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
    } catch (err) {
      return null;
    }
  }

  function saveAuth(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user || null));
  }

  function clearAuth() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function buildQuery(params) {
    if (!params) return '';
    var parts = [];
    Object.keys(params).forEach(function (key) {
      var value = params[key];
      if (value === undefined || value === null || value === '') return;
      parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(value));
    });
    return parts.length ? '?' + parts.join('&') : '';
  }

  function formatFieldErrors(errors) {
    if (!errors || !errors.length) return '';
    return errors
      .map(function (item) {
        return (item.field || '') + ': ' + (item.message || '');
      })
      .join('\n');
  }

  function request(path, options) {
    options = options || {};
    var url = API_BASE + path + buildQuery(options.params);
    var headers = { Accept: 'application/json' };
    if (options.body !== undefined) headers['Content-Type'] = 'application/json';
    var token = getToken();
    if (token) headers.Authorization = 'Bearer ' + token;

    return fetch(url, {
      method: options.method || 'GET',
      headers: headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined
    }).then(function (response) {
      if (response.status === 401) {
        clearAuth();
        if (!options.skipAuthRedirect) {
          global.location.href = '/login';
        }
        return response
          .json()
          .catch(function () {
            return { message: '登录状态已失效' };
          })
          .then(function (body) {
            throw new Error(body.message || '登录状态已失效');
          });
      }

      if (response.status === 204) return null;

      return response
        .json()
        .catch(function () {
          throw new Error('服务器返回了非 JSON 响应（HTTP ' + response.status + '）');
        })
        .then(function (body) {
          if (!response.ok || (body && body.code && body.code >= 400)) {
            var message = (body && body.message) || '请求失败（HTTP ' + response.status + '）';
            var detail = formatFieldErrors(body && body.errors);
            var error = new Error(detail ? message + '\n' + detail : message);
            error.status = response.status;
            error.errors = (body && body.errors) || [];
            throw error;
          }
          return body ? body.data : null;
        });
    });
  }

  global.LedgerApi = {
    API_BASE: API_BASE,
    request: request,
    getToken: getToken,
    getStoredUser: getStoredUser,
    saveAuth: saveAuth,
    clearAuth: clearAuth,
    isLoggedIn: function () {
      return !!getToken();
    },
    register: function (payload) {
      return request('/auth/register', { method: 'POST', body: payload, skipAuthRedirect: true });
    },
    login: function (payload) {
      return request('/auth/login', { method: 'POST', body: payload, skipAuthRedirect: true });
    },
    me: function () {
      return request('/auth/me');
    },
    categories: function (type) {
      return request('/categories', { params: { type: type } });
    },
    createCategory: function (payload) {
      return request('/categories', { method: 'POST', body: payload });
    },
    transactions: function (params) {
      return request('/transactions', { params: params });
    },
    summary: function (params) {
      return request('/transactions/summary', { params: params });
    },
    createTransaction: function (payload) {
      return request('/transactions', { method: 'POST', body: payload });
    },
    updateTransaction: function (id, payload) {
      return request('/transactions/' + id, { method: 'PUT', body: payload });
    },
    deleteTransaction: function (id) {
      return request('/transactions/' + id, { method: 'DELETE' });
    }
  };
})(window);
