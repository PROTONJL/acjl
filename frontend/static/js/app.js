/** 记账主页面逻辑 */
(function () {
  'use strict';

  if (!window.Vue) return;

  var api = window.LedgerApi;
  var validator = window.LedgerValidate;

  if (!api.isLoggedIn()) {
    window.location.replace('/login');
    return;
  }

  function today() {
    var now = new Date();
    var month = String(now.getMonth() + 1).padStart(2, '0');
    var day = String(now.getDate()).padStart(2, '0');
    return now.getFullYear() + '-' + month + '-' + day;
  }

  Vue.createApp({
    data: function () {
      return {
        user: api.getStoredUser(),
        categories: [],
        records: [],
        summary: { total_income: '0.00', total_expense: '0.00', balance: '0.00' },
        loading: false,
        submitting: false,
        filters: { type: '', category_id: '', start_date: '', end_date: '', keyword: '' },
        pagination: { page: 1, page_size: 10, total: 0, pages: 0 },
        showForm: false,
        formMode: 'create',
        editingId: null,
        formError: '',
        form: { type: 'expense', amount: '', category_id: '', occurred_at: today(), remark: '' }
      };
    },

    computed: {
      /** 筛选区的分类下拉：跟随筛选类型联动 */
      filterCategories: function () {
        var self = this;
        if (!this.filters.type) return this.categories;
        return this.categories.filter(function (item) {
          return item.type === self.filters.type;
        });
      },
      /** 弹窗里的分类下拉：与表单类型保持一致 */
      formCategories: function () {
        var self = this;
        return this.categories.filter(function (item) {
          return item.type === self.form.type;
        });
      }
    },

    mounted: function () {
      this.loadUser();
      this.loadCategories();
      this.reload();
    },

    methods: {
      loadUser: function () {
        var self = this;
        api.me()
          .then(function (user) {
            self.user = user;
            api.saveAuth(api.getToken(), user);
          })
          .catch(function () {
            /* 401 已由 api.js 统一处理跳转 */
          });
      },

      loadCategories: function () {
        var self = this;
        api.categories()
          .then(function (list) {
            self.categories = list || [];
          })
          .catch(function (err) {
            window.alert('加载分类失败：' + err.message);
          });
      },

      /** 拉取当前筛选条件下的明细与汇总 */
      reload: function () {
        var self = this;
        this.loading = true;
        var params = {
          page: this.pagination.page,
          page_size: this.pagination.page_size,
          type: this.filters.type,
          category_id: this.filters.category_id,
          start_date: this.filters.start_date,
          end_date: this.filters.end_date,
          keyword: this.filters.keyword
        };

        Promise.all([api.transactions(params), api.summary(params)])
          .then(function (result) {
            var page = result[0] || { items: [], total: 0, page: 1, pages: 0 };
            self.records = page.items || [];
            self.pagination.total = page.total || 0;
            self.pagination.pages = page.pages || 0;
            self.pagination.page = page.page || 1;
            self.summary = result[1] || self.summary;
          })
          .catch(function (err) {
            window.alert('加载数据失败：' + err.message);
          })
          .finally(function () {
            self.loading = false;
          });
      },

      applyFilter: function () {
        this.pagination.page = 1;
        this.reload();
      },

      resetFilter: function () {
        this.filters = { type: '', category_id: '', start_date: '', end_date: '', keyword: '' };
        this.pagination.page = 1;
        this.reload();
      },

      changePage: function (page) {
        if (page < 1 || page > this.pagination.pages) return;
        this.pagination.page = page;
        this.reload();
      },

      sanitizeAmount: function (value) {
        return validator.sanitizeAmountInput(value);
      },

      onTypeChange: function () {
        // 切换收支类型后，原分类可能不再适用，重置选择
        this.form.category_id = '';
      },

      openCreate: function () {
        this.formMode = 'create';
        this.editingId = null;
        this.formError = '';
        this.form = {
          type: 'expense',
          amount: '',
          category_id: '',
          occurred_at: today(),
          remark: ''
        };
        this.showForm = true;
      },

      openEdit: function (record) {
        this.formMode = 'edit';
        this.editingId = record.id;
        this.formError = '';
        this.form = {
          type: record.type,
          amount: record.amount,
          category_id: record.category_id,
          occurred_at: record.occurred_at,
          remark: record.remark || ''
        };
        this.showForm = true;
      },

      closeForm: function () {
        this.showForm = false;
        this.formError = '';
      },

      createCategory: function () {
        var self = this;
        var name = window.prompt('请输入分类名称（最多 30 字）');
        if (name === null) return;
        name = name.trim();
        if (!name) {
          window.alert('分类名称不能为空');
          return;
        }
        api.createCategory({ name: name, type: this.form.type })
          .then(function (category) {
            self.categories.push(category);
            self.form.category_id = category.id;
            window.alert('分类「' + category.name + '」创建成功');
          })
          .catch(function (err) {
            window.alert('创建分类失败：' + err.message);
          });
      },

      submitForm: function () {
        var self = this;

        // ---------- 前端体验层校验：不通过直接弹窗，不发请求 ----------
        var message = validator.checkAmount(this.form.amount);
        if (message) {
          window.alert(message);
          return;
        }
        if (!this.form.category_id) {
          window.alert('请选择分类');
          return;
        }
        if (!this.form.occurred_at) {
          window.alert('请选择日期');
          return;
        }

        var payload = {
          type: this.form.type,
          amount: String(this.form.amount),
          category_id: Number(this.form.category_id),
          occurred_at: this.form.occurred_at,
          remark: this.form.remark || null
        };

        this.submitting = true;
        this.formError = '';
        var task =
          this.formMode === 'create'
            ? api.createTransaction(payload)
            : api.updateTransaction(this.editingId, payload);

        task
          .then(function () {
            self.closeForm();
            self.reload();
          })
          .catch(function (err) {
            self.formError = err.message;
            window.alert('保存失败：' + err.message);
          })
          .finally(function () {
            self.submitting = false;
          });
      },

      removeRecord: function (record) {
        var self = this;
        if (!window.confirm('确认删除这条记录吗？删除后不可在列表中看到。')) return;
        api.deleteTransaction(record.id)
          .then(function () {
            // 删除后如果当前页空了，自动回退一页
            if (self.records.length === 1 && self.pagination.page > 1) {
              self.pagination.page -= 1;
            }
            self.reload();
          })
          .catch(function (err) {
            window.alert('删除失败：' + err.message);
          });
      },

      logout: function () {
        api.clearAuth();
        window.location.href = '/login';
      }
    }
  }).mount('#app');
})();
