/* ==========================================================================
   Chatbox AI - Admin Panel Logic
   ========================================================================== */
(function () {
  "use strict";

  const TOKEN_KEY = "cb-token";
  const token = localStorage.getItem(TOKEN_KEY);

  if (!token) {
    window.location.href = "/";
    return;
  }

  // DOM Elements
  const sidebar = document.querySelector(".admin-sidebar");
  const navItems = document.querySelectorAll(".admin-nav-item");
  const sections = document.querySelectorAll(".admin-section");
  const logoutBtn = document.getElementById("admin-logout");
  const userInfoEl = document.getElementById("admin-user-info");
  const pageTitleEl = document.getElementById("admin-page-title");

  // Stats elements
  const statUsers = document.getElementById("stat-users");
  const statConversations = document.getElementById("stat-conversations");
  const statMessages = document.getElementById("stat-messages");
  const statAdmins = document.getElementById("stat-admins");

  // Tables
  const usersTableBody = document.getElementById("users-table-body");
  const conversationsTableBody = document.getElementById(
    "conversations-table-body",
  );

  // Filters
  const userSearch = document.getElementById("user-search");
  const userRoleFilter = document.getElementById("user-role-filter");
  const convSearch = document.getElementById("conv-search");

  // Modals
  const roleModal = document.getElementById("role-modal");
  const roleModalUsername = document.getElementById("role-modal-username");
  const roleModalSelect = document.getElementById("role-modal-select");

  // State
  let currentSection = "dashboard";
  let editingUserId = null;

  // Init
  async function init() {
    try {
      const res = await fetch("/api/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();

      if (!res.ok || !data.user) {
        localStorage.removeItem(TOKEN_KEY);
        window.location.href = "/";
        return;
      }

      if (data.user.role !== "admin") {
        alert("صلاحية الوصول مخصصة للمشرفين فقط");
        localStorage.removeItem(TOKEN_KEY);
        window.location.href = "/";
        return;
      }

      userInfoEl.textContent = `${data.user.username} (${data.user.email})`;
      loadStats();
      loadUsers();
      loadConversations();
    } catch (err) {
      console.error(err);
      localStorage.removeItem(TOKEN_KEY);
      window.location.href = "/";
    }
  }

  /* ----- Navigation ----- */
  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      const section = item.dataset.section;
      goToSection(section);
    });
  });

  function goToSection(section) {
    currentSection = section;

    // Update nav
    navItems.forEach((item) => {
      item.classList.toggle("active", item.dataset.section === section);
    });

    // Update sections
    sections.forEach((sec) => {
      sec.classList.toggle("hidden", sec.id !== `section-${section}`);
      sec.classList.toggle("active", sec.id === `section-${section}`);
    });

    // Update title
    const titles = {
      dashboard: "لوحة المعلومات",
      users: "إدارة المستخدمين",
      conversations: "جميع المحادثات",
      settings: "إعدادات النظام",
    };
    pageTitleEl.textContent = titles[section] || "لوحة التحكم";

    // Load data
    if (section === "dashboard") loadStats();
    if (section === "users") loadUsers();
    if (section === "conversations") loadConversations();
  }

  /* ----- API Helpers ----- */
  async function api(endpoint, options = {}) {
    const res = await fetch(endpoint, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });
    return res;
  }

  /* ----- Stats ----- */
  async function loadStats() {
    try {
      const res = await api("/api/admin/stats");
      const data = await res.json();
      statUsers.textContent = data.users;
      statConversations.textContent = data.conversations;
      statMessages.textContent = data.messages;
      statAdmins.textContent = data.admins;
    } catch (err) {
      console.error("Failed to load stats:", err);
    }
  }

  /* ----- Users ----- */
  async function loadUsers() {
    try {
      const res = await api("/api/admin/users");
      const users = await res.json();

      const search = userSearch.value.toLowerCase();
      const roleFilter = userRoleFilter.value;

      const filtered = users.filter((u) => {
        const matchSearch =
          u.username.toLowerCase().includes(search) ||
          u.email.toLowerCase().includes(search);
        const matchRole = roleFilter === "all" || u.role === roleFilter;
        return matchSearch && matchRole;
      });

      usersTableBody.innerHTML = "";
      filtered.forEach((user, index) => {
        const tr = document.createElement("tr");
        const isSelf = user.id === getCurrentUserId();
        tr.innerHTML = `
          <td>${index + 1}</td>
          <td>${escapeHtml(user.username)}</td>
          <td>${escapeHtml(user.email)}</td>
          <td>
            <span class="role-badge ${user.role}">${user.role}</span>
          </td>
          <td>${formatDate(user.created_at)}</td>
          <td>
            <div style="display:flex; gap:6px; justify-content:flex-end;">
              ${!isSelf ? `<button class="btn-danger" onclick="adminApp.deleteUser(${user.id})" title="حذف">حذف</button>` : `<span style="color:#6b7280; font-size:0.8rem;">أنت</span>`}
              <button class="btn btn-outline" style="padding:4px 10px; font-size:0.8rem;" onclick="adminApp.openRoleModal(${user.id}, '${escapeHtml(user.username)}', '${user.role}')" title="تغيير الدور">
                ${user.role === "admin" ? "تنزيل إلى مستخدم" : "ترقية إلى مشرف"}
              </button>
            </div>
          </td>
        `;
        usersTableBody.appendChild(tr);
      });
    } catch (err) {
      console.error("Failed to load users:", err);
    }
  }

  async function deleteUser(userId) {
    if (!confirm("هل أنت متأكد من حذف هذا المستخدم؟")) return;
    try {
      const res = await api(`/api/admin/users/${userId}`, { method: "DELETE" });
      if (res.ok) {
        loadUsers();
        loadStats();
      } else {
        const data = await res.json();
        alert(data.error || "فشل في حذف المستخدم");
      }
    } catch (err) {
      console.error(err);
      alert("حدث خطأ أثناء الحذف");
    }
  }

  /* ----- Role Modal ----- */
  async function openRoleModal(userId, username, currentRole) {
    editingUserId = userId;
    roleModalUsername.textContent = username;
    roleModalSelect.value = currentRole;
    roleModal.hidden = false;
  }

  function closeRoleModal() {
    roleModal.hidden = true;
    editingUserId = null;
  }

  async function saveRole() {
    if (!editingUserId) return;
    const newRole = roleModalSelect.value;
    try {
      const res = await api(`/api/admin/users/${editingUserId}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role: newRole }),
      });
      if (res.ok) {
        closeRoleModal();
        loadUsers();
        loadStats();
      } else {
        const data = await res.json();
        alert(data.error || "فشل في تحديث الدور");
      }
    } catch (err) {
      console.error(err);
      alert("حدث خطأ أثناء التحديث");
    }
  }

  /* ----- Conversations ----- */
  async function loadConversations() {
    try {
      const res = await api("/api/admin/conversations");
      const convs = await res.json();

      const search = convSearch.value.toLowerCase();
      const filtered = convs.filter((c) => {
        const matchSearch =
          c.username.toLowerCase().includes(search) ||
          c.title.toLowerCase().includes(search) ||
          c.email.toLowerCase().includes(search);
        return matchSearch;
      });

      conversationsTableBody.innerHTML = "";
      filtered.forEach((conv, index) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${index + 1}</td>
          <td>${escapeHtml(conv.username)} (${escapeHtml(conv.email)})</td>
          <td>${escapeHtml(conv.title)}</td>
          <td>${formatDate(conv.created_at)}</td>
          <td>${formatDate(conv.updated_at)}</td>
          <td>
            <button class="btn-danger" onclick="adminApp.deleteConversation(${conv.id})" title="حذف المحادثة">
              حذف
            </button>
          </td>
        `;
        conversationsTableBody.appendChild(tr);
      });
    } catch (err) {
      console.error("Failed to load conversations:", err);
    }
  }

  async function deleteConversation(convId) {
    if (!confirm("هل أنت متأكد من حذف هذه المحادثة؟")) return;
    try {
      const res = await api(`/api/admin/conversations/${convId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        loadConversations();
        loadStats();
      } else {
        const data = await res.json();
        alert(data.error || "فشل في حذف المحادثة");
      }
    } catch (err) {
      console.error(err);
      alert("حدث خطأ أثناء الحذف");
    }
  }

  /* ----- Utilities ----- */
  function getCurrentUserId() {
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload.id;
    } catch {
      return null;
    }
  }

  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function formatDate(isoString) {
    if (!isoString) return "-";
    const d = new Date(isoString);
    return d.toLocaleDateString("ar-SA", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  }

  /* ----- Event Listeners ----- */
  logoutBtn.addEventListener("click", () => {
    localStorage.removeItem(TOKEN_KEY);
    window.location.href = "/";
  });

  userSearch.addEventListener("input", loadUsers);
  userRoleFilter.addEventListener("change", loadUsers);
  convSearch.addEventListener("input", loadConversations);

  // Expose to HTML onclick
  window.adminApp = {
    goToSection,
    deleteUser,
    openRoleModal,
    closeRoleModal,
    saveRole,
    deleteConversation,
  };

  init();
})();
