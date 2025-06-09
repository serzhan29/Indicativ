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

// Функция загрузки списка файлов с отображением соавторов
async function loadFiles(reportId) {
  try {
    const res = await fetch(`/get-files/${reportId}/`);
    if (!res.ok) {
      throw new Error(`Ошибка сервера: ${res.status}`);
    }
    const data = await res.json();
    console.log('Ответ сервера:', data); // для отладки

    const list = document.getElementById('uploadedFilesList');
    const count = document.getElementById('fileCount');
    list.innerHTML = '';
    if (data.files.length) {
      data.files.forEach(file => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${file.file_name}</td>
          <td>${file.uploaded_at}</td>
          <td style="text-align: left;">
            ${file.co_authors.length
              ? `<ul class="mb-0 ps-3">${file.co_authors.map(name => `<li>${name}</li>`).join('')}</ul>`
              : '—'}
          </td>

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
  } catch (error) {
    console.error('Ошибка при загрузке файлов:', error);
  }
}

// Открытие модалки при клике на триггер
document.querySelectorAll('.open-file-modal').forEach(btn => {
  btn.addEventListener('click', () => {
    const reportId = btn.dataset.id;
    const type = btn.dataset.type; // 'sub' или 'main'
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
  const form = new FormData(e.target);
  try {
    const res = await fetch(`/get-indicator-files/${reportId}/`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': csrftoken },
      body: form
    });
    if (!res.ok) {
      throw new Error(`Ошибка сервера: ${res.status}`);
    }
    const data = await res.json();
    alert(data.message);
    if (data.success) {
      e.target.reset();
      loadFiles(reportId);
    }
  } catch (error) {
    alert('Ошибка при загрузке файла.');
    console.error(error);
  }
});

// Удаление файла
async function deleteFile(fileId, reportId) {
  if (!confirm('Удалить файл?')) return;
  try {
    const res = await fetch(`/delete-file/${fileId}/`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': csrftoken }
    });
    if (!res.ok) {
      throw new Error(`Ошибка сервера: ${res.status}`);
    }
    const data = await res.json();
    alert(data.message);
    loadFiles(reportId);
  } catch (error) {
    alert('Ошибка при удалении файла.');
    console.error(error);
  }
}