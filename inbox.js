document.addEventListener('DOMContentLoaded', function() {
    const formatToolbar = document.querySelector('.format-toolbar');
    const messageInput = document.getElementById('message-input');

    // Si les éléments de la messagerie ne sont pas sur la page, ne rien faire.
    if (!formatToolbar || !messageInput) {
        return;
    }

    formatToolbar.addEventListener('click', function(e) {
        const button = e.target.closest('.format-btn');
        if (!button) return;

        e.preventDefault(); // Empêche le comportement par défaut du bouton

        const formatType = button.dataset.format;
        const markdown = {
            bold: '**',
            italic: '*',
            strikethrough: '~~'
        };

        const chars = markdown[formatType];
        if (chars) {
            applyMarkdown(messageInput, chars);
        }
    });

    /**
     * Applique le formatage Markdown au texte sélectionné dans un champ de saisie.
     * @param {HTMLInputElement} input - Le champ de saisie.
     * @param {string} chars - Les caractères Markdown à utiliser (ex: '**').
     */
    function applyMarkdown(input, chars) {
        const start = input.selectionStart;
        const end = input.selectionEnd;
        const selectedText = input.value.substring(start, end);

        const textBefore = input.value.substring(0, start);
        const textAfter = input.value.substring(end);

        input.value = `${textBefore}${chars}${selectedText}${chars}${textAfter}`;
        input.focus();
        input.setSelectionRange(start + chars.length, start + chars.length + selectedText.length);
    }
});