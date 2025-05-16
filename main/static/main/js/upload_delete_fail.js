  // Получаем CSRF-токен из куки
  function getCookie(name) {
    let value = null;
    document.cookie.split(';').forEach(c => {
      c = c.trim();
      if (c.startsWith(name + '=')) {
        value = decodeURIComponent(c.slice(name.length + 1));
      }
    });
    return value;
  }
  const csrftoken = getCookie('csrftoken');

  // Функция загрузки списка файлов
  async function loadFiles(reportId) {
    const res = await fetch(`/get-files/${reportId}/`);
    const data = await res.json();
    const list = document.getElementById('uploadedFilesList');
    const count = document.getElementById('fileCount');
    list.innerHTML = '';
    if (data.files.length) {
      data.files.forEach(file => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${file.file_name.split('/').pop()}</td>
          <td>${file.uploaded_at}</td>
          <td>
            <a href="${file.file_url}" download class="btn btn-sm btn-success me-1">
              Жүктеу
            </a>
            <button class="btn btn-sm btn-danger"
                    onclick="deleteFile(${file.id}, ${reportId})">
              Жою
            </button>
          </td>`;
        list.appendChild(tr);
      });
      count.textContent = `Барлық файлдар: ${data.files.length}`;
    } else {
      count.textContent = 'Жүктелген файлдар жоқ.';
    }
  }

  // Открытие модалки при клике на триггер
  document.querySelectorAll('.open-file-modal').forEach(btn => {
    btn.addEventListener('click', () => {
      const reportId = btn.dataset.id;
      const type     = btn.dataset.type; // 'sub' или 'main'
      document.getElementById('modalReportId').value = reportId;

      // Передаём в форму тип для бэкенда
      const container = document.getElementById('indicatorFieldContainer');
      container.innerHTML = '';
      if (type === 'sub') {
        container.innerHTML = `<input type="hidden" name="indicator" value="1">`;
      }

      loadFiles(reportId);
      new bootstrap.Modal(document.getElementById('fileModal')).show();
    });
  });

  // Загрузка нового файла
  document.getElementById('fileForm').addEventListener('submit', async e => {
    e.preventDefault();
    const reportId = document.getElementById('modalReportId').value;
    const form    = new FormData(e.target);
    const res     = await fetch(`/get-indicator-files/${reportId}/`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': csrftoken },
      body: form
    });
    const data = await res.json();
    alert(data.message);
    if (data.success) {
      e.target.reset();
      loadFiles(reportId);
    }
  });

  // Удаление файла
  async function deleteFile(fileId, reportId) {
    if (!confirm('Удалить файл?')) return;
    const res = await fetch(`/delete-file/${fileId}/`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': csrftoken }
    });
    const data = await res.json();
    alert(data.message);
    loadFiles(reportId);
  }