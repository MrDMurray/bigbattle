document.addEventListener('DOMContentLoaded', () => {
  const loginBtn = document.getElementById('login-btn');
  const seatingLink = document.getElementById('seating-link');

  const updateButton = () => {
    if (localStorage.getItem('loggedIn') === 'true') {
      loginBtn.textContent = 'Logged in with Google';
      loginBtn.disabled = true;
    }
  };

  loginBtn.addEventListener('click', () => {
    localStorage.setItem('loggedIn', 'true');
    updateButton();
  });

  seatingLink.addEventListener('click', (e) => {
    if (localStorage.getItem('loggedIn') !== 'true') {
      e.preventDefault();
      alert('Please log in with Google before visiting Seating Planet.');
    }
  });

  updateButton();
});
