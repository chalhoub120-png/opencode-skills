      const STORAGE_KEY = "boardspace-state-v1";
      const LEGACY_STORAGE_KEY = "trello-full-v2";

      const LABEL_DEFS = [
        { id: "green", name: "Done", color: "#61bd4f" },
        { id: "yellow", name: "Warning", color: "#f2d600" },
        { id: "orange", name: "Medium", color: "#ff9f1a" },
        { id: "red", name: "Urgent", color: "#eb5a46" },
        { id: "purple", name: "Design", color: "#c377e0" },
        { id: "blue", name: "To Do", color: "#0079bf" },
        { id: "sky", name: "Info", color: "#00c2e0" },
        { id: "lime", name: "Low", color: "#51e898" },
      ];

      const COVER_COLORS = [
        "",
        "#0079bf",
        "#61bd4f",
        "#f2d600",
        "#ff9f1a",
        "#eb5a46",
        "#c377e0",
        "#00c2e0",
        "#51e898",
        "#172b4d",
        "#ff78cb",
      ];

      let state = loadState();
      let openCard = null;
      let modalReturnFocus = null;
      window.boardspaceState = {
        get: () => state,
        replace(raw) {
          state = normalizeState(raw);
          saveState();
          render();
        },
        reset() {
          state = defaultState();
          saveState();
          render();
        },
      };

      const boardEl = document.getElementById("board");
      const boardTitleEl = document.getElementById("boardTitle");
      const searchInputEl = document.getElementById("searchInput");
      const labelFilterEl = document.getElementById("labelFilter");
      const showArchivedEl = document.getElementById("showArchived");

      function uid() {
        return globalThis.crypto?.randomUUID?.() ||
          `${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
      }

      function defaultState() {
        const boardId = uid();
        const members = [
          { id: uid(), name: "You", initials: "YO", color: "#0079bf" },
          { id: uid(), name: "Sara", initials: "SA", color: "#eb5a46" },
          { id: uid(), name: "Ali", initials: "AL", color: "#61bd4f" },
        ];
        const listTodo = uid(),
          listDoing = uid(),
          listDone = uid();
        const seedCards = [
          {
            id: uid(),
            listId: listTodo,
            boardId,
            title: "Welcome! Open this card",
            description:
              "Double-click any card to edit title, description, labels, due date, checklist, comments, attachments.",
            labels: ["blue", "green"],
            dueDate: "",
            completed: false,
            checklists: [],
            comments: [
              {
                id: uid(),
                author: "You",
                text: "This is a demo comment",
                createdAt: Date.now(),
              },
            ],
            attachments: [],
            members: [members[0].id],
            cover: "#0079bf",
            isArchived: false,
            isFavorite: false,
          },
          {
            id: uid(),
            listId: listTodo,
            boardId,
            title: "Try drag & drop",
            description: "Drag this card to another list.",
            labels: [],
            dueDate: "",
            completed: false,
            checklists: [],
            comments: [],
            attachments: [],
            members: [],
            cover: "",
            isArchived: false,
            isFavorite: false,
          },
          {
            id: uid(),
            listId: listDoing,
            boardId,
            title: "Add checklist & due date",
            description: "",
            labels: ["yellow"],
            dueDate: new Date(Date.now() + 86400000).toISOString().slice(0, 10),
            completed: false,
            checklists: [
              {
                id: uid(),
                title: "Steps",
                items: [
                  { id: uid(), text: "Open card", done: true },
                  { id: uid(), text: "Add checklist", done: false },
                ],
              },
            ],
            comments: [],
            attachments: [],
            members: [members[1].id],
            cover: "",
            isArchived: false,
            isFavorite: false,
          },
          {
            id: uid(), listId: listTodo, boardId,
            title: "Map the customer onboarding journey",
            description: "Document the first 30 days, identify friction points, and share a draft with the team.",
            labels: ["purple", "blue"], dueDate: "", completed: false, checklists: [],
            comments: [], attachments: [], members: [members[0].id], cover: "#c377e0", isArchived: false, isFavorite: false,
          },
          {
            id: uid(), listId: listTodo, boardId,
            title: "Prepare launch announcement",
            description: "Draft the release note, product screenshots, and social copy.",
            labels: ["orange"], dueDate: "", completed: false, checklists: [],
            comments: [], attachments: [], members: [members[2].id], cover: "", isArchived: false, isFavorite: false,
          },
          {
            id: uid(), listId: listDoing, boardId,
            title: "Review dashboard accessibility",
            description: "Check keyboard navigation, focus states, contrast, and screen-reader labels.",
            labels: ["red", "purple"], dueDate: new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10), completed: false,
            checklists: [{ id: uid(), title: "Audit", items: [{ id: uid(), text: "Keyboard-only pass", done: true }, { id: uid(), text: "Contrast review", done: false }, { id: uid(), text: "Screen-reader pass", done: false }] }],
            comments: [{ id: uid(), author: "Sara", text: "I can take the contrast review.", createdAt: Date.now() }],
            attachments: [], members: [members[1].id], cover: "#eb5a46", isArchived: false, isFavorite: false,
          },
          {
            id: uid(), listId: listDoing, boardId,
            title: "Build reusable card components",
            description: "Standardize spacing, interaction states, and metadata across card views.",
            labels: ["blue"], dueDate: "", completed: false, checklists: [],
            comments: [], attachments: [], members: [members[0].id, members[2].id], cover: "", isArchived: false, isFavorite: false,
          },
          {
            id: uid(), listId: listDone, boardId,
            title: "Agree on sprint goals",
            description: "The team aligned on the three outcomes for this sprint.",
            labels: ["green"], dueDate: "", completed: true, checklists: [],
            comments: [], attachments: [], members: [members[0].id, members[1].id], cover: "#61bd4f", isArchived: false, isFavorite: true,
          },
        ];
        return {
          boards: [{ id: boardId, title: "Q4 Product Launch", isFavorite: true }],
          currentBoardId: boardId,
          lists: [
            { id: listTodo, boardId, title: "To Do", isArchived: false },
            { id: listDoing, boardId, title: "Doing", isArchived: false },
            { id: listDone, boardId, title: "Done", isArchived: false },
          ],
          cards: seedCards,
          members,
          filter: { text: "", labelId: "" },
        };
      }

      function loadState() {
        try {
          const current = localStorage.getItem(STORAGE_KEY);
          if (current) return normalizeState(JSON.parse(current));

          // One-time, non-destructive migration from the previous app key.
          const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
          if (legacy) {
            const migrated = normalizeState(JSON.parse(legacy));
            try {
              localStorage.setItem(STORAGE_KEY, JSON.stringify(migrated));
              localStorage.removeItem(LEGACY_STORAGE_KEY);
            } catch (migrationError) {
              console.warn("Local data migration could not be persisted; legacy data was retained.", migrationError);
            }
            return migrated;
          }
          return defaultState();
        } catch (error) {
          console.warn("Saved workspace could not be parsed; starting with sample data.", error);
          return defaultState();
        }
      }

      function saveState() {
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
          window.boardspaceCloud?.scheduleSave();
          return true;
        } catch (error) {
          console.warn("Board data could not be saved locally.", error);
          toast("Storage is full or unavailable. Export your data or free space.");
          return false;
        }
      }

      function currentBoard() {
        return (
          state.boards.find((b) => b.id === state.currentBoardId) ||
          state.boards[0]
        );
      }

      function boardCards(boardId) {
        return state.cards.filter((c) => c.boardId === boardId);
      }

      function boardLists(boardId) {
        return state.lists.filter(
          (l) =>
            l.boardId === boardId &&
            (!showArchivedEl.checked || l.isArchived ? true : !l.isArchived),
        );
      }

      function isOverdue(card) {
        if (!card.dueDate || card.completed) return false;
        return new Date(card.dueDate) < new Date(new Date().toDateString());
      }

      function isDueSoon(card) {
        if (!card.dueDate || card.completed) return false;
        const diff = new Date(card.dueDate) - Date.now();
        return diff >= 0 && diff <= 2 * 86400000;
      }

      function checklistProgress(card) {
        const total = card.checklists.reduce((s, cl) => s + cl.items.length, 0);
        const done = card.checklists.reduce(
          (s, cl) => s + cl.items.filter((i) => i.done).length,
          0,
        );
        return {
          total,
          done,
          pct: total ? Math.round((done / total) * 100) : 0,
        };
      }

      function render() {
        renderBoardSwitch();
        renderSidebar();
        renderBoard();
        renderBoardHeader();
      }

      function renderBoardSwitch() {
        const el = document.getElementById("boardsSwitch");
        el.innerHTML = "";
        state.boards.slice(0, 4).forEach((b) => {
          const btn = document.createElement("button");
          btn.className =
            "board-pill" +
            (b.id === state.currentBoardId ? " active" : "") +
            (b.isFavorite ? " fav" : "");
          btn.textContent = (b.isFavorite ? "★ " : "") + b.title;
          btn.onclick = () => {
            state.currentBoardId = b.id;
            saveState();
            render();
          };
          el.appendChild(btn);
        });
      }

      function renderSidebar() {
        const boardsEl = document.getElementById("sidebarBoards");
        boardsEl.innerHTML = "";
        state.boards.forEach((b) => {
          const row = document.createElement("div");
          row.style.display = "flex";
          row.style.gap = "4px";
          row.style.marginBottom = "4px";
          const btn = document.createElement("button");
          btn.className =
            "board-item" + (b.id === state.currentBoardId ? " active" : "");
          btn.dataset.shortName = b.title.slice(0, 1).toUpperCase() || "B";
          btn.innerHTML = `<span>${escapeHtml(b.title)}</span>`;
          btn.onclick = () => {
            state.currentBoardId = b.id;
            saveState();
            render();
          };
          const star = document.createElement("button");
          star.className = "star" + (b.isFavorite ? " on" : "");
          star.textContent = "★";
          star.title = "Toggle favorite";
          star.style.padding = "6px";
          star.onclick = () => {
            b.isFavorite = !b.isFavorite;
            saveState();
            render();
          };
          row.append(btn, star);
          boardsEl.appendChild(row);
        });

        const mEl = document.getElementById("sidebarMembers");
        mEl.innerHTML = "";
        state.members.forEach((m) => {
          const row = document.createElement("div");
          row.style.display = "flex";
          row.style.alignItems = "center";
          row.style.gap = "8px";
          row.style.marginBottom = "6px";
          const av = document.createElement("span");
          av.className = "avatar";
          av.style.background = m.color;
          av.textContent = m.initials;
          av.title = m.name;
          const name = document.createElement("span");
          name.textContent = m.name;
          name.style.fontSize = "13px";
          const del = document.createElement("button");
          del.className = "icon-btn";
          del.textContent = "✕";
          del.style.color = "#fff";
          del.title = "Remove member";
          del.onclick = () => {
            state.members = state.members.filter((x) => x.id !== m.id);
            saveState();
            render();
          };
          row.append(av, name, del);
          mEl.appendChild(row);
        });

        const top = document.getElementById("topMembers");
        top.innerHTML = "";
        state.members.slice(0, 5).forEach((m) => {
          const s = document.createElement("span");
          s.className = "avatar";
          s.style.background = m.color;
          s.textContent = m.initials;
          s.title = m.name;
          top.appendChild(s);
        });
      }

      function renderBoardHeader() {
        const board = currentBoard();
        if (board) boardTitleEl.value = board.title;
        const count = boardCards(state.currentBoardId).filter(
          (c) => !c.isArchived,
        ).length;
        document.getElementById("cardCount").textContent =
          `${count} cards • ${boardLists(state.currentBoardId).length} lists`;
      }

      function renderBoard() {
        boardEl.innerHTML = "";
        const boardId = state.currentBoardId;
        const lists = state.lists.filter(
          (l) =>
            l.boardId === boardId &&
            (showArchivedEl.checked ? true : !l.isArchived),
        );
        lists.forEach((list) => boardEl.appendChild(renderList(list)));
        boardEl.appendChild(renderAddList());
      }

      function renderList(list) {
        const el = document.createElement("section");
        el.className = "list";
        const cards = boardCards(list.boardId).filter(
          (c) => c.listId === list.id,
        );
        const visible = cards.filter(cardMatchesFilter);

        el.setAttribute("aria-label", `${list.title} list`);
        el.innerHTML = `
    <div class="list-header">
      <input class="list-title" aria-label="List title" value="${escapeHtml(list.title)}" />
      <span class="list-count" aria-label="${visible.length} cards">${visible.length}</span>
      <div class="dropdown">
        <button class="icon-btn" aria-label="List menu">•••</button>
        <div class="menu">
          <button data-act="copy">Copy list</button>
          <button data-act="archive">${list.isArchived ? "Unarchive list" : "Archive list"}</button>
          <button data-act="delete" class="danger">Delete list</button>
        </div>
      </div>
    </div>
    <div class="cards"></div>
    <button class="add-card-btn">+ Add a card</button>`;

        const titleInput = el.querySelector(".list-title");
          titleInput.maxLength = 80;
        titleInput.addEventListener("change", () => {
          list.title = titleInput.value.trim().slice(0, 80) || "Untitled";
          saveState();
        });

        const menuBtn = el.querySelector(".icon-btn");
        const menu = el.querySelector(".menu");
        menuBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          menu.classList.toggle("open");
        });
        menu.querySelector("[data-act=copy]").addEventListener("click", () => {
          const copy = {
            id: uid(),
            boardId: list.boardId,
            title: list.title + " (copy)",
            isArchived: false,
          };
          state.lists.splice(state.lists.indexOf(list) + 1, 0, copy);
          cards.forEach((c) =>
            state.cards.push({ ...c, id: uid(), listId: copy.id }),
          );
          saveState();
          render();
          toast("List copied");
        });
        menu
          .querySelector("[data-act=archive]")
          .addEventListener("click", () => {
            list.isArchived = !list.isArchived;
            saveState();
            render();
          });
          menu
          .querySelector("[data-act=delete]")
          .addEventListener("click", () => {
            if (!confirm(`Delete “${list.title}” and all its cards? This cannot be undone.`)) return;
            state.lists = state.lists.filter((l) => l.id !== list.id);
            state.cards = state.cards.filter((c) => c.listId !== list.id);
            saveState();
            render();
            toast("List deleted");
          });

        const cardsEl = el.querySelector(".cards");
        if (visible.length === 0) {
          cardsEl.innerHTML = `<div class="empty">${state.filter.text || state.filter.labelId ? "No matching cards" : "No cards yet"}</div>`;
        } else {
          visible.forEach((card) => cardsEl.appendChild(renderCard(card)));
        }
        setupDropZone(cardsEl, list);
        el.querySelector(".add-card-btn").addEventListener("click", () =>
          startAddCard(list, cardsEl),
        );
        return el;
      }

      function cardMatchesFilter(card) {
        if (card.isArchived && !showArchivedEl.checked) return false;
        if (card.isArchived && showArchivedEl.checked) {
          /* show */
        }
        const q = state.filter.text.toLowerCase();
        if (
          q &&
          !(
            card.title.toLowerCase().includes(q) ||
            (card.description || "").toLowerCase().includes(q)
          )
        )
          return false;
        if (state.filter.labelId && !card.labels.includes(state.filter.labelId))
          return false;
        return true;
      }

      function renderCard(card) {
        const el = document.createElement("article");
        el.className = "card";
        el.draggable = true;
        el.tabIndex = 0;
        el.setAttribute("role", "button");
        el.setAttribute("aria-label", `Open card: ${card.title}`);
        el.dataset.cardId = card.id;
        const coverColor = safeColor(card.cover);
        const cover = coverColor
          ? `<div class="cover" style="background:${coverColor}"></div>`
          : "";
        const labels = card.labels
          .map((id) => {
            const def = LABEL_DEFS.find((l) => l.id === id);
            return def
              ? `<span class="label" title="${def.name}" style="background:${def.color}"></span>`
              : "";
          })
          .join("");

        const prog = checklistProgress(card);
        let badges = "";
        if (card.dueDate) {
          const cls = card.completed
            ? "due completed"
            : isOverdue(card)
              ? "due overdue"
              : "due";
          badges += `<span class="badge ${cls}">📅 ${escapeHtml(card.dueDate)}</span>`;
        }
        if (prog.total)
          badges += `<span class="badge">☑ ${prog.done}/${prog.total}</span>`;
        if (card.comments.length)
          badges += `<span class="badge">💬 ${card.comments.length}</span>`;
        if (card.attachments.length)
          badges += `<span class="badge">📎 ${card.attachments.length}</span>`;
        if (card.isArchived) badges += `<span class="badge">Archived</span>`;
        if (card.isFavorite) badges += `<span class="badge">★</span>`;

        const members = card.members
          .map((id) => state.members.find((m) => m.id === id))
          .filter(Boolean)
          .map(
            (m) =>
              `<span class="avatar" style="background:${safeColor(m.color)}" title="${escapeHtml(m.name)}">${escapeHtml(m.initials)}</span>`,
          )
          .join("");

        el.innerHTML = `${cover}<div class="card-body">
    ${labels ? `<div class="card-labels">${labels}</div>` : ""}
    <div class="card-title">${escapeHtml(card.title)}</div>
    ${badges || members ? `<div class="card-meta">${badges}${members ? `<span class="card-members">${members}</span>` : ""}</div>` : ""}
  </div>`;

        el.addEventListener("click", () => openCardModal(card.id));
        el.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openCardModal(card.id);
          }
        });
        el.addEventListener("dragstart", (e) => {
          e.dataTransfer.setData("text/plain", card.id);
          e.dataTransfer.effectAllowed = "move";
          el.classList.add("dragging");
        });
        el.addEventListener("dragend", () => el.classList.remove("dragging"));
        el.addEventListener("dragover", (e) => {
          e.preventDefault();
          el.classList.add("drag-over");
        });
        el.addEventListener("dragleave", () =>
          el.classList.remove("drag-over"),
        );
        el.addEventListener("drop", (e) => {
          e.preventDefault();
          el.classList.remove("drag-over");
          const draggedId = e.dataTransfer.getData("text/plain");
          moveCard(draggedId, card.listId, card.id);
        });
        return el;
      }

      function setupDropZone(cardsEl, list) {
        cardsEl.addEventListener("dragover", (e) => e.preventDefault());
        cardsEl.addEventListener("drop", (e) => {
          e.preventDefault();
          if (e.target.closest(".card")) return;
          const draggedId = e.dataTransfer.getData("text/plain");
          moveCard(draggedId, list.id);
        });
      }

      function moveCard(cardId, toListId, beforeCardId = null) {
        const card = state.cards.find((c) => c.id === cardId);
        if (!card) return;
        if (!state.lists.some((list) => list.id === toListId && list.boardId === card.boardId)) return;
        if (beforeCardId === cardId) return;
        card.listId = toListId;
        const cardIndex = state.cards.indexOf(card);
        state.cards.splice(cardIndex, 1);
        const targetIndex = beforeCardId
          ? state.cards.findIndex((candidate) => candidate.id === beforeCardId && candidate.listId === toListId)
          : -1;
        if (targetIndex >= 0) {
          state.cards.splice(targetIndex, 0, card);
        } else {
          const listCards = state.cards.filter((candidate) => candidate.listId === toListId);
          const lastIndex = listCards.length ? state.cards.indexOf(listCards[listCards.length - 1]) : -1;
          state.cards.splice(lastIndex + 1, 0, card);
        }
        saveState();
        render();
      }

      function startAddCard(list, cardsEl) {
        if (cardsEl.querySelector("textarea")) return;
        const textarea = document.createElement("textarea");
        textarea.className = "card-editor";
        textarea.rows = 3;
        textarea.maxLength = 200;
        textarea.setAttribute("aria-label", "New card title");
        textarea.placeholder = "Enter card title...";
        cardsEl.appendChild(textarea);
        textarea.focus();
        const actions = document.createElement("div");
        actions.className = "card-actions";
        actions.innerHTML = `<button class="btn-primary">Add card</button><button class="btn-ghost">Cancel</button>`;
        cardsEl.appendChild(actions);
        const cleanup = () => {
          textarea.remove();
          actions.remove();
        };
        actions.children[1].onclick = cleanup;
        actions.children[0].onclick = () => {
          const title = textarea.value.trim();
          if (!title) return;
          state.cards.push({
            id: uid(),
            listId: list.id,
            boardId: list.boardId,
            title,
            description: "",
            labels: [],
            dueDate: "",
            completed: false,
            checklists: [],
            comments: [],
            attachments: [],
            members: [],
            cover: "",
            isArchived: false,
            isFavorite: false,
          });
          saveState();
          render();
        };
        textarea.addEventListener("keydown", (e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            actions.children[0].click();
          }
          if (e.key === "Escape") cleanup();
        });
      }

      function renderAddList() {
        const wrapper = document.createElement("div");
        wrapper.style.minWidth = "260px";
        wrapper.innerHTML = `<button class="add-list-btn">+ Add another list</button>`;
        wrapper.querySelector("button").onclick = () => startAddList(wrapper);
        return wrapper;
      }

      function startAddList(wrapper) {
        wrapper.innerHTML = `<div class="list" style="background:#fff">
    <input class="list-title" maxlength="80" aria-label="New list title" placeholder="Enter list title..." style="margin-bottom:8px" />
    <div class="card-actions"><button class="btn-primary">Add list</button><button class="btn-ghost">Cancel</button></div></div>`;
        const input = wrapper.querySelector("input");
        input.focus();
        wrapper.querySelector(".btn-ghost").onclick = render;
        wrapper.querySelector(".btn-primary").onclick = () => {
          state.lists.push({
            id: uid(),
            boardId: state.currentBoardId,
            title: input.value.trim().slice(0, 80) || "Untitled",
            isArchived: false,
          });
          saveState();
          render();
        };
        input.addEventListener("keydown", (e) => {
          if (e.key === "Enter") wrapper.querySelector(".btn-primary").click();
          if (e.key === "Escape") render();
        });
      }

      /* Card Modal */
      function getCard(cardId) {
        return state.cards.find((c) => c.id === cardId);
      }

      function openCardModal(cardId) {
        const card = getCard(cardId);
        if (!card) return;
        const modal = document.getElementById("cardModal");
        if (!modal.classList.contains("open")) modalReturnFocus = document.activeElement;
        openCard = cardId;
        const body = document.getElementById("modalBody");
        const list = state.lists.find((l) => l.id === card.listId);

        const listOptions = state.lists
          .filter((candidate) => candidate.boardId === card.boardId && !candidate.isArchived)
          .map((candidate) => `<option value="${candidate.id}" ${candidate.id === card.listId ? "selected" : ""}>${escapeHtml(candidate.title)}</option>`)
          .join("");
        const dueChecked = card.completed ? "checked" : "";
        const dueDateVal = card.dueDate || "";
        const labelsPicker = LABEL_DEFS.map((l) => {
          const sel = card.labels.includes(l.id) ? " sel" : "";
          return `<button class="swatch${sel}" data-label="${l.id}" title="${l.name}" style="background:${l.color}"></button>`;
        }).join("");

        const membersPicker = state.members
          .map((m) => {
            const sel = card.members.includes(m.id);
            return `<button class="side-btn" data-member="${m.id}" style="${sel ? "outline:2px solid #0079bf" : ""}"><span class="avatar" style="background:${safeColor(m.color)}">${escapeHtml(m.initials)}</span> ${escapeHtml(m.name)}</button>`;
          })
          .join("");

        const coverPicker = COVER_COLORS.map((c) => {
          const sel = card.cover === c ? " sel" : "";
          return `<button class="swatch${sel}" data-cover="${c}" style="background:${c || "#fff"}" title="${c || "None"}"></button>`;
        }).join("");

        const checklistsHtml = card.checklists
          .map((cl) => {
            const items = cl.items
              .map(
                (it) =>
                  `<label class="check-item ${it.done ? "done" : ""}"><input type="checkbox" data-check="${cl.id}" data-item="${it.id}" ${it.done ? "checked" : ""} /><span style="flex:1">${escapeHtml(it.text)}</span><button class="icon-btn" data-del-item="${it.id}" data-checklist="${cl.id}">✕</button></label>`,
              )
              .join("");
            const prog = cl.items.length
              ? Math.round(
                  (cl.items.filter((i) => i.done).length / cl.items.length) *
                    100,
                )
              : 0;
            return `<div class="checklist">
      <div class="checklist-head"><span>${escapeHtml(cl.title)} — ${prog}%</span><button class="icon-btn" data-del-checklist="${cl.id}">Delete</button></div>
      <div class="progress"><div class="progress-fill" style="width:${prog}%"></div></div>
      ${items}
      <div style="display:flex;gap:6px;margin-top:6px"><input data-new-item="${cl.id}" maxlength="300" placeholder="Add an item..." style="flex:1;padding:6px;border-radius:6px;border:1px solid #dfe1e6" /><button class="btn-primary" data-add-item="${cl.id}">Add</button></div>
    </div>`;
          })
          .join("");

        const commentsHtml = card.comments
          .map(
            (cm) =>
              `<div class="comment"><div class="comment-head">${escapeHtml(cm.author)}<span class="comment-time">${new Date(cm.createdAt).toLocaleString()}</span></div><div>${escapeHtml(cm.text)}</div></div>`,
          )
          .join("");

        const attachmentsHtml =
          card.attachments
            .filter((a) => safeUrl(a.url))
            .map(
              (a) =>
                `<a href="${escapeHtml(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer">${escapeHtml(a.name)} ↗</a><button class="icon-btn" data-del-att="${a.id}">Remove</button>`,
            )
            .join("") ||
          "<div style='color:#5e6c84;font-size:13px'>No attachments</div>";

        body.innerHTML = `
    <div class="modal-cover" style="background:${safeColor(card.cover) || "#0079bf"}">
      <button class="modal-close" id="closeModal">✕</button>
    </div>
    <div class="modal-content">
      <div class="modal-main">
        <div style="color:#5e6c84;font-size:13px">in list <b>${escapeHtml(list?.title || "")}</b></div>
        <input class="modal-title" id="modalTitle" maxlength="200" aria-label="Card title" value="${escapeHtml(card.title)}" />
        <div class="section"><h4>📝 Description</h4><textarea id="modalDesc" class="desc-box" maxlength="4000" placeholder="Add a more detailed description...">${escapeHtml(card.description || "")}</textarea></div>
        <div class="section"><h4>☑ Checklist</h4><div id="checklistsWrap">${checklistsHtml || "<div style='color:#5e6c84;font-size:13px'>No checklists yet</div>"} </div>
          <div style="display:flex;gap:6px;margin-top:6px"><input id="newCheckTitle" maxlength="120" placeholder="Checklist title..." style="flex:1;padding:6px;border-radius:6px;border:1px solid #dfe1e6"/><button id="addChecklistBtn" class="btn-primary">Add checklist</button></div>
        </div>
        <div class="section"><h4>💬 Comments</h4><div id="commentsWrap">${commentsHtml}</div><input id="newComment" class="comment-input" maxlength="1200" placeholder="Write a comment..." /><button id="addCommentBtn" class="btn-primary" style="margin-top:6px">Add comment</button></div>
      </div>
      <div class="modal-side">
        <h4 style="font-size:13px;margin-bottom:6px">ADD TO CARD</h4>
        <div class="section" style="margin-top:0"><h5 style="font-size:12px">Labels</h5><div class="picker" id="labelsPicker">${labelsPicker}</div></div>
        <div class="section"><h5 style="font-size:12px">Members</h5><div id="membersPicker">${membersPicker}</div></div>
        <div class="section"><h5 style="font-size:12px">Dates</h5><label style="display:flex;gap:6px;align-items:center;font-size:13px;margin-bottom:6px"><input type="checkbox" id="dueDone" ${dueChecked} /> Completed</label><input type="date" id="dueDate" value="${escapeHtml(dueDateVal)}" style="width:100%;padding:6px;border-radius:6px;border:1px solid #dfe1e6" /></div>
        <div class="section"><h5 style="font-size:12px">Cover</h5><div class="picker" id="coverPicker">${coverPicker}</div></div>
        <div class="section"><h5 style="font-size:12px">Attachments (link)</h5><div class="attachments" id="attList">${attachmentsHtml}</div><input id="attName" maxlength="120" placeholder="Name" style="width:100%;padding:6px;margin-top:6px;border-radius:6px;border:1px solid #dfe1e6"/><input id="attUrl" maxlength="2048" placeholder="https://..." style="width:100%;padding:6px;margin-top:6px;border-radius:6px;border:1px solid #dfe1e6"/><button id="addAttBtn" class="btn-primary" style="margin-top:6px;width:100%">Add link</button></div>
        <div class="section"><label for="moveToList">Move card to list</label><select id="moveToList" class="move-list-select">${listOptions}</select></div>
        <div class="section">
          <button class="side-btn" id="favBtn">${card.isFavorite ? "★ Unfavorite" : "☆ Favorite"}</button>
          <button class="side-btn" id="archiveBtn">${card.isArchived ? "Unarchive" : "Archive"}</button>
          <button class="side-btn danger" id="deleteCardBtn">Delete</button>
        </div>
      </div>
    </div>`;

        modal.classList.add("open");
        modal.setAttribute("aria-hidden", "false");
        body.querySelector("#modalTitle").focus();

        body.querySelector("#closeModal").onclick = closeModal;
        modal.onclick = (e) => {
          if (e.target === modal) closeModal();
        };
        body.querySelector("#modalTitle").addEventListener("change", (e) => {
          card.title = e.target.value.trim().slice(0, 200) || card.title;
          saveState();
          render();
        });
        body.querySelector("#modalDesc").addEventListener("change", (e) => {
          card.description = e.target.value.slice(0, 4000);
          saveState();
          toast("Description saved");
        });

        body.querySelectorAll("#labelsPicker .swatch").forEach((btn) => {
          btn.onclick = () => {
            const id = btn.dataset.label;
            card.labels = card.labels.includes(id)
              ? card.labels.filter((x) => x !== id)
              : [...card.labels, id];
            saveState();
            render();
            openCardModal(card.id);
          };
        });
        body.querySelectorAll("#coverPicker .swatch").forEach((btn) => {
          btn.onclick = () => {
            card.cover = btn.dataset.cover;
            saveState();
            render();
            openCardModal(card.id);
          };
        });
        body.querySelectorAll("#membersPicker [data-member]").forEach((btn) => {
          btn.onclick = () => {
            const id = btn.dataset.member;
            card.members = card.members.includes(id)
              ? card.members.filter((x) => x !== id)
              : [...card.members, id];
            saveState();
            render();
            openCardModal(card.id);
          };
        });
        body.querySelector("#dueDate").addEventListener("change", (e) => {
          card.dueDate = e.target.value;
          saveState();
          render();
        });
        body.querySelector("#dueDone").addEventListener("change", (e) => {
          card.completed = e.target.checked;
          saveState();
          render();
        });

        body.querySelector("#addChecklistBtn").onclick = () => {
          const title =
            body.querySelector("#newCheckTitle").value.trim().slice(0, 120) || "Checklist";
          card.checklists.push({ id: uid(), title, items: [] });
          saveState();
          render();
          openCardModal(card.id);
        };
        body.querySelectorAll("[data-add-item]").forEach((btn) => {
          btn.onclick = () => {
            const cl = card.checklists.find(
              (x) => x.id === btn.dataset.addItem,
            );
            const input = body.querySelector(`[data-new-item="${cl.id}"]`);
            const text = input.value.trim().slice(0, 300);
            if (!text) return;
            cl.items.push({ id: uid(), text, done: false });
            saveState();
            render();
            openCardModal(card.id);
          };
        });
        body.querySelectorAll("[data-del-item]").forEach((btn) => {
          btn.onclick = () => {
            const cl = card.checklists.find(
              (x) => x.id === btn.dataset.checklist,
            );
            cl.items = cl.items.filter((i) => i.id !== btn.dataset.delItem);
            saveState();
            render();
            openCardModal(card.id);
          };
        });
        body.querySelectorAll("[data-del-checklist]").forEach((btn) => {
          btn.onclick = () => {
            card.checklists = card.checklists.filter(
              (x) => x.id !== btn.dataset.delChecklist,
            );
            saveState();
            render();
            openCardModal(card.id);
          };
        });
        body
          .querySelectorAll("input[type=checkbox][data-check]")
          .forEach((box) => {
            box.addEventListener("change", () => {
              const cl = card.checklists.find(
                (x) => x.id === box.dataset.check,
              );
              const item = cl.items.find((i) => i.id === box.dataset.item);
              item.done = box.checked;
              saveState();
              render();
              openCardModal(card.id);
            });
          });

        body.querySelector("#addCommentBtn").onclick = () => {
          const input = body.querySelector("#newComment");
          const text = input.value.trim().slice(0, 1200);
          if (!text) return;
          card.comments.push({
            id: uid(),
            author: "You",
            text,
            createdAt: Date.now(),
          });
          saveState();
          render();
          openCardModal(card.id);
        };
        body.querySelector("#addAttBtn").onclick = () => {
          const name = body.querySelector("#attName").value.trim();
          const url = body.querySelector("#attUrl").value.trim();
          if (!url) return;
          card.attachments.push({ id: uid(), name: name || url, url });
          saveState();
          render();
          openCardModal(card.id);
        };
        body.querySelectorAll("[data-del-att]").forEach((btn) => {
          btn.onclick = () => {
            card.attachments = card.attachments.filter(
              (a) => a.id !== btn.dataset.delAtt,
            );
            saveState();
            render();
            openCardModal(card.id);
          };
        });
        body.querySelector("#moveToList").addEventListener("change", (event) => {
          if (event.target.value === card.listId) return;
          moveCard(card.id, event.target.value);
          openCardModal(card.id);
        });
        body.querySelector("#favBtn").onclick = () => {
          card.isFavorite = !card.isFavorite;
          saveState();
          render();
          openCardModal(card.id);
        };
        body.querySelector("#archiveBtn").onclick = () => {
          card.isArchived = !card.isArchived;
          saveState();
          render();
          closeModal();
        };
        body.querySelector("#deleteCardBtn").onclick = () => {
          if (!confirm(`Delete “${card.title}”? This cannot be undone.`)) return;
          state.cards = state.cards.filter((c) => c.id !== card.id);
          saveState();
          render();
          closeModal();
          toast("Card deleted");
        };
      }

      function closeModal() {
        const modal = document.getElementById("cardModal");
        modal.classList.remove("open");
        modal.setAttribute("aria-hidden", "true");
        openCard = null;
        if (modalReturnFocus instanceof HTMLElement && modalReturnFocus.isConnected) {
          modalReturnFocus.focus();
        }
        modalReturnFocus = null;
      }

      function escapeHtml(s) {
        return String(s ?? "").replace(
          /[&<>"']/g,
          (c) =>
            ({
              "&": "&amp;",
              "<": "&lt;",
              ">": "&gt;",
              '"': "&quot;",
              "'": "&#39;",
            })[c],
        );
      }

      /* Accept only plain hex colors, so imported data cannot inject CSS. */
      function safeColor(v) {
        const s = String(v ?? "").trim();
        return /^#[0-9a-fA-F]{3,8}$/.test(s) ? s : "";
      }

      /* Parse and cap links at the trust boundary; reject script and malformed schemes. */
      function safeUrl(v) {
        const value = String(v ?? "").trim();
        if (!value || value.length > 2048) return "";
        try {
          const url = new URL(value);
          if ((url.protocol === "https:" || url.protocol === "http:") && url.hostname && !url.username && !url.password) return url.href;
          if (url.protocol === "mailto:" && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(url.pathname)) return value;
        } catch (_) {
          return "";
        }
        return "";
      }

      function asArray(v) {
        return Array.isArray(v) ? v : [];
      }

      function asText(v) {
        if (typeof v === "string") return v.slice(0, 4000);
        if (typeof v === "number" || typeof v === "boolean") return String(v);
        return "";
      }

      // IDs are interpolated into data-* attributes and selectors; constrain them at the boundary.
      function safeId(value) {
        const id = asText(value);
        return /^[A-Za-z0-9_-]{1,80}$/.test(id) ? id : "";
      }

      function assertUniqueIds(records, entityName) {
        const ids = records.map((record) => record.id);
        if (new Set(ids).size !== ids.length) {
          throw new Error(`Duplicate ${entityName} identifiers`);
        }
      }

      /* Rebuild state from untrusted JSON (localStorage or imported file). */
      function normalizeState(raw) {
        if (!raw || typeof raw !== "object")
          throw new Error("Invalid board file");
        if (!Array.isArray(raw.boards) || !raw.boards.length) {
          throw new Error("Invalid board file");
        }
        if (raw.boards.length > 100 || (Array.isArray(raw.lists) && raw.lists.length > 1000) ||
            (Array.isArray(raw.cards) && raw.cards.length > 5000) ||
            (Array.isArray(raw.members) && raw.members.length > 200)) {
          throw new Error("Board file exceeds supported record limits");
        }

        const boards = raw.boards
          .filter((b) => b && typeof b === "object" && safeId(b.id))
          .map((b) => ({
            id: safeId(b.id),
            title: asText(b.title) || "Untitled",
            isFavorite: Boolean(b.isFavorite),
          }));
        if (!boards.length) throw new Error("Invalid board file");
        assertUniqueIds(boards, "board");
        const boardIds = new Set(boards.map((board) => board.id));

        const lists = asArray(raw.lists)
          .filter((l) => l && typeof l === "object" && safeId(l.id) && boardIds.has(safeId(l.boardId)))
          .map((l) => ({
            id: safeId(l.id),
            boardId: safeId(l.boardId),
            title: asText(l.title) || "Untitled",
            isArchived: Boolean(l.isArchived),
          }));
        assertUniqueIds(lists, "list");
        const listById = new Map(lists.map((list) => [list.id, list]));

        const cards = asArray(raw.cards)
          .filter((c) => {
            if (!c || typeof c !== "object" || !safeId(c.id) || !safeId(c.listId)) return false;
            const list = listById.get(safeId(c.listId));
            return Boolean(list && list.boardId === safeId(c.boardId));
          })
          .map((c) => ({
            id: safeId(c.id),
            listId: safeId(c.listId),
            boardId: safeId(c.boardId),
            title: asText(c.title),
            description: asText(c.description),
            labels: asArray(c.labels).map(asText).filter(Boolean),
            dueDate: asText(c.dueDate),
            completed: Boolean(c.completed),
            checklists: asArray(c.checklists)
              .filter((cl) => cl && typeof cl === "object" && safeId(cl.id))
              .map((cl) => ({
                id: safeId(cl.id),
                title: asText(cl.title) || "Checklist",
                items: asArray(cl.items)
                  .filter((it) => it && typeof it === "object" && safeId(it.id))
                  .map((it) => ({
                    id: safeId(it.id),
                    text: asText(it.text),
                    done: Boolean(it.done),
                  })),
              })),
            comments: asArray(c.comments)
              .filter((cm) => cm && typeof cm === "object" && safeId(cm.id))
              .map((cm) => ({
                id: safeId(cm.id),
                author: asText(cm.author) || "You",
                text: asText(cm.text),
                createdAt: Number(cm.createdAt) || Date.now(),
              })),
            attachments: asArray(c.attachments)
              .filter((a) => a && typeof a === "object" && safeId(a.id))
              .map((a) => ({
                id: safeId(a.id),
                name: asText(a.name),
                url: safeUrl(a.url),
              })),
            members: asArray(c.members).map(safeId).filter(Boolean),
            cover: safeColor(c.cover),
            isArchived: Boolean(c.isArchived),
            isFavorite: Boolean(c.isFavorite),
          }));
        assertUniqueIds(cards, "card");
        cards.forEach((card) => {
          if (card.checklists.length > 100 || card.comments.length > 500 || card.attachments.length > 200) {
            throw new Error("Card exceeds supported nested record limits");
          }
          assertUniqueIds(card.checklists, "checklist");
          card.checklists.forEach((checklist) => {
            if (checklist.items.length > 500) throw new Error("Checklist exceeds supported item limit");
            assertUniqueIds(checklist.items, "checklist item");
          });
          assertUniqueIds(card.comments, "comment");
          assertUniqueIds(card.attachments, "attachment");
        });

        const members = asArray(raw.members)
          .filter((m) => m && typeof m === "object" && safeId(m.id))
          .map((m) => ({
            id: safeId(m.id),
            name: asText(m.name) || "Member",
            initials: asText(m.initials).slice(0, 3) || "M",
            color: safeColor(m.color) || "#0079bf",
          }));
        assertUniqueIds(members, "member");
        const memberIds = new Set(members.map((member) => member.id));
        cards.forEach((card) => {
          card.members = card.members.filter((memberId) => memberIds.has(memberId));
        });

        const filter =
          raw.filter && typeof raw.filter === "object" ? raw.filter : {};
        return {
          boards,
          currentBoardId: boardIds.has(safeId(raw.currentBoardId)) ? safeId(raw.currentBoardId) : boards[0].id,
          lists,
          cards,
          members,
          filter: {
            text: asText(filter.text),
            labelId: asText(filter.labelId),
          },
        };
      }

      function toast(msg) {
        const t = document.getElementById("toast");
        t.textContent = msg;
        t.classList.add("show");
        setTimeout(() => t.classList.remove("show"), 2200);
      }

      /* Board management */
      function createBoard() {
        const title = prompt("Board title:", "New Board");
        if (title === null) return;
        const id = uid();
        state.boards.push({
          id,
          title: title.trim().slice(0, 120) || "New Board",
          isFavorite: false,
        });
        state.currentBoardId = id;
        state.lists.push(
          { id: uid(), boardId: id, title: "To Do", isArchived: false },
          { id: uid(), boardId: id, title: "Doing", isArchived: false },
          { id: uid(), boardId: id, title: "Done", isArchived: false },
        );
        saveState();
        render();
        toast("Board created");
      }

      function addMember() {
        const name = prompt(
          "Member name:",
          `Member ${state.members.length + 1}`,
        );
        if (!name) return;
        const safeName = name.trim().slice(0, 80);
        if (!safeName) return;
        const initials =
          safeName
            .split(/\s+/)
            .map((w) => w[0])
            .join("")
            .slice(0, 2)
            .toUpperCase() || "M";
        const color = [
          "#0079bf",
          "#eb5a46",
          "#61bd4f",
          "#ff9f1a",
          "#c377e0",
          "#00c2e0",
        ][state.members.length % 6];
        state.members.push({ id: uid(), name: safeName, initials, color });
        saveState();
        render();
        toast("Member added");
      }

      function exportBoard() {
        const blob = new Blob([JSON.stringify({ schemaVersion: 1, ...state }, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "boardspace-export.json";
        a.hidden = true;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        toast("Exported");
      }

      function importBoard(file) {
        const MAX_IMPORT_BYTES = 2 * 1024 * 1024;
        if (!file || file.size > MAX_IMPORT_BYTES) {
          toast("Import file is missing or exceeds the 2 MB limit");
          return;
        }
        const reader = new FileReader();
        reader.onload = () => {
          try {
            const parsed = JSON.parse(reader.result);
            if (parsed.schemaVersion !== undefined && parsed.schemaVersion !== 1) {
              throw new Error("Unsupported export version");
            }
            const importedState = normalizeState(parsed);
            if (!confirm("Replace the current workspace with the validated import? Export a backup first if needed.")) return;
            state = importedState;
            saveState();
            render();
            toast("Import complete");
          } catch (error) {
            console.warn("Board import rejected", error);
            toast("Import failed: invalid or unsupported board file");
          }
        };
        reader.onerror = () => toast("Could not read the selected file");
        reader.onabort = () => toast("File import was cancelled");
        reader.readAsText(file);
      }

      /* Global listeners */
      boardTitleEl.addEventListener("change", () => {
        const board = currentBoard();
        if (!board) return;
        board.title = boardTitleEl.value.trim().slice(0, 120) || "Untitled";
        saveState();
        render();
      });
      searchInputEl.addEventListener("input", () => {
        state.filter.text = searchInputEl.value;
        saveState();
        render();
      });
      labelFilterEl.addEventListener("change", () => {
        state.filter.labelId = labelFilterEl.value;
        saveState();
        render();
      });
      showArchivedEl.addEventListener("change", render);
      document
        .getElementById("createBoardBtn")
        .addEventListener("click", createBoard);
      document
        .getElementById("membersBtn")
        .addEventListener("click", addMember);
      document
        .getElementById("addMemberBtn")
        .addEventListener("click", addMember);

      const menuBtn = document.getElementById("menuBtn");
      const boardMenu = document.getElementById("boardMenu");
      menuBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        boardMenu.classList.toggle("open");
      });
      document.addEventListener("click", (event) => {
        if (event.target.closest(".dropdown")) return;
        document.querySelectorAll(".menu.open").forEach((menu) => menu.classList.remove("open"));
      });
      boardMenu
        .querySelector("[data-action=add-board]")
        .addEventListener("click", createBoard);
      boardMenu
        .querySelector("[data-action=export]")
        .addEventListener("click", exportBoard);
      boardMenu
        .querySelector("[data-action=import]")
        .addEventListener("click", () =>
          document.getElementById("importFile").click(),
        );
      boardMenu
        .querySelector("[data-action=duplicate]")
        .addEventListener("click", () => {
          const board = currentBoard();
          if (!board) return;
          const newId = uid();
          state.boards.push({
            id: newId,
            title: board.title + " (copy)",
            isFavorite: false,
          });
          state.lists
            .filter((l) => l.boardId === board.id)
            .forEach((l) => {
              const newListId = uid();
              state.lists.push({ ...l, id: newListId, boardId: newId });
              state.cards
                .filter((c) => c.listId === l.id)
                .forEach((c) =>
                  state.cards.push({
                    ...c,
                    id: uid(),
                    boardId: newId,
                    listId: newListId,
                  }),
                );
            });
          saveState();
          render();
          toast("Board duplicated");
        });
      boardMenu
        .querySelector("[data-action=reset]")
        .addEventListener("click", () => {
          if (!confirm("Replace the entire workspace with sample data? This affects this browser and the signed-in cloud copy. Export a backup first.")) return;
          state = defaultState();
          saveState();
          render();
          toast("Reset done");
        });
      document.getElementById("importFile").addEventListener("change", (e) => {
        if (e.target.files[0]) importBoard(e.target.files[0]);
        e.target.value = "";
      });

      // label filter options
      LABEL_DEFS.forEach((l) => {
        const o = document.createElement("option");
        o.value = l.id;
        o.textContent = l.name;
        labelFilterEl.appendChild(o);
      });
      if (state.filter.labelId) labelFilterEl.value = state.filter.labelId;
      searchInputEl.value = state.filter.text || "";

      document.addEventListener("keydown", (event) => {
        const modal = document.getElementById("cardModal");
        if (!modal.classList.contains("open")) return;
        if (event.key === "Escape") {
          event.preventDefault();
          closeModal();
          return;
        }
        if (event.key === "Tab") {
          const focusable = [...modal.querySelectorAll('button:not([disabled]), input:not([type="hidden"]):not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])')]
            .filter((element) => element.getClientRects().length > 0);
          if (!focusable.length) { event.preventDefault(); modal.focus(); return; }
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          if (event.shiftKey && (document.activeElement === first || !modal.contains(document.activeElement))) {
            event.preventDefault(); last.focus();
          } else if (!event.shiftKey && (document.activeElement === last || !modal.contains(document.activeElement))) {
            event.preventDefault(); first.focus();
          }
        }
      });

      render();
      window.boardspaceCloud?.markReady();
