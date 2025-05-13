    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll(".editable").forEach(input => {
            input.addEventListener("change", function () {
                let value = this.value.trim();
                let id = this.dataset.id;
                let type = this.dataset.type;

                if (!/^(100|[1-9]?\d?)$/.test(value)) {
                    this.value = this.dataset.defaultValue;
                    return;
                }

                fetch("/update_value/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": "{{ csrf_token }}"
                    },
                    body: JSON.stringify({ id: id, value: value, type: type })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        if (type === "indicator") {
                            updateTotals();
                        }
                        console.log("Значение обновлено");
                    }
                });
            });
        });

        function updateTotals() {
            document.querySelectorAll("tbody tr.main-indicator").forEach(row => {
                let sum = 0;
                let totalCell = row.querySelector(".total-value");

                let nextRow = row.nextElementSibling;
                while (nextRow && nextRow.classList.contains("sub-indicator")) {
                    let input = nextRow.querySelector("input");
                    if (input) {
                        sum += parseFloat(input.value) || 0;
                    }
                    nextRow = nextRow.nextElementSibling;
                }

                if (totalCell) {
                    totalCell.innerText = sum;
                }
            });
        }
    });