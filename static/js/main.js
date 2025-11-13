// Main JavaScript for Pickleball Connect

// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Confirm delete actions
function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this?');
}

// Filter players by search
function filterPlayers() {
    const input = document.getElementById('playerSearch');
    const filter = input.value.toLowerCase();
    const cards = document.querySelectorAll('.player-card');
    
    cards.forEach(function(card) {
        const text = card.textContent.toLowerCase();
        if (text.includes(filter)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

// Select all checkboxes
function selectAll(source) {
    const checkboxes = document.querySelectorAll('input[type="checkbox"][name="player_ids"]');
    checkboxes.forEach(function(checkbox) {
        checkbox.checked = source.checked;
    });
    updateSelectedCount();
}

// Update selected player count
function updateSelectedCount() {
    const checkboxes = document.querySelectorAll('input[type="checkbox"][name="player_ids"]:checked');
    const countElement = document.getElementById('selectedCount');
    if (countElement) {
        countElement.textContent = checkboxes.length;
    }
}