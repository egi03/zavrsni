document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('profile-picture-upload');
    
    if (!fileInput) {
      return;
    }
    
    const profilePictureContainer = document.querySelector('.profile-picture');
    if (!profilePictureContainer) {
      return;
    }
    
    const saveButton = document.querySelector('.save-picture-button');
    if (saveButton) {
      saveButton.style.display = 'none';
    }
    
    const existingImg = profilePictureContainer.querySelector('img');
    const placeholderDiv = profilePictureContainer.querySelector('.placeholder-picture');
    
    if (existingImg) {
      const pictureForm = document.getElementById('profile-picture-form');
      if (pictureForm && !document.querySelector('.permanent-remove-btn')) {
        const removeBtn = document.createElement('button');
        removeBtn.className = 'permanent-remove-btn';
        removeBtn.innerHTML = 'Ukloni sliku';
        removeBtn.type = 'button';
        
        removeBtn.style.marginTop = '10px';
        removeBtn.style.padding = '6px 12px';
        removeBtn.style.backgroundColor = '#dc3545';
        removeBtn.style.color = 'white';
        removeBtn.style.border = 'none';
        removeBtn.style.borderRadius = '4px';
        removeBtn.style.cursor = 'pointer';
        removeBtn.style.fontSize = '0.85rem';
        removeBtn.style.display = 'block';
        
        removeBtn.addEventListener('click', function() {
          let removeImageInput = document.getElementById('remove-profile-picture');
          if (!removeImageInput) {
            removeImageInput = document.createElement('input');
            removeImageInput.type = 'hidden';
            removeImageInput.id = 'remove-profile-picture';
            removeImageInput.name = 'remove_profile_picture';
            removeImageInput.value = 'true';
            pictureForm.appendChild(removeImageInput);
          }
          
          if (placeholderDiv) {
            placeholderDiv.style.display = '';
          }
          if (existingImg) {
            existingImg.style.display = 'none';
          }
          
          if (saveButton) {
            saveButton.style.display = 'block';
          }
          
          this.style.display = 'none';
        });
        
        pictureForm.appendChild(removeBtn);
      }
    }
    
    let hiddenInput = document.getElementById('profile-picture-data');
    if (!hiddenInput) {
      hiddenInput = document.createElement('input');
      hiddenInput.type = 'hidden';
      hiddenInput.id = 'profile-picture-data';
      hiddenInput.name = 'profile_picture_data';
      fileInput.parentNode.appendChild(hiddenInput);
    }
    
    fileInput.addEventListener('change', function(event) {
      const file = event.target.files[0];
      
      if (!file) return;
      
      if (!file.type.match('image.*')) {
        alert('Please select an image file.');
        return;
      }
      
      if (file.size > 5 * 1024 * 1024) {
        alert('File is too large. Maximum size is 5MB.');
        return;
      }
      
      const removeImageInput = document.getElementById('remove-profile-picture');
      if (removeImageInput) {
        removeImageInput.parentNode.removeChild(removeImageInput);
      }
      
      if (saveButton) {
        saveButton.style.display = 'block';
      }
      
      const permanentRemoveBtn = document.querySelector('.permanent-remove-btn');
      if (permanentRemoveBtn) {
        permanentRemoveBtn.style.display = 'none';
      }
      
      const reader = new FileReader();
      
      reader.onload = function(e) {
        if (placeholderDiv) {
          placeholderDiv.style.display = 'none';
          
          if (!existingImg) {
            const newImg = document.createElement('img');
            newImg.alt = 'Profile Picture';
            profilePictureContainer.insertBefore(newImg, placeholderDiv);
            newImg.src = e.target.result;
          } else {
            existingImg.style.display = '';
            existingImg.src = e.target.result;
          }
        } 
        else if (existingImg) {
          existingImg.style.display = '';
          existingImg.src = e.target.result;
        }
        
        hiddenInput.value = e.target.result;
        
        let removeBtn = profilePictureContainer.querySelector('.remove-btn');
        if (!removeBtn) {
          removeBtn = document.createElement('button');
          removeBtn.className = 'remove-btn';
          removeBtn.innerHTML = 'x';
          removeBtn.style.position = 'absolute';
          removeBtn.style.top = '5px';
          removeBtn.style.right = '5px';
          removeBtn.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
          removeBtn.style.color = 'white';
          removeBtn.style.border = 'none';
          removeBtn.style.borderRadius = '50%';
          removeBtn.style.width = '25px';
          removeBtn.style.height = '25px';
          removeBtn.style.cursor = 'pointer';
          removeBtn.style.display = 'flex';
          removeBtn.style.alignItems = 'center';
          removeBtn.style.justifyContent = 'center';
          removeBtn.style.fontWeight = 'bold';
          removeBtn.style.fontSize = '16px';
          
          removeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            fileInput.value = '';
            hiddenInput.value = '';
            this.style.display = 'none';
            
            // Show original image if it exists or placeholder if not
            if (existingImg && existingImg.dataset.originalSrc) {
              existingImg.src = existingImg.dataset.originalSrc;
              existingImg.style.display = '';
              
              const permanentRemoveBtn = document.querySelector('.permanent-remove-btn');
              if (permanentRemoveBtn) {
                permanentRemoveBtn.style.display = '';
              }
            } else {
              if (existingImg) {
                existingImg.style.display = 'none';
              }
              if (placeholderDiv) {
                placeholderDiv.style.display = '';
              }
            }
            
            if (saveButton) {
              saveButton.style.display = 'none';
            }
          });
          
          profilePictureContainer.appendChild(removeBtn);
        }
        
        // Save the original src if this is the first change
        if (existingImg && !existingImg.dataset.originalSrc) {
          existingImg.dataset.originalSrc = existingImg.src;
        }
        
        removeBtn.style.display = 'flex';
      };
      
      reader.readAsDataURL(file);
    });
    
    const form = fileInput.closest('form');
    if (form) {
      form.enctype = "multipart/form-data";
    }
  });