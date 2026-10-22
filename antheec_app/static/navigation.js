/* Native details remain keyboard-accessible and work without JavaScript. */
document.querySelectorAll('.main-nav .nav-group').forEach(group => {
  group.addEventListener('toggle', () => {
    if (group.open) document.querySelectorAll('.main-nav .nav-group[open]').forEach(other => {
      if (other !== group) other.open = false;
    });
  });
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') document.querySelectorAll('.main-nav .nav-group[open]').forEach(group => {
    const focused = group.contains(document.activeElement);
    group.open = false;
    if (focused) group.querySelector('summary').focus();
  });
});
document.addEventListener('click', event => {
  if (!event.target.closest('.main-nav')) document.querySelectorAll('.main-nav .nav-group[open]').forEach(group => { group.open = false; });
});
