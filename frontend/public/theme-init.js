// Apply the saved theme before the first paint so the page never flashes.
// Loaded as a classic blocking script from index.html (inline scripts are blocked by the CSP).
try {
  var savedTheme = localStorage.getItem('theme')
  document.documentElement.dataset.theme = savedTheme === 'light' ? 'light' : 'dark'
} catch (error) {
  document.documentElement.dataset.theme = 'dark'
}
