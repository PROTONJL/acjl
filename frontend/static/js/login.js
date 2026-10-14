/** 登录 / 注册页逻辑 */
(function () {
  'use strict';

  if (!window.Vue) return;

  var api = window.LedgerApi;
  var validator = window.LedgerValidate;

  // 已登录直接进主页面
  if (api.isLoggedIn()) {
    window.location.replace('/');
    return;
  }

  Vue.createApp({
    data: function () {
      return {
        mode: 'login',
        loading: false,
        error: '',
        form: { username: '', password: '', confirm: '', nickname: '', email: '' }
      };
    },
    methods: {
      switchMode: function (mode) {
        this.mode = mode;
        this.error = '';
      },

      /** 前端体验层校验：不通过直接弹窗提示，不发送请求 */
      validate: function () {
        var message = validator.checkUsername(this.form.username);
        if (message) return message;

        if (this.mode === 'register') {
          message = validator.checkPassword(this.form.password);
          if (message) return message;
          message = validator.checkPasswordConfirm(this.form.password, this.form.confirm);
          if (message) return message;
        } else if (!this.form.password) {
          return '请输入密码';
        }

        if (this.form.email && !/^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/.test(this.form.email)) {
          return '邮箱格式不正确';
        }
        return null;
      },

      submit: function () {
        var self = this;
        var message = this.validate();
        if (message) {
          // 体验层拦截：直接弹窗，不发请求
          window.alert(message);
          return;
        }

        this.loading = true;
        this.error = '';
        var isRegister = this.mode === 'register';
        var payload = { username: this.form.username, password: this.form.password };
        if (isRegister) {
          if (this.form.nickname) payload.nickname = this.form.nickname;
          if (this.form.email) payload.email = this.form.email;
        }

        var task = isRegister ? api.register(payload) : api.login(payload);
        task
          .then(function () {
            // 注册成功后自动登录，保证一次流程走完
            return api.login({ username: payload.username, password: payload.password });
          })
          .then(function (data) {
            api.saveAuth(data.access_token, data.user);
            window.location.href = '/';
          })
          .catch(function (err) {
            self.error = err.message;
            // 后端拦截（400/401/409/422）时也用弹窗提示，方便对比前后端提示差异
            window.alert('操作失败：' + err.message);
          })
          .finally(function () {
            self.loading = false;
          });
      }
    }
  }).mount('#app');
})();
