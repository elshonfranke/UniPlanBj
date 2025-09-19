/*
 * Gestionnaire des abonnements aux notifications push côté client.
 */

/**
 * Convertit une chaîne base64 URL-safe en Uint8Array.
 * Nécessaire pour la clé publique VAPID.
 */
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

/**
 * Fonction principale pour initialiser les notifications push.
 */
async function initPushNotifications() {
    // 1. Vérifier la compatibilité du navigateur
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.warn('Les notifications push ne sont pas supportées par ce navigateur.');
        return;
    }

    try {
        // 2. Enregistrer le Service Worker
        const swRegistration = await navigator.serviceWorker.register('/static/js/sw.js');
        console.log('Service Worker enregistré avec succès:', swRegistration);

        // 3. Demander la permission à l'utilisateur
        const permission = await window.Notification.requestPermission();
        if (permission !== 'granted') {
            console.log('Permission pour les notifications refusée.');
            return;
        }

        // 4. Obtenir la clé publique VAPID du serveur
        const response = await fetch('/api/vapid-public-key');
        const vapidPublicKey = await response.text();
        const convertedVapidKey = urlBase64ToUint8Array(vapidPublicKey);

        // 5. S'abonner au service push
        const subscription = await swRegistration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: convertedVapidKey
        });

        // 6. Envoyer l'abonnement au serveur pour le sauvegarder
        await fetch('/api/subscribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(subscription),
        });

        console.log('Abonnement aux notifications push réussi.');

    } catch (error) {
        console.error('Erreur lors de l\'initialisation des notifications push:', error);
    }
}

// Lancer l'initialisation une fois que la page est chargée
window.addEventListener('load', initPushNotifications);