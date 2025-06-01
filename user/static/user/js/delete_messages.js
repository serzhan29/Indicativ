  // Удалить сообщение через 5 секунд
  setTimeout(function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
      alert.style.transition = 'opacity 0.5s ease';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 500); // полностью убрать из DOM
    });
  }, 5000); // 5000 мс = 5 секунд