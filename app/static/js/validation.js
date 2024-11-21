function downloadFile(fileId, filename) {
  const button = document.querySelector(`button[data-file-id="${fileId}"]`);
  const spinner = button.querySelector('.spinner-border');
  const icon = button.querySelector('.bi-download');

  // Show loading state
  spinner.classList.remove('d-none');
  icon.classList.add('d-none');
  button.disabled = true;

  fetch(`/merge_and_download/${fileId}`)
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.blob();
    })
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const originalName = filename.split('.')[0];
      a.download = `${originalName}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    })
    .catch(error => {
      console.error('Error:', error);
      showToast('Error downloading file. Please try again.');
    })
    .finally(() => {
      // Reset button state
      spinner.classList.add('d-none');
      icon.classList.remove('d-none');
      button.disabled = false;
    });
}

function showToast(message) {
  const toastEl = document.getElementById('toast');
  const toast = new bootstrap.Toast(toastEl);
  toastEl.querySelector('.toast-body').textContent = message;
  toast.show();
}