/* ==========================================================================
   Chatbox AI Clone — Interactivity
   1. Mobile navbar toggle
   2. Smooth-scroll for anchor links
   3. FAQ accordion
   4. Navbar scroll effect
   ========================================================================== */

(function () {
  "use strict";

  // Mobile navbar toggle
  const navToggle = document.getElementById("nav-toggle");
  const navLinks = document.querySelector(".nav-links");

  if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => {
      const isOpen = navLinks.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", isOpen);
    });

    // Close menu when clicking a link
    navLinks.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        navLinks.classList.remove("open");
        navToggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  // FAQ accordion
  const faqQuestions = document.querySelectorAll(".faq-question");

  faqQuestions.forEach((question) => {
    question.addEventListener("click", () => {
      const item = question.parentElement;
      const answer = item.querySelector(".faq-answer");
      const toggle = item.querySelector(".faq-toggle");
      const isExpanded = question.getAttribute("aria-expanded") === "true";

      // Close all other FAQ items
      faqQuestions.forEach((other) => {
        if (other !== question) {
          other.setAttribute("aria-expanded", "false");
          const otherItem = other.parentElement;
          const otherAnswer = otherItem.querySelector(".faq-answer");
          const otherToggle = otherItem.querySelector(".faq-toggle");
          if (otherAnswer) otherAnswer.hidden = true;
          if (otherToggle) otherToggle.textContent = "+";
        }
      });

      // Toggle current item
      question.setAttribute("aria-expanded", !isExpanded);
      if (answer) answer.hidden = isExpanded;
      if (toggle) toggle.textContent = isExpanded ? "+" : "−";
    });
  });

  // Navbar scroll effect (subtle background change)
  const navbar = document.getElementById("navbar");
  if (navbar) {
    window.addEventListener("scroll", () => {
      if (window.scrollY > 20) {
        navbar.style.background = "rgba(15, 15, 18, 0.95)";
      } else {
        navbar.style.background = "rgba(15, 15, 18, 0.8)";
      }
    });
  }

  // Simple form intercept for newsletter & CTA (demo only)
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const btn = form.querySelector("button[type='submit']");
      const originalText = btn.textContent;
      btn.textContent = "تم الإرسال ✓";
      btn.style.opacity = "0.9";
      setTimeout(() => {
        btn.textContent = originalText;
        btn.style.opacity = "1";
        form.reset();
      }, 1500);
    });
  });
})();
