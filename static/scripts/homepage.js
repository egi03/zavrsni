document.addEventListener('DOMContentLoaded', function() {
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, observerOptions);

  document.querySelectorAll('.animate-on-scroll').forEach(el => {
    observer.observe(el);
  });

  const scrollIndicator = document.querySelector('.scroll-indicator-enhanced');
  if (scrollIndicator) {
    scrollIndicator.addEventListener('click', function() {
      const nextSection = document.querySelector('.section-enhanced');
      if (nextSection) {
        nextSection.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  }

  document.querySelectorAll('.hero-cta-enhanced, .cta-button-enhanced').forEach(button => {
    button.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-3px) scale(1.05)';
    });
    
    button.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0) scale(1)';
    });
  });
});


document.addEventListener('DOMContentLoaded', function() {
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        
        if (entry.target.classList.contains('text-reveal')) {
          const spans = entry.target.querySelectorAll('span');
          spans.forEach((span, index) => {
            setTimeout(() => {
              span.style.transitionDelay = `${index * 0.1}s`;
              span.style.opacity = '1';
              span.style.transform = 'translateY(0)';
            }, index * 100);
          });
        }
        
        if (entry.target.classList.contains('counter')) {
          animateCounter(entry.target);
        }
        
        if (entry.target.classList.contains('progressive-reveal')) {
          const items = entry.target.querySelectorAll('.reveal-item');
          items.forEach((item, index) => {
            setTimeout(() => {
              item.classList.add('visible');
            }, index * 150);
          });
        }
      }
    });
  }, observerOptions);

  const animatedElements = document.querySelectorAll(`
    .animate-on-scroll, 
    .slide-in-left, 
    .slide-in-right, 
    .scale-in, 
    .rotate-in, 
    .fade-in, 
    .blur-in, 
    .text-reveal, 
    .progressive-reveal,
    .counter
  `);
  
  animatedElements.forEach(el => {
    observer.observe(el);
  });

  let ticking = false;
  
  function updateParallax() {
    const scrollY = window.pageYOffset;
    
    document.querySelectorAll('.floating-element').forEach((element, index) => {
      const speed = 0.5 + (index * 0.1);
      const yPos = -(scrollY * speed);
      element.style.transform = `translate3d(0, ${yPos}px, 0)`;
    });
    
    const heroContent = document.querySelector('.hero-content-enhanced');
    if (heroContent) {
      const yPos = -(scrollY * 0.1);
      heroContent.style.transform = `translate3d(0, ${yPos}px, 0)`;
    }
    
    ticking = false;
  }
  
  function requestTick() {
    if (!ticking) {
      requestAnimationFrame(updateParallax);
      ticking = true;
    }
  }
  
  window.addEventListener('scroll', requestTick);

  const scrollIndicator = document.querySelector('.scroll-indicator-enhanced');
  if (scrollIndicator) {
    scrollIndicator.addEventListener('click', function() {
      const nextSection = document.querySelector('.section-enhanced');
      if (nextSection) {
        nextSection.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  }

  let mouseX = 0;
  let mouseY = 0;
  let targetX = 0;
  let targetY = 0;

  document.addEventListener('mousemove', function(e) {
    mouseX = e.clientX;
    mouseY = e.clientY;
  });

  function animateParallaxMouse() {
    targetX += (mouseX - targetX) * 0.02;
    targetY += (mouseY - targetY) * 0.02;

    document.querySelectorAll('.floating-element').forEach((element, index) => {
      const speedX = (index + 1) * 0.01;
      const speedY = (index + 1) * 0.01;
      const x = (targetX - window.innerWidth / 2) * speedX;
      const y = (targetY - window.innerHeight / 2) * speedY;
      
      element.style.transform += ` translate(${x}px, ${y}px)`;
    });

    requestAnimationFrame(animateParallaxMouse);
  }
  
  animateParallaxMouse();

  const featureCards = document.querySelectorAll('.feature-card-enhanced');
  featureCards.forEach((card, index) => {
    card.addEventListener('mouseenter', function() {
      this.classList.add('card-hover');
      
      const icon = this.querySelector('.feature-icon-enhanced');
      if (icon) {
        icon.style.transform = 'scale(1.15) rotate(10deg)';
      }
    });
    
    card.addEventListener('mouseleave', function() {
      this.classList.remove('card-hover');
      
      const icon = this.querySelector('.feature-icon-enhanced');
      if (icon) {
        icon.style.transform = 'scale(1) rotate(0deg)';
      }
    });
  });

  const gridObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const gridItems = entry.target.querySelectorAll('.feature-card-enhanced, [class*="delay-"]');
        gridItems.forEach((item, index) => {
          setTimeout(() => {
            item.classList.add('visible');
          }, index * 200);
        });
      }
    });
  }, { threshold: 0.2 });

  document.querySelectorAll('.features-grid-enhanced').forEach(grid => {
    gridObserver.observe(grid);
  });

  function initializeAnimations() {
    const heroElements = document.querySelectorAll('.hero-content-enhanced > *');
    heroElements.forEach((element, index) => {
      element.style.animationDelay = `${index * 0.2}s`;
      element.classList.add('fade-in-up');
    });
  }

  setTimeout(initializeAnimations, 100);

  const fadeObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('section').forEach(section => {
    section.style.opacity = '0';
    section.style.transform = 'translateY(30px)';
    section.style.transition = 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
    fadeObserver.observe(section);
  });

  window.addEventListener('scroll', function() {
    const scrollY = window.pageYOffset;
    const hero = document.querySelector('.hero-enhanced');
    
    if (hero) {
      const scale = Math.max(0.8, 1 - scrollY * 0.0005);
      const opacity = Math.max(0.3, 1 - scrollY * 0.001);
      hero.style.transform = `scale(${scale})`;
      hero.style.opacity = opacity;
    }
  });

  function typeWriter(element, text, speed = 100) {
    let i = 0;
    element.innerHTML = '';
    
    function type() {
      if (i < text.length) {
        element.innerHTML += text.charAt(i);
        i++;
        setTimeout(type, speed);
      }
    }
    
    type();
  }

  const heroTitle = document.querySelector('.hero-title-enhanced');
  if (heroTitle) {
    const originalText = heroTitle.textContent;
    const titleObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          setTimeout(() => {
            typeWriter(heroTitle, originalText, 80);
          }, 500);
          titleObserver.unobserve(entry.target);
        }
      });
    });
    titleObserver.observe(heroTitle);
  }
});

const additionalStyles = `
<style>
/* Ripple effect */
.ripple {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: scale(0);
  animation: rippleAnimation 0.6s linear;
  pointer-events: none;
}

@keyframes rippleAnimation {
  to {
    transform: scale(4);
    opacity: 0;
  }
}

.fade-in-up {
  animation: fadeInUp 0.8s cubic-bezier(0.4, 0, 0.2, 1) both;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card-hover {
  transform: translateY(-15px) !important;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.4) !important;
}

.floating-element.animate-float {
  animation: enhancedFloat 15s ease-in-out infinite;
}

@keyframes enhancedFloat {
  0%, 100% {
    transform: translate(0, 0) rotate(0deg) scale(1);
  }
  25% {
    transform: translate(10px, -15px) rotate(5deg) scale(1.05);
  }
  50% {
    transform: translate(-5px, -25px) rotate(-3deg) scale(0.95);
  }
  75% {
    transform: translate(-15px, -10px) rotate(8deg) scale(1.02);
  }
}

/* Text glow effect */
.text-glow {
  text-shadow: 0 0 20px rgba(30, 215, 96, 0.5);
  transition: text-shadow 0.3s ease;
}

.text-glow:hover {
  text-shadow: 0 0 30px rgba(30, 215, 96, 0.8);
}

.pulse {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
  100% {
    transform: scale(1);
  }
}

.skeleton-loading {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

@keyframes loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.feature-card-enhanced:hover .feature-icon-enhanced {
  animation: iconBounce 0.6s ease;
}

@keyframes iconBounce {
  0%, 20%, 60%, 100% {
    transform: translateY(0) scale(1.1);
  }
  40% {
    transform: translateY(-10px) scale(1.15);
  }
  80% {
    transform: translateY(-5px) scale(1.12);
  }
}

.scroll-progress {
  position: fixed;
  top: 0;
  left: 0;
  width: 0%;
  height: 3px;
  background: linear-gradient(90deg, var(--spotify-green), #23ea69);
  z-index: 9999;
  transition: width 0.1s ease;
}



.cursor-outline {
  position: fixed;
  width: 40px;
  height: 40px;
  border: 2px solid rgba(30, 215, 96, 0.3);
  border-radius: 50%;
  pointer-events: none;
  z-index: 9998;
  transition: all 0.05s ease;
  transform: translate(-50%, -50%);
}

.cursor.hover {
  transform: translate(-50%, -50%) scale(1.5);
  background: rgba(30, 215, 96, 0.8);
}

.cursor-outline.hover {
  transform: translate(-50%, -50%) scale(2);
  border-color: rgba(30, 215, 96, 0.6);
}

.mouse-trail {
  position: fixed;
  width: 6px;
  height: 6px;
  background: var(--spotify-green);
  border-radius: 50%;
  pointer-events: none;
  z-index: 9997;
  opacity: 0.7;
  transition: all 0.3s ease;
}

.magnetic {
  transition: transform 0.2s ease;
  cursor: none;
}

.magnetic:hover {
  z-index: 1001;
}

/* Cursor text follower */
.cursor-text {
  position: fixed;
  background: var(--bg-elevated);
  color: var(--text-primary);
  padding: 0.5rem 1rem;
  border-radius: 2rem;
  font-size: 0.875rem;
  font-weight: 600;
  pointer-events: none;
  z-index: 10000;
  opacity: 0;
  transform: translate(-50%, -150%);
  transition: all 0.2s ease;
  border: 1px solid var(--ui-border);
  backdrop-filter: blur(10px);
  white-space: nowrap;
}

.cursor-text.show {
  opacity: 1;
}

/* Interactive glow effect */
.interactive-glow {
  position: relative;
  overflow: hidden;
}

.interactive-glow::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(30, 215, 96, 0.1) 0%, transparent 50%);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.interactive-glow:hover::before {
  opacity: 1;
}

/* Sparkle effect */
.sparkle {
  position: fixed;
  width: 4px;
  height: 4px;
  background: var(--spotify-green);
  border-radius: 50%;
  pointer-events: none;
  animation: sparkleAnimation 1s ease-out forwards;
  z-index: 9996;
}

@keyframes sparkleAnimation {
  0% {
    transform: scale(0) rotate(0deg);
    opacity: 1;
  }
  50% {
    transform: scale(1) rotate(180deg);
    opacity: 0.8;
  }
  100% {
    transform: scale(0) rotate(360deg);
    opacity: 0;
  }
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', additionalStyles);

// Add scroll progress bar
document.body.insertAdjacentHTML('afterbegin', '<div class="scroll-progress"></div>');

window.addEventListener('scroll', function() {
  const scrollProgress = document.querySelector('.scroll-progress');
  const scrollPercent = (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100;
  scrollProgress.style.width = scrollPercent + '%';
});

// Custom cursor effects
let cursor = document.querySelector('.cursor');
let cursorOutline = document.querySelector('.cursor-outline');
let cursorText = document.querySelector('.cursor-text');

if (!cursor) {
  cursor = document.createElement('div');
  cursor.className = 'cursor';
  document.body.appendChild(cursor);
}

if (!cursorOutline) {
  cursorOutline = document.createElement('div');
  cursorOutline.className = 'cursor-outline';
  document.body.appendChild(cursorOutline);
}

if (!cursorText) {
  cursorText = document.createElement('div');
  cursorText.className = 'cursor-text';
  document.body.appendChild(cursorText);
}

let mouseX = 0;
let mouseY = 0;
let outlineX = 0;
let outlineY = 0;

// Mouse trail effect
let trails = [];
const maxTrails = 15;

function createTrail(x, y) {
  const trail = document.createElement('div');
  trail.className = 'mouse-trail';
  trail.style.left = x + 'px';
  trail.style.top = y + 'px';
  document.body.appendChild(trail);
  
  trails.push(trail);
  
  if (trails.length > maxTrails) {
    const oldTrail = trails.shift();
    oldTrail.remove();
  }
  
  setTimeout(() => {
    trail.style.opacity = '0';
    trail.style.transform = 'scale(0)';
  }, 100);
  
  setTimeout(() => {
    if (trail.parentNode) {
      trail.remove();
    }
  }, 500);
}

// Sparkle effect
function createSparkle(x, y) {
  const sparkle = document.createElement('div');
  sparkle.className = 'sparkle';
  sparkle.style.left = x + 'px';
  sparkle.style.top = y + 'px';
  document.body.appendChild(sparkle);
  
  setTimeout(() => {
    sparkle.remove();
  }, 1000);
}

document.addEventListener('mousemove', function(e) {
  mouseX = e.clientX;
  mouseY = e.clientY;
  
  cursor.style.left = mouseX + 'px';
  cursor.style.top = mouseY + 'px';
  
  cursorText.style.left = mouseX + 'px';
  cursorText.style.top = mouseY + 'px';
  
  // Create trail every few pixels
  if (Math.random() > 0.8) {
    createTrail(mouseX, mouseY);
  }
  
  // Create sparkles on special elements
  const target = e.target;
  if (target.classList.contains('magnetic') && Math.random() > 0.95) {
    createSparkle(mouseX + (Math.random() - 0.5) * 20, mouseY + (Math.random() - 0.5) * 20);
  }
});

// Smooth animation for cursor outline
function animateCursorOutline() {
  outlineX += (mouseX - outlineX) * 0.5;
  outlineY += (mouseY - outlineY) * 0.5;
  
  cursorOutline.style.left = outlineX + 'px';
  cursorOutline.style.top = outlineY + 'px';
  
  requestAnimationFrame(animateCursorOutline);
}
animateCursorOutline();

// Magnetic effect for interactive elements
document.querySelectorAll('.magnetic').forEach(element => {
  element.addEventListener('mouseenter', function(e) {
    cursor.classList.add('hover');
    cursorOutline.classList.add('hover');
    
    const cursorTextContent = this.getAttribute('data-cursor-text');
    if (cursorTextContent) {
      cursorText.textContent = cursorTextContent;
      cursorText.classList.add('show');
    }
    
    this.style.cursor = 'none';
  });
  
  element.addEventListener('mouseleave', function() {
    cursor.classList.remove('hover');
    cursorOutline.classList.remove('hover');
    cursorText.classList.remove('show');
    
    this.style.transform = '';
    this.style.cursor = '';
  });
  
  element.addEventListener('mousemove', function(e) {
    const rect = this.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    
    // Apply magnetic effect
    const distance = Math.sqrt(x * x + y * y);
    const maxDistance = 50;
    
    if (distance < maxDistance) {
      const force = (maxDistance - distance) / maxDistance;
      const translateX = x * force * 0.3;
      const translateY = y * force * 0.3;
      
      this.style.transform = `translate(${translateX}px, ${translateY}px)`;
    }
  });
});

document.querySelectorAll('.interactive-glow').forEach(element => {
  element.addEventListener('mousemove', function(e) {
    const rect = this.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    
    this.style.setProperty('--mouse-x', x + '%');
    this.style.setProperty('--mouse-y', y + '%');
  });
});

// Hide custom cursor on touch devices
if ('ontouchstart' in window) {
  cursor.style.display = 'none';
  cursorOutline.style.display = 'none';
  cursorText.style.display = 'none';
}

document.querySelectorAll('button, .hero-cta-enhanced, .cta-button-enhanced').forEach(button => {
  button.addEventListener('click', function(e) {
    const ripple = document.createElement('span');
    const rect = this.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 2;
    const x = e.clientX - rect.left - size / 2;
    const y = e.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    ripple.classList.add('ripple');
    
    ripple.style.background = 'radial-gradient(circle, rgba(30, 215, 96, 0.3) 0%, transparent 70%)';
    
    this.appendChild(ripple);
    
    for (let i = 0; i < 5; i++) {
      setTimeout(() => {
        createSparkle(
          e.clientX + (Math.random() - 0.5) * 40,
          e.clientY + (Math.random() - 0.5) * 40
        );
      }, i * 100);
    }
    
    setTimeout(() => {
      ripple.remove();
    }, 600);
  });
});

document.addEventListener('mousemove', function(e) {
  const mouseXPercent = (e.clientX / window.innerWidth) * 2 - 1;
  const mouseYPercent = (e.clientY / window.innerHeight) * 2 - 1;
  
  document.querySelectorAll('.floating-element').forEach((element, index) => {
    const speed = (index + 1) * 0.02;
    const x = mouseXPercent * speed * 20;
    const y = mouseYPercent * speed * 20;
    
    element.style.transform += ` translate(${x}px, ${y}px)`;
  });
  
  document.querySelectorAll('.feature-card-enhanced').forEach((card, index) => {
    const speed = 0.01;
    const x = mouseXPercent * speed * 10;
    const y = mouseYPercent * speed * 10;
    
    card.style.transform += ` translate(${x}px, ${y}px)`;
  });
});

window.addEventListener('scroll', function() {
  const scrollY = window.pageYOffset;
  const scrollPercent = scrollY / (document.body.scrollHeight - window.innerHeight);
  
  // Change cursor color based on scroll position
  const hue = scrollPercent * 60; // 0 to 60 degrees (green to yellow)
  cursor.style.background = `hsl(${120 + hue}, 70%, 50%)`;
  
  let lastScrollY = scrollY;
  setTimeout(() => {
    const scrollSpeed = Math.abs(scrollY - lastScrollY);
    const trailOpacity = Math.min(scrollSpeed / 50, 1);
    
    trails.forEach(trail => {
      trail.style.opacity = trailOpacity;
    });
  }, 50);
});
//  Ripple effect
  document.querySelectorAll('.hero-cta-enhanced, .cta-button-enhanced').forEach(button => {
    button.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;
      
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = x + 'px';
      ripple.style.top = y + 'px';
      ripple.classList.add('ripple');
      
      this.appendChild(ripple);
      
      setTimeout(() => {
        ripple.remove();
      }, 600);
    });
    
    button.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-3px) scale(1.05)';
    });
    
    button.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0) scale(1)';
    });
  });

  function animateCounter(element) {
    const target = parseInt(element.textContent.replace(/\D/g, ''));
    const duration = 2000;
    const start = performance.now();
    const suffix = element.textContent.replace(/\d/g, '');
    
    function updateCounter(currentTime) {
      const elapsed = currentTime - start;
      const progress = Math.min(elapsed / duration, 1);
      
      const easeOutQuart = 1 - Math.pow(1 - progress, 4);
      const current = Math.floor(easeOutQuart * target);
      
      element.textContent = current + suffix;
      
      if (progress < 1) {
        requestAnimationFrame(updateCounter);
      }
    }
    
    requestAnimationFrame(updateCounter);
  }