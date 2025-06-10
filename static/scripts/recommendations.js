document.addEventListener('DOMContentLoaded', function() {
    const playlistId = window.playlistIdFromTemplate;
    let recommendationsContent = document.getElementById('recommendations-content');
    
    let currentSongCount = getCurrentSongCount();
    const MINIMUM_SONGS_FOR_RECOMMENDATIONS = 3;
    
    if (shouldShowRecommendations()) {
        initializeRecommendations();
    } else {
        setupSongCountMonitoring();
    }
    
    function getCurrentSongCount() {
        const songCards = document.querySelectorAll('.song-card');
        return songCards.length;
    }
    
    function shouldShowRecommendations() {
        return window.recommendationsAvailable && 
               window.hasEnoughSongsForRecommendations && 
               currentSongCount >= MINIMUM_SONGS_FOR_RECOMMENDATIONS;
    }
    
    function setupSongCountMonitoring() {
        const observer = new MutationObserver((mutations) => {
            let hasChanges = false;
            
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    if (mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0) {
                        hasChanges = true;
                    }
                }
            });
            
            if (hasChanges) {
                clearTimeout(window.songCountCheckTimeout);
                window.songCountCheckTimeout = setTimeout(() => {
                    checkSongCountChange();
                }, 500);
            }
        });
        
        const songsContainer = document.querySelector('.songs-grid') || 
                              document.querySelector('.songs-simple-container') ||
                              document.querySelector('.songs-scroll-container');
        const mainContainer = document.querySelector('.container');
        
        if (songsContainer) {
            observer.observe(songsContainer, { childList: true, subtree: true });
        }
        
        if (mainContainer) {
            observer.observe(mainContainer, { childList: true, subtree: true });
        }
        
        setInterval(() => { checkSongCountChange(); }, 2000);
    }

    function checkSongCountChange() {
        const newSongCount = getCurrentSongCount();
        
        if (newSongCount !== currentSongCount) {
            const oldCount = currentSongCount;
            currentSongCount = newSongCount;
            
            if (oldCount < MINIMUM_SONGS_FOR_RECOMMENDATIONS && 
                newSongCount >= MINIMUM_SONGS_FOR_RECOMMENDATIONS && 
                !document.querySelector('.recommendations-section')) {
                
                showAutoRefreshNotification();
            }
        }
    }
    
    function initializeRecommendations() {
        if (!shouldShowRecommendations()) return;
        
        const hasRecommendationsLoading = document.getElementById('recommendations-loading');
        if (hasRecommendationsLoading) {
            setTimeout(() => { generateInitialRecommendations(); }, 2000);
        }
        
        const strategySelect = document.getElementById('recommendation-strategy');
        const refreshBtn = document.getElementById('refresh-recommendations');
        
        if (strategySelect && !strategySelect.hasAttribute('data-initialized')) {
            strategySelect.addEventListener('change', handleStrategyChange);
            strategySelect.setAttribute('data-initialized', 'true');
        }
        
        if (refreshBtn && !refreshBtn.hasAttribute('data-initialized')) {
            refreshBtn.addEventListener('click', refreshRecommendations);
            refreshBtn.setAttribute('data-initialized', 'true');
        }
        
        initializeRecommendationCards();
    }
    
    function generateInitialRecommendations() {
        if (!recommendationsContent) {
            return;
        }
        
        const strategySelectElement = document.getElementById('recommendation-strategy');
        const strategy = strategySelectElement ? strategySelectElement.value : 'balanced';
        
        startLoadingSteps();
        
        const timeoutId = setTimeout(() => {
            showNotification('Preporuke se generiram u pozadini. Molimo pokušajte ponovno za minutu.', 'info', 5000);
        }, 60000);
        
        fetch(`/playlists/${playlistId}/recommendations/refresh/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({ strategy: strategy })
        })
        .then(response => {
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                completeLoadingSteps();
                
                if (data.message) {
                    showNotification(data.message, 'info');
                }
                
                if (data.recommendations && Array.isArray(data.recommendations)) {
                    setTimeout(() => { 
                        updateRecommendationsDisplay(data.recommendations); 
                        showNotification('Preporuke su spremne!', 'success');
                    }, 1500);
                } else {
                    updateRecommendationsDisplay([]);
                }
            } else {
                throw new Error(data.error || 'Failed to generate recommendations');
            }
        })
        .catch(error => {
            clearTimeout(timeoutId);
            showNotification('Greška pri generiranju preporuka. Pokušajte osvježiti stranicu.', 'error', 5000);
            
            const loadingElement = document.getElementById('recommendations-loading');
            if (loadingElement) {
                updateRecommendationsDisplay([]);
            }
        });
    }
    
    function handleStrategyChange() {
        const strategySelectElement = document.getElementById('recommendation-strategy');
        if (!strategySelectElement) return;
        
        const strategy = strategySelectElement.value;
        const currentUrl = new URL(window.location);
        currentUrl.searchParams.set('strategy', strategy);
        window.history.pushState({}, '', currentUrl);
        
        showNotification(`Strategija promijenjena na: ${getStrategyDisplayName(strategy)}`, 'info');
        setTimeout(() => { refreshRecommendations(); }, 500);
    }
    
    function refreshRecommendations() {
        const refreshBtnElement = document.getElementById('refresh-recommendations');
        if (refreshBtnElement && refreshBtnElement.classList.contains('loading')) return;
        
        const strategySelectElement = document.getElementById('recommendation-strategy');
        const strategy = strategySelectElement ? strategySelectElement.value : 'balanced';
        
        if (refreshBtnElement) refreshBtnElement.classList.add('loading');
        showRefreshSkeletonLoading();
        
        const timeoutId = setTimeout(() => {
            showNotification('Osvježavanje preporuka je trajalo predugo. Pokušajte ponovno.', 'error');
            if (refreshBtnElement) refreshBtnElement.classList.remove('loading');
        }, 30000);
        
        fetch(`/playlists/${playlistId}/recommendations/refresh/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({ strategy: strategy })
        })
        .then(response => {
            clearTimeout(timeoutId);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (data.success) {
                completeRefreshSkeletonLoading();
                if (data.message) showNotification(data.message, 'info');
                
                setTimeout(() => {
                    updateRecommendationsDisplay(data.recommendations);
                    showNotification('Preporuke su osvježene!', 'success');
                }, 1500);
            } else {
                throw new Error(data.error || 'Failed to refresh recommendations');
            }
        })
        .catch(error => {
            clearTimeout(timeoutId);
            showNotification('Greška pri osvježavanju preporuka.', 'error');
        })
        .finally(() => {
            if (refreshBtnElement) refreshBtnElement.classList.remove('loading');
        });
    }
    
    function startLoadingSteps() {
        const steps = document.querySelectorAll('.loading-step');
        let currentStep = 0;
        
        const progressSteps = () => {
            if (currentStep < steps.length) {
                if (currentStep > 0) {
                    steps[currentStep - 1].classList.remove('active');
                    steps[currentStep - 1].classList.add('completed');
                }
                steps[currentStep].classList.add('active');
                currentStep++;
                
                const delay = currentStep === 1 ? 2000 : currentStep === 2 ? 3000 : 2000;
                setTimeout(progressSteps, delay);
            }
        };
        
        progressSteps();
    }
    
    function completeLoadingSteps() {
        const steps = document.querySelectorAll('.loading-step');
        steps.forEach((step, index) => {
            setTimeout(() => {
                step.classList.remove('active');
                step.classList.add('completed');
            }, index * 200);
        });
    }
    
    function showRefreshSkeletonLoading() {
        const currentRecommendationsContent = document.getElementById('recommendations-content');
        if (!currentRecommendationsContent) return;
        
        const skeletonHTML = `
            <div class="recommendations-refresh-loading" id="recommendations-refresh-loading">
                <div class="refresh-loading-header">
                    <div class="refresh-loading-spinner">
                        <div class="spinner-ring"></div>
                        <div class="spinner-ring"></div>
                        <div class="spinner-ring"></div>
                    </div>
                    <div class="refresh-loading-text">
                        <h3>Osvježavam preporuke...</h3>
                        <p>Tražim nove mogućnosti na osnovu vaše strategije</p>
                        <div class="refresh-loading-steps">
                            <span class="loading-step active" data-step="1">Analiziram strategiju</span>
                            <span class="loading-step" data-step="2">Generiram nove preporuke</span>
                            <span class="loading-step" data-step="3">Ocjenjujem rezultate</span>
                        </div>
                    </div>
                </div>
                
                <div class="recommendations-skeleton refresh">
                    ${createRefreshSkeletonCards(8)}
                </div>
            </div>
        `;
        
        currentRecommendationsContent.style.opacity = '0';
        currentRecommendationsContent.style.transform = 'scale(0.95)';
        
        setTimeout(() => {
            currentRecommendationsContent.innerHTML = skeletonHTML;
            currentRecommendationsContent.style.opacity = '1';
            currentRecommendationsContent.style.transform = 'scale(1)';
            currentRecommendationsContent.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            
            startRefreshLoadingSteps();
        }, 300);
    }
    
    function createRefreshSkeletonCards(count) {
        let cards = '';
        for (let i = 0; i < count; i++) {
            cards += `
                <div class="skeleton-card refresh" style="animation-delay: ${i * 0.1}s">
                    <div class="skeleton-image refresh"></div>
                    <div class="skeleton-content">
                        <div class="skeleton-line skeleton-title refresh"></div>
                        <div class="skeleton-line skeleton-artist refresh"></div>
                        <div class="skeleton-line skeleton-album refresh"></div>
                        <div class="skeleton-score">
                            <div class="skeleton-bar refresh"></div>
                            <div class="skeleton-number refresh"></div>
                        </div>
                    </div>
                </div>
            `;
        }
        return cards;
    }
    
    function startRefreshLoadingSteps() {
        const steps = document.querySelectorAll('.refresh-loading-steps .loading-step');
        let currentStep = 0;
        
        const progressSteps = () => {
            if (currentStep < steps.length) {
                if (currentStep > 0) {
                    steps[currentStep - 1].classList.remove('active');
                    steps[currentStep - 1].classList.add('completed');
                }
                
                if (steps[currentStep]) {
                    steps[currentStep].classList.add('active');
                }
                currentStep++;
                
                const delay = currentStep === 1 ? 1500 : currentStep === 2 ? 2000 : 1500;
                window.refreshStepsTimeout = setTimeout(progressSteps, delay);
            }
        };
        
        progressSteps();
    }
    
    function completeRefreshSkeletonLoading() {
        const steps = document.querySelectorAll('.refresh-loading-steps .loading-step');
        steps.forEach((step, index) => {
            setTimeout(() => {
                step.classList.remove('active');
                step.classList.add('completed');
            }, index * 100);
        });
        
        const skeletonCards = document.querySelectorAll('.skeleton-card.refresh');
        skeletonCards.forEach((card, index) => {
            setTimeout(() => {
                card.classList.add('completing');
            }, index * 50);
        });
        
        if (window.refreshStepsTimeout) {
            clearTimeout(window.refreshStepsTimeout);
        }
    }
    
    function updateRecommendationsDisplay(recommendations) {
        const currentRecommendationsContent = document.getElementById('recommendations-content');
        if (!currentRecommendationsContent) {
            return;
        }

        const wasRefreshLoading = !!document.getElementById('recommendations-refresh-loading');
        const wasInitialLoading = !!document.getElementById('recommendations-loading');

        if (!recommendations || recommendations.length === 0) {
            const emptyHTML = `
                <div class="recommendations-empty">
                    <div class="recommendations-empty-content">
                        <i class="fas fa-lightbulb"></i>
                        <h3>Nema preporuka</h3>
                        <p>Dodajte više pjesama u playlistu da biste dobili preporuke.</p>
                    </div>
                </div>
            `;
            
            if (wasRefreshLoading || wasInitialLoading) {
                currentRecommendationsContent.style.opacity = '0';
                setTimeout(() => {
                    currentRecommendationsContent.innerHTML = emptyHTML;
                    currentRecommendationsContent.style.opacity = '1';
                }, 300);
            } else {
                currentRecommendationsContent.innerHTML = emptyHTML;
            }
            return;
        }
        
        const gridHtml = `
            <div class="recommendations-grid ${wasRefreshLoading ? 'refresh-transition' : ''}">
                ${recommendations.map(rec => createRecommendationCardHtml(rec)).join('')}
            </div>
        `;
        
        if (wasRefreshLoading || wasInitialLoading) {
            currentRecommendationsContent.style.opacity = '0';
            currentRecommendationsContent.style.transform = 'scale(0.95)';
            
            setTimeout(() => {
                currentRecommendationsContent.innerHTML = gridHtml;
                initializeRecommendationCards();
                
                currentRecommendationsContent.style.transform = 'scale(1)';
                currentRecommendationsContent.style.opacity = '1';
                
                const cards = currentRecommendationsContent.querySelectorAll('.recommendation-card');
                cards.forEach((card, index) => {
                    card.style.opacity = '0';
                    card.style.transform = 'translateY(20px) scale(0.9)';
                    
                    setTimeout(() => {
                        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                        card.style.opacity = '1';
                        card.style.transform = 'translateY(0) scale(1)';
                    }, index * 100 + 200);
                });
                
                setTimeout(() => {
                    const grid = currentRecommendationsContent.querySelector('.recommendations-grid');
                    if (grid) grid.classList.remove('refresh-transition');
                }, 1000);
                
            }, 400);
            
        } else {
            currentRecommendationsContent.style.opacity = '0';
            
            setTimeout(() => {
                currentRecommendationsContent.innerHTML = gridHtml;
                initializeRecommendationCards();
                
                const cards = currentRecommendationsContent.querySelectorAll('.recommendation-card');
                cards.forEach((card, index) => {
                    card.style.opacity = '0';
                    card.style.transform = 'translateY(20px)';
                    
                    setTimeout(() => {
                        card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                        card.style.opacity = '1';
                        card.style.transform = 'translateY(0)';
                    }, index * 100);
                });
                
                currentRecommendationsContent.style.opacity = '1';
            }, 300);
        }
    }
    
    function createRecommendationCardHtml(rec) {
        if (!rec || !rec.song) {
            return '';
        }
        
        const scorePercentage = Math.round((rec.score || 0) * 100);
        
        return `
            <div class="recommendation-card" data-song-id="${rec.song.id || ''}">
                <div class="recommendation-card-image-container">
                    <img src="${rec.song.photo || '/static/images/default-album.png'}" 
                         alt="${escapeHtml(rec.song.name || 'Unknown')} cover" 
                         class="recommendation-card-image">
                    <div class="recommendation-card-overlay">
                        <button class="add-recommendation-btn" title="Dodaj u plejlistu">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                </div>
                
                <div class="recommendation-card-content">
                    <h4 class="recommendation-card-title">${escapeHtml(rec.song.name || 'Unknown')}</h4>
                    <p class="recommendation-card-artist">${escapeHtml(rec.song.artist || 'Unknown Artist')}</p>
                    <p class="recommendation-card-album">${escapeHtml(rec.song.album || 'Unknown Album')}</p>
                    
                    <div class="recommendation-score">
                        <div class="score-bar">
                            <div class="score-fill" style="width: ${scorePercentage}%"></div>
                        </div>
                        <span class="score-text">${(rec.score || 0).toFixed(1)}</span>
                    </div>
                    
                    <div class="recommendation-explanation">
                        ${rec.explanation && rec.explanation.content_audio !== undefined ? `
                        <div class="explanation-item">
                            <span class="explanation-label">Slični sadržaj:</span>
                            <span class="explanation-value">${rec.explanation.content_audio.toFixed(1)}</span>
                        </div>
                        ` : ''}
                        ${rec.explanation && rec.explanation.popularity !== undefined ? `
                        <div class="explanation-item">
                            <span class="explanation-label">Popularnost:</span>
                            <span class="explanation-value">${rec.explanation.popularity.toFixed(1)}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    function initializeRecommendationCards() {
        const addButtons = document.querySelectorAll('.add-recommendation-btn');
        addButtons.forEach(button => {
            button.addEventListener('click', handleAddRecommendation);
        });
    }
    
    function handleAddRecommendation(event) {
        const button = event.currentTarget;
        const card = button.closest('.recommendation-card');
        const songId = card.dataset.songId;
        
        if (button.classList.contains('loading') || button.classList.contains('added')) return;
        
        const songName = card.querySelector('.recommendation-card-title').textContent;
        const songArtist = card.querySelector('.recommendation-card-artist').textContent;
        const songAlbum = card.querySelector('.recommendation-card-album').textContent;
        const songImage = card.querySelector('.recommendation-card-image').src;
        
        button.classList.add('loading');
        button.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i>';
        
        fetch(`/playlists/${playlistId}/recommendations/add/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({ song_id: songId })
        })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (data.success) {
                button.classList.remove('loading');
                button.classList.add('added');
                button.innerHTML = '<i class="fas fa-check"></i>';
                
                addRecommendedSongToContainer(songId, songName, songArtist, songAlbum, songImage);
                
                showNotification('Pjesma je dodana!', 'success');
                
                setTimeout(() => {
                    card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.8)';
                    
                    setTimeout(() => {
                        card.remove();
                        const grid = document.querySelector('.recommendations-grid');
                        if (grid && grid.children.length === 0) {
                            updateRecommendationsDisplay([]);
                        }
                    }, 500);
                }, 1000);
                
            } else {
                throw new Error(data.error || 'Failed to add song');
            }
        })
        .catch(error => {
            button.classList.remove('loading');
            button.innerHTML = '<i class="fas fa-plus"></i>';
            
            let errorMessage = 'Greška pri dodavanju pjesme.';
            if (error.message.includes('already in playlist')) {
                errorMessage = 'Pjesma je već u playlisti.';
            }
            
            showNotification(errorMessage, 'error');
        });
    }
    
    function getCsrfToken() {
        const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
        if (tokenElement) return tokenElement.value;
        
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
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
    
    function escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    }
    
    function showNotification(message, type = 'info', duration = 3000) {
        const existingNotifications = document.querySelectorAll(`.notification-${type}`);
        existingNotifications.forEach(notification => {
            if (notification.parentNode) notification.parentNode.removeChild(notification);
        });
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        if (message.includes('Strategija') || message.includes('preporuke')) {
            notification.classList.add('notification-enhanced');
        }
        
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
                <span>${message}</span>
            </div>
            <div class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => { notification.classList.add('show'); }, 100);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) notification.parentNode.removeChild(notification);
            }, 300);
        }, duration);
    }
    
    function getStrategyDisplayName(strategy) {
        const strategyNames = {
            'balanced': 'Balansirano',
            'discovery': 'Otkrijte novo',
            'popular': 'Popularno'
        };
        return strategyNames[strategy] || strategy;
    }
    
    function addRecommendedSongToContainer(songId, songName, songArtist, songAlbum, songImage) {
        const newSongCard = document.createElement('div');
        newSongCard.className = 'song-card';
        newSongCard.style.opacity = '0';
        newSongCard.style.transform = 'scale(0.8)';
        newSongCard.innerHTML = `
            <div class="song-card-actions">
                <form action="/playlists/${playlistId}/remove/${songId}/" method="post">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${getCsrfToken()}">
                    <button type="submit" class="song-card-remove-btn" title="Remove from playlist">
                        <i class="fas fa-times"></i>
                    </button>
                </form>
            </div>
            
            <div class="song-card-image-container">
                <img src="${songImage}" alt="${escapeHtml(songName)} cover" class="song-card-image">
                <div class="song-card-play-overlay">
                    <div class="song-card-play-button">
                        <svg viewBox="0 0 24 24">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                    </div>
                </div>
            </div>
            
            <div class="song-card-content">
                <h3 class="song-card-title">${escapeHtml(songName)}</h3>
                <p class="song-card-artist">${escapeHtml(songArtist)}</p>
                <p class="song-card-album">${escapeHtml(songAlbum)}</p>
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
            
            const playlistSongCount = document.querySelector('.playlist-info span:nth-child(2)');
            if (playlistSongCount) {
                const currentHeaderCount = currentSongCount + 1;
                playlistSongCount.innerHTML = `<i class="fas fa-music"></i> ${currentHeaderCount} pjesama`;
            }
        }
        
        setTimeout(() => {
            newSongCard.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            newSongCard.style.opacity = '1';
            newSongCard.style.transform = 'scale(1)';
        }, 100);
        
        setTimeout(() => {
            newSongCard.style.boxShadow = '0 0 20px rgba(30, 215, 96, 0.5)';
            setTimeout(() => {
                newSongCard.style.boxShadow = '';
            }, 2000);
        }, 600);
    }
    
    function upgradeToScrollableContainer() {
        const simpleContainer = document.querySelector('.songs-simple-container');
        if (!simpleContainer) return;
        
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
});

function showAutoRefreshNotification() {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0, 0, 0, 0.9); display: flex;
        align-items: center; justify-content: center; z-index: 9999;
    `;
    
    notification.innerHTML = `
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 2rem; border-radius: 15px; text-align: center;
                    color: white; max-width: 400px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);">
            <div style="font-size: 3rem; color: #ffd700; margin-bottom: 1rem; animation: pulse 1.5s ease-in-out infinite;">🎵</div>
            <h3 style="margin: 0 0 0.5rem 0; font-size: 1.5rem;">Otključali ste prijedloge!</h3>
            <p style="margin: 0 0 1rem 0; opacity: 0.9;">Ozvježavam stranicu...</p>
            <div style="font-size: 2rem; font-weight: bold; color: #ffd700;" id="countdown">3</div>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    let countdown = 3;
    const countdownElement = document.getElementById('countdown');
    
    const interval = setInterval(() => {
        countdown--;
        countdownElement.textContent = countdown;
        
        if (countdown <= 0) {
            clearInterval(interval);
            window.location.reload();
        }
    }, 1000);
    
    notification.addEventListener('click', () => {
        clearInterval(interval);
        window.location.reload();
    });
}