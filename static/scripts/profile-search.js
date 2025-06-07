document.addEventListener('DOMContentLoaded', function() {

    const searchToggle = document.getElementById('searchToggle');
    const searchOverlay = document.getElementById('searchOverlay');
    const searchClose = document.getElementById('searchClose');
    const searchInput = document.getElementById('profileSearchInput');
    const searchResults = document.getElementById('searchResults');
    const searchSpinner = document.getElementById('searchSpinner');


    let searchTimeout;

    searchToggle.addEventListener('click', function() {
        searchOverlay.classList.add('active');
        searchInput.focus();
        document.body.style.overflow = 'hidden';
    });

    // Closing the search overlay
    searchClose.addEventListener('click', closeSearch);

    searchOverlay.addEventListener('click', function(event) {
        if (event.target === searchOverlay) {
            closeSearch();
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && searchOverlay.classList.contains('active')) {
            closeSearch();
        }
    });

    function closeSearch() {
        searchOverlay.classList.remove('active');
        document.body.style.overflow = '';
        searchInput.value = '';
        searchResults.innerHTML = '';
    }

    // Search functionality
    searchInput.addEventListener('input', function() {
        const query = searchInput.value.trim();
        
        clearTimeout(searchTimeout);
       
        if (query.length < 2) {
            searchResults.innerHTML = `
                <div class="search-empty">
                    <i class="fas fa-search"></i>
                    <p>Unesite najmanje 2 karaktera za pretragu</p>
                </div>
            `;
            return;
        }

        searchSpinner.classList.add('active');

        searchTimeout = setTimeout(() => {
            searchProfile(query);
        }, 300);
    });

    function searchProfile(query){
        const csrfToken = getCookie('csrftoken');

        fetch(`/accounts/search-profiles/?q=${encodeURIComponent(query)}`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            searchSpinner.classList.remove('active');
            displayResults(data.users);
        })
        .catch(error => {
            console.error('Search error:', error);
            searchSpinner.classList.remove('active');
            searchResults.innerHTML = `
                <div class="search-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Greška pri pretraživanju. Pokušajte ponovo.</p>
                </div>
            `;
        });
    }

    function displayResults(users){
        if(users.length === 0){
            searchResults.innerHTML = `
                <div class="search-no-results">
                    <p>Nema rezultata za "${searchInput.value}"</p>
                </div>
            `;
            return;
        }

        const resultsHTML = users.map(user => {
            const profilePicture = user.profile_picture 
            ? `<img src="${user.profile_picture}" alt="${user.username}">`
            : `<div class="search-result-placeholder">${user.username.charAt(0).toUpperCase()}</div>`;

            return `
                <a href="/accounts/profile/${user.username}/" class="search-result-item">
                <div class="search-result-avatar">
                    ${profilePicture}
                    </div>
                    <span class="search-result-username">@${escapeHtml(user.username)}</span>
                </a>
            `;
        }).join('');
        searchResults.innerHTML = resultsHTML;
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== ''){
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
        }
    }
    return cookieValue;
    }

    function escapeHtml(text){
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

});