    document.querySelectorAll('.open-deadline-modal').forEach(button => {
        button.addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('deadlineModal'));
            document.getElementById('deadline-item-id').value = button.dataset.id;
            document.getElementById('deadline-item-type').value = button.dataset.type;
            modal.show();
        });
    });

    document.getElementById('deadlineForm').addEventListener('submit', function(e) {
        e.preventDefault();

        const itemId = this.item_id.value;
        const itemType = this.item_type.value;
        const month = this.month.value;
        const year = this.year.value;

        fetch('{% url "update_deadline" %}', {
            method: 'POST',
            headers: {
                'X-CSRFToken': '{{ csrf_token }}',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ id: itemId, type: itemType, month: month, year: year })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();  // Обновим страницу
            } else {
                alert('Ошибка при сохранении даты.');
            }
        });
    });