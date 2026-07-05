// Kanban board - basit HTML5 drag & drop.
// Not: Durum sadece tarayıcıda (client-side) tutulur, sayfa yenilenince sıfırlanır.
// Kalıcı depolama gerekiyorsa backend'e bir /kanban/save endpoint'i eklenip
// kart durumları veritabanına yazılabilir.

let draggedCard = null;

function drag(event) {
    draggedCard = event.target;
    event.dataTransfer.effectAllowed = "move";
}

function allowDrop(event) {
    event.preventDefault();
}

function dragEnter(event) {
    const column = event.currentTarget;
    column.classList.add("drag-over");
}

function dragLeave(event) {
    const column = event.currentTarget;
    column.classList.remove("drag-over");
}

function drop(event) {
    event.preventDefault();
    const column = event.currentTarget;
    column.classList.remove("drag-over");

    if (draggedCard) {
        const list = column.querySelector(".card-list");
        list.appendChild(draggedCard);
        draggedCard = null;
    }
}

function addManualCard() {
    const input = document.getElementById("new-card-input");
    const title = input.value.trim();
    if (!title) return;

    const card = document.createElement("div");
    card.className = "kanban-card";
    card.draggable = true;
    card.ondragstart = drag;
    card.innerHTML = `<strong>${escapeHtml(title)}</strong>`;

    document.getElementById("todo-list").appendChild(card);
    input.value = "";
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
