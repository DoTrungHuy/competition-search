/**
 * flower 向轻量星尘粒子。仅用于环境层，支持主题更新和完整清理。
 */
(function (global) {
  "use strict";

  var activeStop = null;

  function startParticles(canvas) {
    if (activeStop) activeStop();
    if (!canvas) return function () {};

    var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (reduceMotion.matches) {
      canvas.style.display = "none";
      return function () {};
    }

    canvas.style.display = "";
    var context = canvas.getContext("2d", { alpha: true });
    var particles = [];
    var animationFrame = 0;
    var running = true;

    function particleCount() {
      return window.innerWidth < 720 ? 36 : 64;
    }

    function color() {
      var dark =
        document.documentElement.getAttribute("data-theme") === "dark";
      if (dark) {
        return Math.random() > 0.65 ? "200,180,255" : "180,210,255";
      }
      return Math.random() > 0.65 ? "112,72,170" : "52,86,138";
    }

    function resize() {
      var dpr = Math.min(window.devicePixelRatio || 1, 2.5);
      var width = window.innerWidth;
      var height = window.innerHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = width + "px";
      canvas.style.height = height + "px";
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function initializeParticles() {
      particles = [];
      var width = window.innerWidth;
      var height = window.innerHeight;
      for (var index = 0; index < particleCount(); index += 1) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          radius: Math.random() * 1.8 + 0.4,
          velocityX: (Math.random() - 0.5) * 0.28,
          velocityY: (Math.random() - 0.5) * 0.28,
          alpha: Math.random() * 0.45 + 0.2,
          color: color(),
        });
      }
    }

    function draw() {
      if (!running) return;
      var width = window.innerWidth;
      var height = window.innerHeight;
      context.clearRect(0, 0, width, height);
      particles.forEach(function (particle) {
        particle.x += particle.velocityX;
        particle.y += particle.velocityY;
        if (particle.x < -4) particle.x = width + 4;
        if (particle.x > width + 4) particle.x = -4;
        if (particle.y < -4) particle.y = height + 4;
        if (particle.y > height + 4) particle.y = -4;
        context.beginPath();
        context.fillStyle =
          "rgba(" + particle.color + "," + particle.alpha + ")";
        context.arc(
          particle.x,
          particle.y,
          particle.radius,
          0,
          Math.PI * 2
        );
        context.fill();
      });
      animationFrame = window.requestAnimationFrame(draw);
    }

    function handleResize() {
      resize();
      initializeParticles();
    }

    function handleThemeChange() {
      particles.forEach(function (particle) {
        particle.color = color();
      });
    }

    function handleVisibility() {
      if (document.hidden) {
        window.cancelAnimationFrame(animationFrame);
      } else if (running) {
        animationFrame = window.requestAnimationFrame(draw);
      }
    }

    resize();
    initializeParticles();
    draw();
    window.addEventListener("resize", handleResize);
    document.addEventListener("compsearch:themechange", handleThemeChange);
    document.addEventListener("visibilitychange", handleVisibility);

    function stop() {
      if (!running) return;
      running = false;
      window.cancelAnimationFrame(animationFrame);
      window.removeEventListener("resize", handleResize);
      document.removeEventListener(
        "compsearch:themechange",
        handleThemeChange
      );
      document.removeEventListener("visibilitychange", handleVisibility);
      if (activeStop === stop) activeStop = null;
    }

    activeStop = stop;
    return stop;
  }

  global.CompParticles = { start: startParticles };
})(typeof window !== "undefined" ? window : globalThis);
