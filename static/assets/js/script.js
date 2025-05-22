let currentIndex = 0
const rows = document.querySelectorAll('.song-row')

function highlightRow(index) {
  rows.forEach((row, i) => {
    row.classList.toggle('active', i === index)
  })
}

function playNextSong() {
  currentIndex = (currentIndex + 1) % rows.length
  highlightRow(currentIndex)
}

// Simulasikan auto-next setiap 5 detik
setInterval(playNextSong, 5000)

function showAlbum(albumId) {
  document.getElementById('albumGrid').classList.add('d-none')
  document.getElementById('albumDetail').classList.remove('d-none')

  document
    .querySelectorAll('.album-panel')
    .forEach(panel => panel.classList.add('d-none'))
  document.getElementById(albumId).classList.remove('d-none')
}

function backToGridAlbum() {
  document.getElementById('albumGrid').classList.remove('d-none')
  document.getElementById('albumDetail').classList.add('d-none')
}

function goBack() {
  document.getElementById('artist-detail').style.display = 'none'
  document.getElementById('artist-list').style.display = 'flex'
}

// $(document).ready(function () {
//   $('#toggle-genres').click(function () {
//     $('#more-genres').toggleClass('show');
//     $(this).html($('#more-genres').hasClass('show') ? '&hellip; Less' : '&hellip; More');
//   });
// });

window.addEventListener("scroll", () => {
  if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 300) {
    loadArtists();
  }
});

window.addEventListener("DOMContentLoaded", loadArtists);
