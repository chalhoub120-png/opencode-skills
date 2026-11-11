/* Optional Supabase auth + per-user cloud sync. Depends on Supabase JS v2 UMD. */
(() => {
  const cfg = window.BOARDSPACE_SUPABASE || {};
  const configured = /^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(cfg.url || "") &&
    cfg.publishableKey && !cfg.publishableKey.startsWith("REPLACE_");
  let client = null;
  let currentUser = null;
  let saveTimer = 0;
  let appReady = false;
  let stateLoadedFor = null;
  let cloudRevision = 0;
  let syncInFlight = false;
  let syncAgain = false;
  let syncConflict = false;
  let suppressNextSave = false;
  let syncReady = false;
  let cloudLoadError = false;
  let sessionGeneration = 0;

  if (configured && window.supabase?.createClient) {
    client = window.supabase.createClient(cfg.url, cfg.publishableKey, {
      auth: { storage: window.sessionStorage, persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
    });
  }

  const byId = (id) => document.getElementById(id);
  const status = (text) => { const el = byId("cloudStatus"); if (el) el.textContent = text; };

  async function restoreCloudState(user, generation) {
    if (!window.boardspaceState || !user) return;
    const { data, error } = await client.from("boardspace_state").select("state,revision").eq("user_id", user.id).maybeSingle();
    if (generation !== sessionGeneration || currentUser?.id !== user.id) return;
    if (error) throw error;
    syncConflict = false;
    if (data?.state) {
      cloudRevision = data.revision;
      suppressNextSave = true;
      window.boardspaceState.replace(data.state);
      syncReady = true;
      cloudLoadError = false;
      status("Cloud synced");
    } else {
      // Never seed a new account from another account's browser-local data.
      cloudRevision = 0;
      suppressNextSave = true;
      window.boardspaceState.reset();
      syncReady = true;
      cloudLoadError = false;
      await saveCloudState();
      status("New account cloud board created");
    }
  }

  async function saveCloudState() {
    if (!client || !currentUser || !appReady || !window.boardspaceState || !syncReady || syncConflict) return;
    if (syncInFlight) { syncAgain = true; return; }
    syncInFlight = true;
    const saveGeneration = sessionGeneration;
    const snapshot = window.boardspaceState.get();
    try {
      const { data, error } = await client.rpc("save_boardspace_state", {
        p_state: snapshot,
        p_expected_revision: cloudRevision,
      });
      if (error) throw error;
      if (saveGeneration !== sessionGeneration) return;
      const result = Array.isArray(data) ? data[0] : data;
      if (!result?.saved) {
        cloudRevision = result?.current_revision ?? cloudRevision;
        syncConflict = true;
        status("Conflict: another session saved changes. Reload cloud or export your local board.");
        renderAuth();
        return;
      }
      cloudRevision = result.current_revision;
      status("All changes saved");
      if (JSON.stringify(snapshot) !== JSON.stringify(window.boardspaceState.get())) syncAgain = true;
    } catch (error) {
      if (saveGeneration !== sessionGeneration) return;
      console.error("Cloud sync failed", error);
      status("Cloud sync failed — local copy kept; retry when online");
    } finally {
      syncInFlight = false;
      if (syncAgain) {
        syncAgain = false;
        clearTimeout(saveTimer);
        saveTimer = setTimeout(() => void saveCloudState(), 250);
      }
    }
  }

  async function reloadCloudState() {
    if (!client || !currentUser) return;
    status("Reloading cloud board…");
    try {
      const { data, error } = await client.from("boardspace_state").select("state,revision").eq("user_id", currentUser.id).single();
      if (error) throw error;
      cloudRevision = data.revision;
      syncConflict = false;
      suppressNextSave = true;
      window.boardspaceState.replace(data.state);
      status("Cloud version loaded");
      renderAuth();
    } catch (error) {
      console.error("Cloud reload failed", error);
      status("Could not load cloud version; your local board is unchanged");
    }
  }

  window.boardspaceCloud = {
    ready: Boolean(client),
    markReady() {
      appReady = true;
      if (currentUser && stateLoadedFor !== currentUser.id) void applySession({ user: currentUser });
    },
    scheduleSave() {
      if (suppressNextSave) { suppressNextSave = false; return; }
      if (!currentUser || syncConflict) return;
      status("Syncing…");
      clearTimeout(saveTimer);
      saveTimer = setTimeout(() => void saveCloudState(), 500);
    },
  };

  function renderAuth() {
    const area = byId("cloudAuth");
    if (!area) return;
    if (!client) {
      area.innerHTML = '<span class="cloud-unavailable">Cloud sync needs Supabase configuration</span>';
      status("Local mode"); return;
    }
    if (currentUser) {
      const safeEmail = String(currentUser.email || "Signed in").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
      area.innerHTML = `<span class="cloud-user">${safeEmail}</span>${syncConflict ? '<button id="cloudReload" class="btn-ghost" type="button">Reload cloud</button>' : ''}${cloudLoadError ? '<button id="cloudRetry" class="btn-ghost" type="button">Retry cloud load</button>' : ''}<button id="cloudSignOut" class="btn-ghost" type="button">Sign out</button>`;
      if (syncConflict) byId("cloudReload").addEventListener("click", () => void reloadCloudState());
      if (cloudLoadError) byId("cloudRetry").addEventListener("click", () => {
        if (!confirm("Retry loading the cloud copy? This may replace local edits. Export a backup first if needed.")) return;
        syncReady = false;
        cloudLoadError = false;
        stateLoadedFor = null;
        setWorkspaceBusy(true);
        void applySession({ user: currentUser });
      });
      byId("cloudSignOut").addEventListener("click", async () => {
        const { error } = await client.auth.signOut();
        if (error) status("Sign out failed");
      });
      return;
    }
    area.innerHTML = '<form id="cloudForm" class="cloud-form"><label class="sr-only" for="cloudEmail">Email</label><input id="cloudEmail" type="email" autocomplete="email" maxlength="254" placeholder="Email" required><label class="sr-only" for="cloudPassword">Password</label><input id="cloudPassword" type="password" autocomplete="current-password" minlength="10" maxlength="128" placeholder="Password (10+ chars)" required><button class="btn-primary" type="submit">Sign in</button><button id="cloudSignUp" class="btn-ghost" type="button">Create account</button></form>';
    byId("cloudForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const email = byId("cloudEmail").value.trim();
      const password = byId("cloudPassword").value;
      if (!email || password.length < 10) { status("Enter a valid email and 10+ character password"); return; }
      status("Signing in…");
      const { error } = await client.auth.signInWithPassword({ email, password });
      status(error ? (error.message || "Sign in failed") : "Signed in");
    });
    byId("cloudSignUp").addEventListener("click", async () => {
      const email = byId("cloudEmail").value.trim();
      const password = byId("cloudPassword").value;
      if (!email || password.length < 10) { status("Enter a valid email and 10+ character password"); return; }
      status("Creating account…");
      const { error } = await client.auth.signUp({ email, password });
      status(error ? (error.message || "Sign up failed") : "Check your email to confirm your account");
    });
  }

  function setWorkspaceBusy(isBusy) {
    document.querySelectorAll(".subbar, .layout").forEach((element) => {
      element.inert = isBusy;
      element.setAttribute("aria-busy", String(isBusy));
    });
  }

  if (client) setWorkspaceBusy(true);

  async function applySession(session) {
    const nextUser = session?.user || null;
    if (currentUser?.id !== nextUser?.id) {
      sessionGeneration += 1;
      syncReady = false;
      cloudLoadError = false;
      syncConflict = false;
      cloudRevision = 0;
      stateLoadedFor = null;
      setWorkspaceBusy(Boolean(nextUser));
    }
    currentUser = nextUser;
    renderAuth();
    if (!currentUser) {
      stateLoadedFor = null;
      setWorkspaceBusy(false);
      status(client ? "Local mode · sign in to sync" : "Local mode");
      return;
    }
    if (!appReady || stateLoadedFor === currentUser.id) return;
    stateLoadedFor = currentUser.id;
    status("Loading your cloud board…");
    const generation = sessionGeneration;
    try {
      await restoreCloudState(currentUser, generation);
      if (generation !== sessionGeneration) return;
      setWorkspaceBusy(false);
      renderAuth();
    } catch (error) {
      if (generation !== sessionGeneration) return;
      cloudLoadError = true;
      console.error("Unable to load cloud state", error);
      setWorkspaceBusy(false);
      status("Cloud unavailable — local data is safe; retry before editing cloud data");
      renderAuth();
    }
  }

  if (client) {
    client.auth.onAuthStateChange((_event, session) => { queueMicrotask(() => void applySession(session)); });
    client.auth.getSession().then(({ data, error }) => {
      if (error) { setWorkspaceBusy(false); status("Could not restore session"); return; }
      void applySession(data.session);
    });
  }
  document.addEventListener("DOMContentLoaded", renderAuth);
})();
