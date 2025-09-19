/*
 * Service Worker pour les notifications push
 * Ce fichier s'exécute en arrière-plan dans le navigateur.
 */

// Écouteur pour l'événement 'push'
self.addEventListener('push', function(event) {
    // Récupère les données de la notification envoyée par le serveur
    const data = event.data.json();

    const title = data.title || 'UniPlanBJ';
    const options = {
        body: data.body,
        icon: data.icon || '/static/images/logo.png', // Assurez-vous d'avoir un logo ici
        badge: data.badge || '/static/images/badge.png', // Et un badge ici
        data: {
            url: data.url // URL à ouvrir lors du clic sur la notification
        }
    };

    // Affiche la notification
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// Écouteur pour l'événement 'notificationclick'
self.addEventListener('notificationclick', function(event) {
    // Ferme la notification
    event.notification.close();

    // Ouvre l'URL associée à la notification dans un nouvel onglet
    const urlToOpen = event.notification.data.url;
    if (urlToOpen) {
        event.waitUntil(
            clients.openWindow(urlToOpen)
        );
    }
});