document.addEventListener('DOMContentLoaded', function() {
    if (window.innerWidth <= 768 || 'ontouchstart' in window) {
        return;
    }
    
    initSimpleCursor();
    initParticleTrail();
    initSimpleInteractions();
});

function initSimpleCursor() {
    const cursor = document.createElement('div');
    cursor.className = 'simple-cursor';
    document.body.appendChild(cursor);
    
    let mouseX = 0, mouseY = 0;
    let isVisible = false;
    
    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        
        if (!isVisible) {
            cursor.classList.add('active');
            isVisible = true;
        }
        
        cursor.style.left = mouseX + 'px';
        cursor.style.top = mouseY + 'px';
    });
    
    document.addEventListener('mouseenter', () => {
        cursor.classList.add('active');
        isVisible = true;
    });
    
    document.addEventListener('mouseleave', () => {
        cursor.classList.remove('active');
        isVisible = false;
    });
    
    document.addEventListener('mousedown', () => {
        cursor.classList.add('click');
    });
    
    document.addEventListener('mouseup', () => {
        cursor.classList.remove('click');
    });
    
    return cursor;
}

function initParticleTrail() {
    const particles = [];
    const maxParticles = 12;
    let lastParticleTime = 0;
    
    document.addEventListener('mousemove', (e) => {
        const now = Date.now();
        
        if (now - lastParticleTime > 80) {
            createParticle(e.clientX, e.clientY);
            lastParticleTime = now;
        }
    });
    
    function createParticle(x, y) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        
        const offsetX = (Math.random() - 0.5) * 8;
        const offsetY = (Math.random() - 0.5) * 8;
        
        particle.style.left = (x + offsetX) + 'px';
        particle.style.top = (y + offsetY) + 'px';
        
        document.body.appendChild(particle);
        particles.push(particle);
        
        if (particles.length > maxParticles) {
            const oldParticle = particles.shift();
            if (oldParticle.parentNode) {
                oldParticle.remove();
            }
        }
        
        setTimeout(() => {
            if (particle.parentNode) {
                particle.remove();
                const index = particles.indexOf(particle);
                if (index > -1) {
                    particles.splice(index, 1);
                }
            }
        }, 1000);
    }
}

function initSimpleInteractions() {
    const cursor = document.querySelector('.simple-cursor');
    
    const interactiveSelectors = [
        '.hero-cta-primary',
        '.cta-button-primary',
        '.feature-card-primary',
        'button',
        'a:not(.no-cursor)',
        '.btn'
    ];
    
    interactiveSelectors.forEach(selector => {
        document.querySelectorAll(selector).forEach(element => {
            if (!element.classList.contains('simple-interactive')) {
                element.classList.add('simple-interactive');
            }
        });
    });
    
    document.querySelectorAll('.simple-interactive').forEach(element => {
        element.addEventListener('mouseenter', () => {
            if (cursor) cursor.classList.add('hover');
        });
        
        element.addEventListener('mouseleave', () => {
            if (cursor) cursor.classList.remove('hover');
        });
        
        element.addEventListener('click', (e) => {
            createSimpleRipple(e);
        });
    });
}

function createSimpleRipple(event) {
    const element = event.currentTarget;
    const ripple = document.createElement('span');
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 1.5;
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    ripple.classList.add('simple-ripple');
    
    const originalPosition = element.style.position;
    if (!originalPosition || originalPosition === 'static') {
        element.style.position = 'relative';
    }
    
    element.style.overflow = 'hidden';
    element.appendChild(ripple);
    
    setTimeout(() => {
        if (ripple.parentNode) {
            ripple.remove();
        }
    }, 600);
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        document.querySelectorAll('.particle').forEach(particle => {
            particle.remove();
        });
    }
});