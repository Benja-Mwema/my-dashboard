'use strict';
// Filenames carry the content hash. Only the small revision file needs revalidation.
window.AurumDelivery = {
  interval: 15 * 60 * 1000,
  async revision(key) {
    const response = await fetch('delivery/' + key + '.json', {cache: 'no-cache'});
    if (!response.ok) throw Error('Revision unavailable (' + response.status + ')');
    return response.json();
  },
  async read(filename) {
    const response = await fetch('delivery/' + filename, {cache: 'force-cache'});
    if (!response.ok) throw Error('Published data unavailable (' + response.status + ')');
    return response.json();
  }
};

// Full dashboards keep their assets at the site root via <base>. Resolve
// ordinary section links inside the current dashboard after UI tab handlers.
if (document.querySelector('base')) {
  document.addEventListener('click', event => {
    const anchor = event.target.closest('a[href^="#"]');
    if (!anchor || event.defaultPrevented || event.ctrlKey || event.metaKey ||
        event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    location.hash = anchor.hash;
    document.getElementById(anchor.hash.slice(1))?.scrollIntoView();
  });
}
