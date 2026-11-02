(function () {
  const yearEl = document.getElementById("year");
  if (yearEl) {
    yearEl.textContent = String(new Date().getFullYear());
  }

  const navLinks = Array.from(document.querySelectorAll("[data-nav]"));
  const sections = navLinks
    .map((link) => {
      const id = link.getAttribute("href")?.slice(1);
      return id ? document.getElementById(id) : null;
    })
    .filter(Boolean);

  if (!sections.length || !navLinks.length) {
    return;
  }

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const setActive = (id) => {
    navLinks.forEach((link) => {
      const match = link.getAttribute("href") === `#${id}`;
      link.classList.toggle("is-active", match);
      if (match) {
        link.setAttribute("aria-current", "location");
      } else {
        link.removeAttribute("aria-current");
      }
    });
  };

  if ("IntersectionObserver" in window && !reducedMotion) {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target?.id) {
          setActive(visible.target.id);
        }
      },
      { rootMargin: "-20% 0px -55% 0px", threshold: [0, 0.25, 0.5] }
    );
    sections.forEach((section) => observer.observe(section));
  } else {
    setActive(sections[0].id);
  }

  navLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      const href = link.getAttribute("href");
      if (!href?.startsWith("#")) {
        return;
      }
      const target = document.querySelector(href);
      if (!target) {
        return;
      }
      event.preventDefault();
      target.focus({ preventScroll: reducedMotion });
      target.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
      setActive(target.id);
    });
  });
})();
