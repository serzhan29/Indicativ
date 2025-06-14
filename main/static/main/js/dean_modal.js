function showTeachersModal(teachers) {
    const tableBody = document.getElementById("teacherList").querySelector("tbody");
    tableBody.innerHTML = "";

    teachers
        .filter(obj => obj.value > 0)
        .forEach(obj => {
            const row = document.createElement("tr");

            const nameCell = document.createElement("td");
            nameCell.textContent = obj.name;

            const valueCell = document.createElement("td");
            valueCell.textContent = obj.value;
            valueCell.style.textAlign = "right";

            row.appendChild(nameCell);
            row.appendChild(valueCell);
            tableBody.appendChild(row);
        });

    document.getElementById("teacherModal").style.display = "block";
}

function closeModal(event) {
    if (event.target === document.getElementById("teacherModal")) {
        document.getElementById("teacherModal").style.display = "none";
    }
}