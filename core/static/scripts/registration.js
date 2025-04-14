let overlay = document.getElementById("overlay");

// Buttons to 'switch' the page
let openSignUpButton = document.getElementById("slide-left-button");
let openSignInButton = document.getElementById("slide-right-button");

// The sidebars
let leftText = document.getElementById("sign-in");
let rightText = document.getElementById("sign-up");

// The forms
let accountForm = document.getElementById("sign-in-info");
let signinForm = document.getElementById("sign-up-info");

// Open the Sign Up page
const openSignUp = () => {
  // Remove current animation states
  leftText.classList.remove("overlay-text-left-animation-out");
  overlay.classList.remove("open-sign-in");
  rightText.classList.remove("overlay-text-right-animation");
  accountForm.classList.remove("form-left-slide-in");
  signinForm.classList.remove("form-right-slide-in");

  // Add new animation classes
  accountForm.classList.add("form-left-slide-out");
  rightText.classList.add("overlay-text-right-animation-out");
  overlay.classList.add("open-sign-up");
  leftText.classList.add("overlay-text-left-animation");

  // Hide sign-in form after animation
  setTimeout(() => {
    accountForm.style.display = "none";
    accountForm.classList.remove("form-left-slide-out");
  }, 700);

  // Show sign-up form after short delay
  setTimeout(() => {
    signinForm.style.display = "flex";
    signinForm.classList.add("form-right-slide-in");
  }, 200);
};

// Open the Sign In page
const openSignIn = () => {
  // Remove current animation states
  leftText.classList.remove("overlay-text-left-animation");
  overlay.classList.remove("open-sign-up");
  rightText.classList.remove("overlay-text-right-animation-out");
  signinForm.classList.remove("form-right-slide-in");
  accountForm.classList.remove("form-left-slide-in");

  // Add new animation classes
  signinForm.classList.add("form-right-slide-out");
  leftText.classList.add("overlay-text-left-animation-out");
  overlay.classList.add("open-sign-in");
  rightText.classList.add("overlay-text-right-animation");

  // Hide sign-up form after animation
  setTimeout(() => {
    signinForm.style.display = "none";
    signinForm.classList.remove("form-right-slide-out");
  }, 700);

  // Show sign-in form after short delay
  setTimeout(() => {
    accountForm.style.display = "flex";
    accountForm.classList.add("form-left-slide-in");
  }, 200);
};

// Hook up buttons
openSignUpButton.addEventListener("click", openSignUp, false);
openSignInButton.addEventListener("click", openSignIn, false);