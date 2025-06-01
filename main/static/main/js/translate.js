  (function(){
    const langs = ['kk','ru','en','tr'];
    const select = document.getElementById('lang-select');
    if (!select) return;

    select.addEventListener('change', () => {
      const newLang = select.value;
      // Разбираем текущий путь
      const parts = window.location.pathname.split('/');
      // Если первый сегмент — существующий код языка, удаляем его
      if (langs.includes(parts[1])) {
        parts.splice(1, 1);
      }
      // Вставляем новый код языка
      parts.splice(1, 0, newLang);
      // Собираем URL
      const newPath = parts.join('/') || '/';
      // Переходим
      window.location.href = newPath + window.location.search;
    });
  })();