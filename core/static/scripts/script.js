document.addEventListener('DOMContentLoaded', () => {
    const sections = document.querySelectorAll('section');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                changeBackgroundColor(entry.target);
            }
        });
    }, {
        threshold: 0.5 
    });

    sections.forEach(section => {
        observer.observe(section);
    });

    function changeBackgroundColor(section) {
        const sectionId = section.id;
        const body = document.body;
        
        body.classList.remove('bg-color-1', 'bg-color-2', 'bg-color-3', 'bg-color-4');
        
        switch (sectionId) {
            case 'section1':
                body.classList.add('bg-color-1');
                break;
            case 'section2':
                body.classList.add('bg-color-2');
                break;
            case 'section3':
                body.classList.add('bg-color-3');
                break;
            case 'section4':
                body.classList.add('bg-color-4');
                break;
            default:
                body.classList.add('bg-color-1'); // Fallback color
        }
    }

    if (sections.length > 0) {
        changeBackgroundColor(sections[0]);
    }
});