const pre = document.getElementById('content-preloader');

// Скрываем прелоадер при обычной загрузке
window.addEventListener('load', () => {
  if (pre) pre.style.display = 'none';
});

// Скрываем прелоадер, когда страница возвращается из bfcache
window.addEventListener('pageshow', (event) => {
  if (pre) pre.style.display = 'none';
});

// Показываем при переходе по внутренним ссылкам
document.addEventListener('click', e => {
  const a = e.target.closest('a');
  if (a && a.href && a.origin === location.origin) {
    if (pre) pre.style.display = 'flex';
  }
});

// Показываем при нажатии F5
window.addEventListener('keydown', e => {
  if (e.key === 'F5') {
    if (pre) pre.style.display = 'flex';
  }
});

// Показываем при любом уходе со страницы (back/forward, Ctrl+R, кнопки браузера и т.п.)
window.addEventListener('beforeunload', (e) => {
  if (pre) pre.style.display = 'flex';
  // не возвращаем строку — просто показываем прелоадер
});
