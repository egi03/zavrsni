document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('song-search');
    const searchResults = document.getElementById('song-search-results');
    const searchSpinner = document.getElementById('search-spinner');
    
    if (!searchInput) return;
    
    function debounce(func, delay) {
        let debounceTimer;
        return function() {
            const context = this;
            const args = arguments;
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => func.apply(context, args), delay);
        };
    }
    
    function getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') return value;
        }
        
        const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (csrfInput) return csrfInput.value;
        
        return '';
    }   
    
    function getPlaylistId() {
        const pathParts = window.location.pathname.split('/');
        const playlistsIndex = pathParts.indexOf('playlists');
        if (playlistsIndex !== -1 && playlistsIndex + 1 < pathParts.length) {
            return pathParts[playlistsIndex + 1];
        }
        
        const playlistContainer = document.querySelector('[data-playlist-id]');
        if (playlistContainer) {
            return playlistContainer.getAttribute('data-playlist-id');
        }
        
        return playlistIdFromTemplate;
    }
    
    const searchSongs = debounce(function(query) {
        if (query.length < 2) {
            searchResults.innerHTML = '';
            searchResults.classList.remove('active');
            return;
        }
        
        searchSpinner.style.display = 'block';
        
        fetch(`/playlists/search/?query=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                searchSpinner.style.display = 'none';
                
                if (data.length > 0) {
                    searchResults.innerHTML = '';
                    data.forEach(song => {
                        const songResult = document.createElement('div');
                        songResult.className = 'song-result';
                        songResult.innerHTML = `
                            <img src="${song.album_image || '/static/photos/playlist-default.jpg'}" alt="${song.name} Cover">
                            <div class="song-result-info">
                                <p class="song-result-name">${song.name}</p>
                                <p class="song-result-artist">${song.artist}</p>
                                <p class="song-result-album">${song.album}</p>
                            </div>
                            <div class="song-result-actions">
                                <button class="add-song-btn" data-song-id="${song.id}">Add</button>
                            </div>
                        `;
                        searchResults.appendChild(songResult);
                    });
                    
                    document.querySelectorAll('.add-song-btn').forEach(button => {
                        button.addEventListener('click', function() {
                            const songId = this.getAttribute('data-song-id');
                            addSongToPlaylist(songId, this);
                            
                            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                            this.disabled = true;
                        });
                    });
                    
                    searchResults.classList.add('active');
                } else {
                    searchResults.innerHTML = '<div class="no-results">Trenutno nemamo pjesmu koju tražite</div>';
                    searchResults.classList.add('active');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                searchSpinner.style.display = 'none';
                searchResults.innerHTML = '<div class="no-results">Dogodila se greška. Molimo pokušajte kasnije.</div>';
                searchResults.classList.add('active');
            });
    }, 500);
    
    function addSongToPlaylist(songId, buttonElement) {
        const playlistId = getPlaylistId();
        
        if (!playlistId) {
            console.error('No playlist ID found');
            return;
        }
        
        fetch(`/playlists/${playlistId}/add/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ song_id: songId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage('Pjesma uspješno dodana!', 'success');
                addSongToDOM(songId, buttonElement);
                
                setTimeout(() => {
                    if (buttonElement) {
                        const songResult = buttonElement.closest('.song-result');
                        if (songResult) {
                            songResult.style.opacity = '0';
                            setTimeout(() => songResult.remove(), 300);
                        }
                    }
                    
                    const remainingResults = searchResults.querySelectorAll('.song-result');
                    if (remainingResults.length <= 1) {
                        searchResults.classList.remove('active');
                        searchInput.value = '';
                    }
                }, 1000);
                
            } else {
                showMessage(`Error: ${data.error}`, 'error');
                
                if (buttonElement) {
                    buttonElement.innerHTML = 'Add';
                    buttonElement.disabled = false;
                }
            }
        })
        .catch(error => {
            console.error('Error adding song:', error);
            showMessage('Dogodila se greška. Molimo pokušajte kasnije.', 'error');
            
            if (buttonElement) {
                buttonElement.innerHTML = 'Add';
                buttonElement.disabled = false;
            }
        });
    }
    
    function addSongToDOM(songId, buttonElement) {
        const songResult = buttonElement.closest('.song-result');
        if (!songResult) return;
        
        const songName = songResult.querySelector('.song-result-name').textContent;
        const songArtist = songResult.querySelector('.song-result-artist').textContent;
        const songAlbum = songResult.querySelector('.song-result-album').textContent;
        const songImage = songResult.querySelector('img').src;
        
        const newSongCard = document.createElement('div');
        newSongCard.className = 'song-card';
        newSongCard.style.opacity = '0';
        newSongCard.style.transform = 'scale(0.8)';
        newSongCard.innerHTML = `
            <div class="song-card-actions">
                <form action="/playlists/${getPlaylistId()}/remove/${songId}/" method="post">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${getCSRFToken()}">
                    <button type="submit" class="song-card-remove-btn" title="Remove from playlist">
                        <i class="fas fa-times"></i>
                    </button>
                </form>
            </div>
            
            <div class="song-card-image-container">
                <img src="${songImage}" alt="${songName} cover" class="song-card-image">
                <div class="song-card-play-overlay">
                    <div class="song-card-play-button">
                        <svg viewBox="0 0 24 24">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                    </div>
                </div>
            </div>
            
            <div class="song-card-content">
                <h3 class="song-card-title">${songName}</h3>
                <p class="song-card-artist">${songArtist}</p>
                <p class="song-card-album">${songAlbum}</p>
            </div>
            
            <div class="song-card-playing">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        
        const songsGrid = document.querySelector('.songs-grid');
        const songsEmpty = document.querySelector('.songs-empty');
        const currentSongCount = document.querySelectorAll('.song-card').length;
        
        const SCROLL_CONTAINER_THRESHOLD = 6;
        
        if (songsEmpty) {
            const simpleContainer = document.createElement('div');
            simpleContainer.className = 'songs-simple-container';
            simpleContainer.innerHTML = `
                <div class="songs-simple-header">
                    <h2 class="songs-simple-title">
                        <i class="fas fa-music"></i>
                        Pjesme
                    </h2>
                    <span class="songs-count">Broj pjesama: 1</span>
                </div>
                <div class="songs-grid simple"></div>
            `;
            
            songsEmpty.parentNode.replaceChild(simpleContainer, songsEmpty);
            
            const newSongsGrid = document.querySelector('.songs-grid');
            newSongsGrid.appendChild(newSongCard);
            
        } else if (songsGrid) {
            songsGrid.appendChild(newSongCard);
            
            const songsCount = document.querySelector('.songs-count');
            if (songsCount) {
                const newCount = currentSongCount + 1;
                songsCount.textContent = `Broj pjesama: ${newCount}`;
                
                if (newCount >= SCROLL_CONTAINER_THRESHOLD && songsGrid.classList.contains('simple')) {
                    upgradeToScrollableContainer();
                }
            }
        }
        
        setTimeout(() => {
            newSongCard.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            newSongCard.style.opacity = '1';
            newSongCard.style.transform = 'scale(1)';
        }, 100);
    }
    
    function upgradeToScrollableContainer() {
        const simpleContainer = document.querySelector('.songs-simple-container');
        if (!simpleContainer) return;
        
        console.log('🔄 Upgrading to scrollable container');
        
        const currentSongs = Array.from(document.querySelectorAll('.song-card'));
        const songCount = currentSongs.length;
        
        const scrollableContainer = document.createElement('div');
        scrollableContainer.className = 'songs-scroll-wrapper';
        scrollableContainer.innerHTML = `
            <div class="songs-scroll-container">
                <div class="songs-scroll-header">
                    <h2 class="songs-scroll-title">
                        <i class="fas fa-music"></i>
                        Pjesme
                    </h2>
                    <span class="songs-count">Broj pjesama: ${songCount}</span>
                </div>
                
                <div class="songs-scrollable">
                    <div class="songs-grid"></div>
                </div>
                
                <div class="scroll-indicator bottom">
                    <i class="fas fa-chevron-down"></i>
                </div>
            </div>
        `;
        
        const newGrid = scrollableContainer.querySelector('.songs-grid');
        currentSongs.forEach(song => {
            newGrid.appendChild(song);
        });
        
        simpleContainer.parentNode.replaceChild(scrollableContainer, simpleContainer);
        
        scrollableContainer.style.opacity = '0';
        scrollableContainer.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            scrollableContainer.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            scrollableContainer.style.opacity = '1';
            scrollableContainer.style.transform = 'translateY(0)';
        }, 100);
    }
    
    function showMessage(text, type = 'success') {
        let messagesContainer = document.querySelector('.messages');
        
        if (!messagesContainer) {
            messagesContainer = document.createElement('div');
            messagesContainer.className = 'messages';
            messagesContainer.style.position = 'fixed';
            messagesContainer.style.top = '20px';
            messagesContainer.style.right = '20px';
            messagesContainer.style.zIndex = '1000';
            messagesContainer.style.maxWidth = '350px';
            document.body.appendChild(messagesContainer);
        }
        
        const messageEl = document.createElement('div');
        messageEl.className = `message ${type}`;
        messageEl.textContent = text;
        messageEl.style.cssText = `
            padding: 12px 16px;
            margin-bottom: 10px;
            border-radius: 4px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            animation: fadeIn 0.3s, fadeOut 0.5s 4.5s forwards;
            background-color: ${type === 'success' ? '#4CAF50' : '#f44336'};
            color: white;
        `;
        
        messagesContainer.appendChild(messageEl);
        
        setTimeout(() => {
            messageEl.remove();
        }, 5000);
    }
    
    function setupSearchInputEffects() {
        searchInput.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        searchInput.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    }
    
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        searchSongs(query);
    });
    
    document.addEventListener('click', function(event) {
        if (!searchResults.contains(event.target) && event.target !== searchInput) {
            searchResults.classList.remove('active');
        }
    });
    
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && document.activeElement !== searchInput) {
            event.preventDefault();
            searchInput.focus();
        }
        
        if (event.key === 'Escape') {
            searchResults.classList.remove('active');
            searchInput.blur();
        }
    });
    
    setupSearchInputEffects();
    
    const originalPlaceholder = searchInput.placeholder;
    searchInput.placeholder = `${originalPlaceholder} (Klikni Enter za fokus)`;
});