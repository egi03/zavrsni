document.addEventListener('DOMContentLoaded', function() {
  console.log("Password checker script loaded");
  
  const passwordField = document.querySelector('input[name="password1"]') || 
                        document.querySelector('#sign-up-form input[type="password"]:first-of-type');
  
  const confirmPasswordField = document.querySelector('input[name="password2"]') || 
                              document.querySelector('#sign-up-form input[type="password"]:nth-of-type(2)');
  
  console.log("Password field found:", !!passwordField);
  console.log("Confirm password field found:", !!confirmPasswordField);
  
  if (!passwordField) {
    console.error("Password field not found");
    return;
  }
  
  const requirementsContainer = document.createElement('div');
  requirementsContainer.className = 'password-requirements';
  requirementsContainer.style.margin = '10px 0';
  requirementsContainer.style.fontSize = '0.85rem';
  requirementsContainer.style.color = '#222';
  requirementsContainer.style.backgroundColor = '#111'; 
  requirementsContainer.style.borderRadius = '4px';
  requirementsContainer.style.padding = '10px';
  requirementsContainer.style.width = '100%';
  requirementsContainer.style.border = '1px solid #333'; 
  
  passwordField.parentNode.insertBefore(requirementsContainer, passwordField.nextSibling);
  
  const requirements = [
    { id: 'length', text: 'At least 8 characters', regex: /.{8,}/ },
    { id: 'lowercase', text: 'At least one lowercase letter', regex: /[a-z]/ },
    { id: 'number', text: 'At least one number', regex: /[0-9]/ }
  ];
  
  let html = '<div style="font-weight: bold; margin-bottom: 5px; color: #aaa;">Password must contain:</div>';
  html += '<ul style="list-style-type: none; padding-left: 0; margin: 0;">';
  
  requirements.forEach(req => {
    html += `<li id="req-${req.id}" style="margin: 5px 0; display: flex; align-items: center;">
              <span class="req-icon" style="color: #dc3545; margin-right: 8px; font-weight: bold;">✕</span> 
              <span style="color: #aaa;">${req.text}</span>
            </li>`;
  });
  
  html += '</ul>';
  
  if (confirmPasswordField) {
    html += `<div id="req-match" style="margin-top: 10px; padding-top: 5px; border-top: 1px solid #333; display: none;">
              <span class="req-icon" style="color: #dc3545; margin-right: 8px; font-weight: bold;">✕</span> 
              <span style="color: #aaa;">Passwords match</span>
            </div>`;
  }
  
  requirementsContainer.innerHTML = html;
  
  function checkPasswordStrength(password) {
    console.log("Checking password strength");
    
    requirements.forEach(req => {
      const reqElement = document.getElementById(`req-${req.id}`);
      if (!reqElement) return;
      
      const icon = reqElement.querySelector('.req-icon');
      if (!icon) return;
      
      if (req.regex.test(password)) {
        icon.style.color = '#4CAF50';
        icon.textContent = '✓';
      } else {
        icon.style.color = '#dc3545'; 
        icon.textContent = '✕';
      }
    });
  }
  
  function checkPasswordsMatch() {
    if (!confirmPasswordField) return;
    
    const matchReq = document.getElementById('req-match');
    if (!matchReq) return;
    
    const icon = matchReq.querySelector('.req-icon');
    if (!icon) return;
    
    const password1 = passwordField.value;
    const password2 = confirmPasswordField.value;
    
    if (password2.length > 0) {
      matchReq.style.display = 'flex';
      
      if (password1 === password2) {
        icon.style.color = '#4CAF50'; 
        icon.textContent = '✓';
      } else {
        icon.style.color = '#dc3545'; 
        icon.textContent = '✕';
      }
    } else {
      matchReq.style.display = 'none';
    }
  }
  
  passwordField.addEventListener('input', function() {
    checkPasswordStrength(this.value);
    checkPasswordsMatch();
  });
  
  passwordField.addEventListener('keyup', function() {
    checkPasswordStrength(this.value);
    checkPasswordsMatch();
  });
  
  passwordField.addEventListener('focus', function() {
    requirementsContainer.style.display = 'block';
  });
  
  if (confirmPasswordField) {
    confirmPasswordField.addEventListener('input', checkPasswordsMatch);
    confirmPasswordField.addEventListener('keyup', checkPasswordsMatch);
    confirmPasswordField.addEventListener('focus', function() {
      requirementsContainer.style.display = 'block';
    });
  }
  
  checkPasswordStrength(passwordField.value);
  if (confirmPasswordField) {
    checkPasswordsMatch();
  }
});