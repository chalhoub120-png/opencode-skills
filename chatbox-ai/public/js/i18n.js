const i18n = {
  current: localStorage.getItem("cb-lang") || "en",
  data: {
    en: {
      appTitle: "Chatbox AI",
      login: "Login",
      loginSub: "Welcome back",
      loginBtn: "Login",
      createAccount: "Create Account",
      registerSub: "Join us today",
      registerBtn: "Register",
      noAccount: "Don't have an account?",
      haveAccount: "Already have an account?",
      email: "Email",
      password: "Password",
      username: "Username",
      emailPlaceholder: "you@example.com",
      passwordPlaceholder: "••••••••",
      usernamePlaceholder: "john_doe",
      logout: "Logout",
      modelStatus: "Model Status",
      newChat: "New Chat",
      conversations: "Conversations",
      welcome: "Hello! I'm your AI assistant. How can I help you today?",
      placeholder: "Type your message...",
      send: "Send",
      sending: "Sending...",
      typing: "typing...",
      errorConn: "Sorry, I couldn't connect to the internal model.",
      errorServer: "Sorry, an error occurred: ",
      settings: "Settings",
      adminPanel: "Admin Panel",
      noFile: "No file selected",
      remove: "Remove",
      subtitleEn: "AI Assistant",
      subtitleAr: "المساعد الذكي",
      subtitleLb: "المساعد الذكائي",
    },
    ar: {
      appTitle: "تشات بوكس AI",
      login: "تسجيل الدخول",
      loginSub: "مرحباً بعودتك",
      loginBtn: "تسجيل الدخول",
      createAccount: "إنشاء حساب",
      registerSub: "انضم إلينا اليوم",
      registerBtn: "تسجيل",
      noAccount: "ليس لديك حساب؟",
      haveAccount: "لديك حساب بالفعل؟",
      email: "البريد الإلكتروني",
      password: "كلمة المرور",
      username: "اسم المستخدم",
      emailPlaceholder: "you@example.com",
      passwordPlaceholder: "••••••••",
      usernamePlaceholder: "اسم_المستخدم",
      logout: "تسجيل الخروج",
      modelStatus: "حالة النموذج",
      newChat: "محادثة جديدة",
      conversations: "المحادثات",
      welcome: "مرحباً! أنا مساعدك الذكي. كيف يمكنني مساعدتك اليوم؟",
      placeholder: "اكتب رسالتك هنا...",
      send: "إرسال",
      sending: "جاري الإرسال...",
      typing: "يكتب...",
      errorConn: "عذراً، لم أتمكن من الاتصال بالنموذج الداخلي.",
      errorServer: "عذراً، حدث خطأ: ",
      settings: "الإعدادات",
      adminPanel: "لوحة التحكم",
      noFile: "لم يتم اختيار ملف",
      remove: "إزالة",
      subtitleEn: "المساعد الذكي",
      subtitleAr: "مساعد ذكي",
      subtitleLb: "مساعد ذكائي",
    },
    lb: {
      appTitle: "تشات بوكس AI",
      login: "دخول",
      loginSub: "أهلا بعودتك",
      loginBtn: "دخول",
      createAccount: "حساب جديد",
      registerSub: "انضم إلينا اليوم",
      registerBtn: "تسجيل",
      noAccount: "ما عندك حساب؟",
      haveAccount: "عندك حساب؟",
      email: "الإيميل",
      password: "الباسورد",
      username: "اسم المستخدم",
      emailPlaceholder: "you@example.com",
      passwordPlaceholder: "••••••••",
      usernamePlaceholder: "اسم_المستخدم",
      logout: "تسجيل الخروج",
      modelStatus: "حالة الموديل",
      newChat: "كلام جديد",
      conversations: "المحكي",
      welcome: "مرحبا! أنا مساعدك الذكائي. شو بدك اليوم؟",
      placeholder: "اكتب رسالتك هون...",
      send: "بعت",
      sending: "بعتها...",
      typing: "كيتب...",
      errorConn: "آسف، ما قدرت أصل للموديل الداخلي.",
      errorServer: "آسف، صار خطأ: ",
      settings: "إعدادات",
      adminPanel: "لوحة التحكم",
      noFile: "ما في ملف مختار",
      remove: "أزل",
      subtitleEn: "المساعد الذكائي",
      subtitleAr: "مساعد ذكي",
      subtitleLb: "مساعد ذكائي",
    },
  },
  set(lang) {
    this.current = lang;
    localStorage.setItem("cb-lang", lang);
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "en" ? "ltr" : "rtl";
    this.apply();
  },
  t(key) {
    return this.data[this.current][key] || key;
  },
  apply() {
    document
      .querySelectorAll("[data-i18n]")
      .forEach((el) => (el.textContent = this.t(el.dataset.i18n)));
    document
      .querySelectorAll("[data-i18n-placeholder]")
      .forEach((el) => (el.placeholder = this.t(el.dataset.i18n)));
    document
      .querySelectorAll(".lang-btn")
      .forEach((btn) =>
        btn.classList.toggle("active", btn.dataset.lang === this.current),
      );
    const sub = document.getElementById("chat-subtitle");
    if (sub) {
      const key =
        "subtitle" +
        this.current.charAt(0).toUpperCase() +
        this.current.slice(1);
      sub.textContent = this.t(key);
    }
  },
};
window.i18n = i18n;
