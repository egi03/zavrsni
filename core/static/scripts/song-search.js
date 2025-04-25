document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('song-search');
    const searchResults = document.getElementById('search-results');
    const searchSpinner = document.getElementById('search-spinner');
    
    if (!searchInput) return;
    
    // Debounce function to prevent lot of API calls
    // wait until user stops typeing for 0.5s before calling the API
    function debounce(func, delay) {
      let debounceTimer;
      return function() {
        const context = this;
        const args = arguments;
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => func.apply(context, args), delay);
      };
    }
    
    // Look for CSRF token in cookies or in the form
    function getCSRFToken() {
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
          return value;
        }
      }
      
      const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
      if (csrfInput) {
        return csrfInput.value;
      }
      
      return '';
    }
    
    function setupSearchInputEffects() {
      searchInput.addEventListener('focus', function() {
        this.parentElement.classList.add('focused');
      });
      
      searchInput.addEventListener('blur', function() {
        this.parentElement.classList.remove('focused');
      });
    }
    
    const searchSongs = debounce(function(query) {
      if (query.length < 2) {
        searchResults.innerHTML = '';
        searchResults.classList.remove('active');
        return;
      }
      
      searchSpinner.style.display = 'block';
      
      fetch(`/search_songs/?query=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
          searchSpinner.style.display = 'none';
          
          if (data.length > 0) {
            searchResults.innerHTML = '';
            data.forEach(song => {
              const songResult = document.createElement('div');
              songResult.className = 'song-result';
              songResult.innerHTML = `
                <img src="${song.album_image || '/static/photos/playlist-default.jpg'}" alt="${song.title} Cover">
                <div class="song-result-info">
                  <p class="song-result-title">${song.title}</p>
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
                addSongToPlaylist(songId);
                
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


    // First try to get ID from URL, if not found, try data attribure, if not found, use the template variable
    function getPlaylistId() {
      const pathParts = window.location.pathname.split('/');
      const playlistIndex = pathParts.indexOf('playlist');
      if (playlistIndex !== -1 && playlistIndex + 1 < pathParts.length) {
        return pathParts[playlistIndex + 1];
      }
      
      const playlistContainer = document.querySelector('[data-playlist-id]');
      if (playlistContainer) {
        return playlistContainer.getAttribute('data-playlist-id');
      }
      
      return playlistIdFromTemplate;
    }

    
    function addSongToPlaylist(songId) {
      const playlistId = getPlaylistId();
      
      if (!playlistId) {
        console.error('Dont have playlist id');
        return;
      }
      
      fetch(`/add_to_playlist/${playlistId}/`, {
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
          showMessage('Pjesma uspješno dodana!!', 'success');
          
          setTimeout(() => {
            window.location.reload();
          }, 1000);
        } else {
          showMessage(`Error: ${data.error}`, 'error');
        }
      })
      .catch(error => {
        console.error('Dogodila se greška. Molimo pokušajte kasnije.:', error);
        showMessage('Dogodila se greška. Molimo pokušajte kasnije.', 'error');
      });
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