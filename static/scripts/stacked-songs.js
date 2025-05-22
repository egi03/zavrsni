// stacked-songs.js

document.addEventListener('DOMContentLoaded', function() {
    // Create audio player
    const audioPlayer = new Audio();
    let currentlyPlaying = null;
    let currentPlayButton = null;
    
    // Select all song cards and play buttons
    const songCards = document.querySelectorAll('.stacked-song-card');
    const playButtons = document.querySelectorAll('.play-button');
    const songsContainer = document.querySelector('.stacked-songs-container');
    
    // Add hover class for 3D effect when cards are hovered
    songCards.forEach(card => {
      // Handle card hover effects
      card.addEventListener('mouseenter', function() {
        // Add a class to nearby cards to create depth effect
        const index = Array.from(songCards).indexOf(this);
        
        if (index > 0) {
          songCards[index - 1].classList.add('card-before');
        }
        
        if (index < songCards.length - 1) {
          songCards[index + 1].classList.add('card-after');
        }
      });
      
      card.addEventListener('mouseleave', function() {
        // Remove classes when mouse leaves
        songCards.forEach(c => {
          c.classList.remove('card-before', 'card-after');
        });
      });
    });
    
    // Handle play button clicks
    playButtons.forEach(button => {
      button.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const previewUrl = this.getAttribute('data-preview-url');
        
        // If no preview URL is available
        if (!previewUrl) {
          showToast('No preview available for this song');
          return;
        }
        
        // If this is already playing
        if (currentPlayButton === this) {
          if (audioPlayer.paused) {
            audioPlayer.play();
            this.classList.add('playing');
            this.innerHTML = '<i class="fas fa-pause"></i>';
          } else {
            audioPlayer.pause();
            this.classList.remove('playing');
            this.innerHTML = '<i class="fas fa-play"></i>';
          }
        } else {
          // If another song is playing, reset it
          if (currentPlayButton) {
            currentPlayButton.classList.remove('playing');
            currentPlayButton.innerHTML = '<i class="fas fa-play"></i>';
          }
          
          // Play the new song
          audioPlayer.src = previewUrl;
          audioPlayer.play();
          this.classList.add('playing');
          this.innerHTML = '<i class="fas fa-pause"></i>';
          currentPlayButton = this;
          
          // Scroll to center the playing card
          const parentCard = this.closest('.stacked-song-card');
          scrollToCard(parentCard);
        }
      });
    });
    
    // Handle audio playback end
    audioPlayer.addEventListener('ended', function() {
      if (currentPlayButton) {
        currentPlayButton.classList.remove('playing');
        currentPlayButton.innerHTML = '<i class="fas fa-play"></i>';
        currentPlayButton = null;
      }
    });
    
    // Add smooth scrolling to the songs container
    if (songsContainer) {
      // Smooth scroll for mouse wheel
      songsContainer.addEventListener('wheel', function(e) {
        e.preventDefault();
        
        const delta = e.deltaY;
        const scrollSpeed = 0.8; // Adjust speed
        
        // Smooth scroll with requestAnimationFrame
        smoothScroll(songsContainer, delta * scrollSpeed);
      }, { passive: false });
      
      // Touch scrolling for mobile
      let touchStartY = 0;
      let touchEndY = 0;
      
      songsContainer.addEventListener('touchstart', function(e) {
        touchStartY = e.changedTouches[0].screenY;
      }, { passive: true });
      
      songsContainer.addEventListener('touchmove', function(e) {
        touchEndY = e.changedTouches[0].screenY;
        const delta = touchStartY - touchEndY;
        touchStartY = touchEndY;
        
        // Direct scroll for touch - smoother on mobile
        songsContainer.scrollTop += delta;
      }, { passive: true });
      
      // Add scroll animation when songs are added
      animateCardsOnLoad();
    }
    
    // Function to scroll to a specific card
    function scrollToCard(card) {
      if (!card || !songsContainer) return;
      
      const containerRect = songsContainer.getBoundingClientRect();
      const cardRect = card.getBoundingClientRect();
      const offset = cardRect.top - containerRect.top;
      const center = offset - (containerRect.height / 2) + (cardRect.height / 2);
      
      smoothScroll(songsContainer, center);
    }
    
    // Function for smooth scrolling
    function smoothScroll(element, delta) {
      const start = element.scrollTop;
      const target = start + delta;
      const duration = 300; // ms
      const startTime = performance.now();
      
      function step(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeInOutQuad = progress < 0.5 ? 2 * progress * progress : 1 - Math.pow(-2 * progress + 2, 2) / 2;
        
        element.scrollTop = start + (target - start) * easeInOutQuad;
        
        if (progress < 1) {
          requestAnimationFrame(step);
        }
      }
      
      requestAnimationFrame(step);
    }
    
    // Function to animate cards on load
    function animateCardsOnLoad() {
      songCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        
        setTimeout(() => {
          card.style.opacity = '1';
          card.style.transform = 'translateY(0)';
        }, 100 + (index * 50)); // Staggered animation
      });
    }
    
    // Function to show toast message
    function showToast(message) {
      // Create toast element if it doesn't exist
      let toast = document.querySelector('.custom-toast');
      if (!toast) {
        toast = document.createElement('div');
        toast.className = 'custom-toast';
        document.body.appendChild(toast);
        
        // Add styles inline to ensure they're applied
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.left = '50%';
        toast.style.transform = 'translateX(-50%)';
        toast.style.backgroundColor = 'rgba(30, 215, 96, 0.9)';
        toast.style.color = '#000';
        toast.style.padding = '10px 20px';
        toast.style.borderRadius = '5px';
        toast.style.zIndex = '1000';
        toast.style.boxShadow = '0 4px 10px rgba(0, 0, 0, 0.3)';
        toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translate(-50%, 20px)';
      }
      
      // Set message and show toast
      toast.textContent = message;
      toast.style.opacity = '1';
      toast.style.transform = 'translate(-50%, 0)';
      
      // Hide toast after delay
      clearTimeout(toast.timeoutId);
      toast.timeoutId = setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translate(-50%, 20px)';
      }, 3000);
    }
  });