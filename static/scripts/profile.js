document.addEventListener('DOMContentLoaded', () => {
    const editButton = document.querySelector('.edit-button');
    const saveButton = document.querySelector('.save-button');
    const inputs = document.querySelectorAll('.profile-form input, .profile-form textarea');
  
    editButton.addEventListener('click', () => {
      inputs.forEach(input => {
        if (input.id !== 'username') {
          input.removeAttribute('readonly');
          input.style.background = 'rgba(255, 255, 255, 0.15)';
          input.style.cursor = 'text';
        }
      });
      saveButton.style.display = 'block';
    });
  
    saveButton.addEventListener('click', (e) => {
      e.preventDefault();
      inputs.forEach(input => {
        input.setAttribute('readonly', 'readonly');
        input.style.background = 'rgba(255, 255, 255, 0.05)';
        input.style.cursor = 'not-allowed';
      });
      saveButton.style.display = 'none';
    });
  });