(() => {
  const deck = document.querySelector(".deck");
  const slides = [...document.querySelectorAll(".slide")];
  if (!deck || slides.length === 0) return;

  let current = Math.max(0, Math.min(slides.length - 1, Number(location.hash.slice(1)) - 1 || 0));

  function show(index) {
    current = (index + slides.length) % slides.length;
    slides.forEach((slide, i) => slide.classList.toggle("is-active", i === current));
    history.replaceState(null, "", `#${current + 1}`);
  }

  deck.classList.add("is-ready");
  show(current);

  addEventListener("keydown", (event) => {
    if (["ArrowRight", "PageDown", " "].includes(event.key)) show(current + 1);
    if (["ArrowLeft", "PageUp"].includes(event.key)) show(current - 1);
    if (event.key.toLowerCase() === "f") document.documentElement.requestFullscreen?.();
  });
})();
