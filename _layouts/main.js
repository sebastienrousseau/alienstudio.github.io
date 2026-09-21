(function () {
  'use strict';
  var root = document.documentElement;
  var toggle = document.getElementById('navToggle');
  var menu = document.getElementById('navMenu');
  var mode = document.getElementById('mode-toggle');
  var state = document.getElementById('mode-state');
  var searchSlot = document.getElementById('search-slot');

  function placeSearch() {
    var button = document.getElementById('ssg-search-btn');
    if (!button || !menu) return false;
    var target = searchSlot || menu;
    if (button.parentNode !== target) target.appendChild(button);
    return true;
  }

  function setMenu(open) {
    if (!toggle || !menu) return;
    toggle.setAttribute('aria-expanded', String(open));
    menu.setAttribute('data-open', String(open));
  }

  if (toggle && menu) {
    toggle.addEventListener('click', function () {
      var opening = toggle.getAttribute('aria-expanded') !== 'true';
      if (opening) placeSearch();
      setMenu(opening);
    });
    menu.addEventListener('click', function (event) {
      if (event.target.closest('a')) setMenu(false);
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
        setMenu(false);
        toggle.focus();
      }
    });
    document.addEventListener('click', function (event) {
      if (!menu.contains(event.target) && !toggle.contains(event.target)) setMenu(false);
    });
  }

  if (mode && state) {
    var order = ['system', 'light', 'dark'];
    var labels = { system: 'System', light: mode.dataset.labelLight, dark: mode.dataset.labelDark };
    function current() {
      var value = root.getAttribute('data-theme');
      return value === 'light' || value === 'dark' ? value : 'system';
    }
    function apply(value) {
      if (value === 'system') {
        root.removeAttribute('data-theme');
        try { localStorage.removeItem('theme'); } catch (error) { /* no-op */ }
      } else {
        root.setAttribute('data-theme', value);
        try { localStorage.setItem('theme', value); } catch (error) { /* no-op */ }
      }
      state.textContent = labels[value];
      mode.setAttribute('aria-label', 'Change colour theme: ' + labels[value]);
    }
    var initialTheme = current();
    var initialLabel = labels[initialTheme];
    if (state.textContent !== initialLabel) state.textContent = initialLabel;
    if (mode.getAttribute('aria-label') !== 'Change colour theme: ' + initialLabel) {
      mode.setAttribute('aria-label', 'Change colour theme: ' + initialLabel);
    }
    mode.addEventListener('click', function () {
      apply(order[(order.indexOf(current()) + 1) % order.length]);
    });
  }

  /*
   * SSG adds its search widget after the theme script. Adopt the trigger into
   * the navigation row so it cannot cover adjacent controls or focused page
   * content. On compact layouts it becomes the final control in the disclosed
   * mobile menu instead of floating above the document.
   */
  if (menu) {
    var searchObserver;
    if (!placeSearch() && typeof MutationObserver === 'function') {
      searchObserver = new MutationObserver(function () {
        if (placeSearch()) searchObserver.disconnect();
      });
      searchObserver.observe(document.body, { childList: true, subtree: true });
    }
  }

  var galleryTriggers = Array.prototype.slice.call(document.querySelectorAll('.gallery-trigger'));
  var galleryLightbox = document.getElementById('gallery-lightbox');
  var galleryImage = document.getElementById('gallery-lightbox-image');
  var galleryCaption = document.getElementById('gallery-lightbox-caption');
  var galleryCount = document.getElementById('gallery-lightbox-count');
  var galleryPrevious = document.querySelector('[data-gallery-previous]');
  var galleryNext = document.querySelector('[data-gallery-next]');
  var galleryIndex = 0;

  function setGalleryImage(index) {
    if (!galleryTriggers.length || !galleryImage) return;
    galleryIndex = (index + galleryTriggers.length) % galleryTriggers.length;
    var thumbnail = galleryTriggers[galleryIndex].querySelector('img');
    if (!thumbnail) return;
    galleryImage.src = thumbnail.currentSrc || thumbnail.src;
    galleryImage.alt = thumbnail.alt;
    if (galleryCaption) galleryCaption.textContent = thumbnail.alt;
    if (galleryCount) {
      var countSeparator = String.fromCharCode(32) + 'of' + String.fromCharCode(32);
      galleryCount.textContent = (galleryIndex + 1) + countSeparator + galleryTriggers.length;
    }
  }

  if (galleryLightbox && galleryImage && galleryTriggers.length) {
    galleryTriggers.forEach(function (trigger, index) {
      trigger.addEventListener('click', function () { setGalleryImage(index); });
    });
    if (galleryPrevious) galleryPrevious.addEventListener('click', function () { setGalleryImage(galleryIndex - 1); });
    if (galleryNext) galleryNext.addEventListener('click', function () { setGalleryImage(galleryIndex + 1); });
    galleryLightbox.addEventListener('keydown', function (event) {
      if (event.key === 'Tab') {
        var lightboxControls = Array.prototype.slice.call(galleryLightbox.querySelectorAll('button:not([disabled])'));
        var firstControl = lightboxControls[0];
        var lastControl = lightboxControls[lightboxControls.length - 1];
        if (event.shiftKey && document.activeElement === firstControl) {
          event.preventDefault();
          lastControl.focus();
        } else if (!event.shiftKey && document.activeElement === lastControl) {
          event.preventDefault();
          firstControl.focus();
        }
      }
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        setGalleryImage(galleryIndex - 1);
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault();
        setGalleryImage(galleryIndex + 1);
      }
    });
  }
})();
