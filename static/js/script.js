document.addEventListener('DOMContentLoaded', function() {
    // Fade out flash messages after 3 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    if (flashMessages.length > 0) {
        setTimeout(function() {
            flashMessages.forEach(function(message) {
                message.style.transition = 'opacity 1s';
                message.style.opacity = '0';
            });
        }, 3000);
    }
});
