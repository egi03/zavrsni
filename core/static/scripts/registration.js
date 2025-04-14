document.addEventListener('DOMContentLoaded', function() {
  let overlay = document.getElementById("overlay");

  let openSignUpButton = document.getElementById("slide-left-button");
  let openSignInButton = document.getElementById("slide-right-button");

  let leftText = document.getElementById("sign-in");
  let rightText = document.getElementById("sign-up");

  let accountForm = document.getElementById("sign-in-info");
  let signinForm = document.getElementById("sign-up-info");

  const openSignUp = () => {
    leftText.classList.remove("overlay-text-left-animation-out");
    overlay.classList.remove("open-sign-in");
    rightText.classList.remove("overlay-text-right-animation");
    accountForm.classList.remove("form-left-slide-in");
    signinForm.classList.remove("form-right-slide-in");

    accountForm.classList.add("form-left-slide-out");
    rightText.classList.add("overlay-text-right-animation-out");
    overlay.classList.add("open-sign-up");
    leftText.classList.add("overlay-text-left-animation");

    setTimeout(() => {
      accountForm.style.display = "none";
      accountForm.classList.remove("form-left-slide-out");
    }, 700);

    setTimeout(() => {
      signinForm.style.display = "flex";
      signinForm.classList.add("form-right-slide-in");
    }, 200);
    
    history.pushState(null, null, '/register/');
  };

  const openSignIn = () => {
    leftText.classList.remove("overlay-text-left-animation");
    overlay.classList.remove("open-sign-up");
    rightText.classList.remove("overlay-text-right-animation-out");
    signinForm.classList.remove("form-right-slide-in");
    accountForm.classList.remove("form-left-slide-in");

    signinForm.classList.add("form-right-slide-out");
    leftText.classList.add("overlay-text-left-animation-out");
    overlay.classList.add("open-sign-in");
    rightText.classList.add("overlay-text-right-animation");

    setTimeout(() => {
      signinForm.style.display = "none";
      signinForm.classList.remove("form-right-slide-out");
    }, 700);

    setTimeout(() => {
      accountForm.style.display = "flex";
      accountForm.classList.add("form-left-slide-in");
    }, 200);
    
    history.pushState(null, null, '/login/');
  };

  openSignUpButton.addEventListener("click", openSignUp, false);
  openSignInButton.addEventListener("click", openSignIn, false);

  const loginFailedInput = document.getElementById('login_failed');
  if (loginFailedInput && loginFailedInput.value === 'true') {
    setTimeout(openSignIn, 100);
    return;
  }
  
  const loginFormErrors = document.querySelectorAll('#sign-in-form .error-message');
  if (loginFormErrors.length > 0) {
    setTimeout(openSignIn, 100);
    return; 
  }
  
  const registerFormErrors = document.querySelectorAll('#sign-up-form .error-message');
  if (registerFormErrors.length > 0) {
    setTimeout(openSignUp, 100);
    return; 
  }
  
  const currentUrl = window.location.pathname;
  
  if (currentUrl.includes('login')) {
    setTimeout(openSignIn, 100);
  } 
  else if (currentUrl.includes('register')) {
    setTimeout(openSignUp, 100);
  }
  
  const messages = document.querySelectorAll('.messages .message');
  if (messages.length > 0) {
    let messageContainer = document.querySelector('.message-container');
    if (!messageContainer) {
      messageContainer = document.createElement('div');
      messageContainer.className = 'message-container';
      document.querySelector('.container').prepend(messageContainer);
    }
    
    messages.forEach(message => {
      const newMessage = document.createElement('div');
      newMessage.className = `message ${message.className}`;
      newMessage.textContent = message.textContent;
      messageContainer.appendChild(newMessage);
      
      setTimeout(() => {
        newMessage.style.opacity = '0';
        setTimeout(() => {
          newMessage.remove();
        }, 500);
      }, 5000);
    });
  }
});