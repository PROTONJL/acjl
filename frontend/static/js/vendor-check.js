/**
 * Vue3 通过 CDN 引入。若网络不可达，页面上给出明确提示，
 * 避免出现"空白页面"这种难以排查的现象。
 */
window.addEventListener('DOMContentLoaded', function () {
  setTimeout(function () {
    if (window.Vue) return;
    var box = document.getElementById('app');
    if (!box) return;
    box.removeAttribute('v-cloak');
    box.innerHTML =
      '<div class="card" style="max-width:520px;padding:24px;">' +
      '<h1 style="font-size:18px;margin-top:0;">前端资源加载失败</h1>' +
      '<p>页面依赖的 Vue 3 CDN（unpkg.com）无法访问，请检查网络，' +
      '或把 <code>vue.global.prod.js</code> 下载到 <code>frontend/static/js/</code> 后，' +
      '把页面里的 CDN 引用改为本地路径。</p>' +
      '<p>后端接口本身不受影响，可直接用 Apifox/Postman 测试。</p>' +
      '</div>';
  }, 1500);
});
