document.addEventListener('DOMContentLoaded', () => {
    const themeSwitcher = document.getElementById('theme-switcher');
    const themeIcon = themeSwitcher ? themeSwitcher.querySelector('i') : null;
    const htmlElement = document.documentElement;

    if (!themeSwitcher || !themeIcon) {
        console.error("Theme switcher button or icon not found.");
        return;
    }

    // Applique le thème sauvegardé au chargement de la page
    const currentTheme = localStorage.getItem('theme') || 'light';
    htmlElement.setAttribute('data-theme', currentTheme);
    updateIcon(currentTheme);

    // Gère le clic sur le bouton
    themeSwitcher.addEventListener('click', () => {
        const newTheme = htmlElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        htmlElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateIcon(newTheme);
    });

    // Met à jour l'icône en fonction du thème
    function updateIcon(theme) {
        if (theme === 'dark') {
            themeIcon.classList.remove('bi-moon-stars-fill');
            themeIcon.classList.add('bi-brightness-high-fill');
        } else {
            themeIcon.classList.remove('bi-brightness-high-fill');
            themeIcon.classList.add('bi-moon-stars-fill');
        }
    }
});