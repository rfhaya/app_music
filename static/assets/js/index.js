
let titleText = "Harmony Hub - Your Music, Your Vibe ";
let speed = 300; // kecepatan scroll dalam milidetik

function scrollTitle() {
  document.title = titleText;
  titleText = titleText.substring(1) + titleText.charAt(0); // geser satu karakter ke kiri
  setTimeout(scrollTitle, speed);
}

scrollTitle();

$(document).ready(function () {
  // Toggle menu icon (top-left menu icon)
  $('.mobile-toggle-menu').click(function () {
    $('.wrapper').toggleClass('sidebar-open');
  });

  // Overlay click: close sidebar (mobile)
  $('.overlay').click(function () {
    $('.wrapper').removeClass('sidebar-open');
  });

  // Optional: close mobile sidebar when clicking menu link
  $('.sidebar-wrapper a').click(function () {
    if (window.innerWidth <= 1024) {
      $('.wrapper').removeClass('sidebar-open');
    }
  });

  // Toggle sidebar collapse/expand for desktop
  $('.toggle-icon').click(function () {
    if (window.innerWidth <= 1024) {
      // Kalau mobile: tutup sidebar
      $('.wrapper').removeClass('sidebar-open');
    } else {
      // Kalau desktop: toggle mode kecil
      $('.wrapper').hasClass('toggled')
        ? ($('.wrapper').removeClass('toggled'),
          $('.sidebar-wrapper').off('hover'))
        : ($('.wrapper').addClass('toggled'),
          $('.sidebar-wrapper').hover(
            function () { $('.wrapper').addClass('sidebar-hovered') },
            function () { $('.wrapper').removeClass('sidebar-hovered') }
          ));
    }
  });
});