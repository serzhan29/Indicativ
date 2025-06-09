const pre = document.getElementById('content-preloader');

function hidePreloader() {
  if (pre) pre.style.display = 'none';
}

function showPreloader() {
  if (pre) {
    pre.style.display = 'flex';
    // Через 5 секунд автоматически скрываем, если ещё показан
    setTimeout(() => {
      if (pre.style.display === 'flex') {
        hidePreloader();
      }
    }, 3000);
  }
}

window.addEventListener('load', () => {
  hidePreloader();
});

window.addEventListener('pageshow', () => {
  hidePreloader();
});

document.addEventListener('click', e => {
  const a = e.target.closest('a');
  if (!a || !a.href) return;

  if (a.origin !== location.origin) return;

  const downloadableExtensions = ['.pdf', '.xls', '.xlsx', '.doc', '.docx', '.zip', '.rar'];
  const urlPath = new URL(a.href).pathname.toLowerCase();

  const isDownloadLink = a.hasAttribute('download') || downloadableExtensions.some(ext => urlPath.endsWith(ext));

  if (isDownloadLink) {
    // Не показываем прелоадер при скачивании
    return;
  }

  showPreloader();
});

window.addEventListener('keydown', e => {
  if (e.key === 'F5') {
    showPreloader();
  }
});

window.addEventListener('beforeunload', () => {
  showPreloader();
});
